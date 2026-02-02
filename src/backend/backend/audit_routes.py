"""
Audit Log API Routes
REST endpoints for creating and querying cryptographic audit logs.
Converted to FastAPI APIRouter.
"""
from fastapi import APIRouter, Request, HTTPException, Query
from backend.core.audit import get_audit_logger
from backend.core.database import get_db_connection
from backend.core.logger import get_logger
from typing import Optional, List, Dict, Any

audit_bp = APIRouter()
logger = get_logger(__name__)

@audit_bp.post("/audit", status_code=201)
async def create_audit_log(request: Request):
    """Create audit log entry (called from C# plugin or other services)."""
    try:
        data = await request.json()
        audit = get_audit_logger()
        
        audit_id = audit.log(
            event_type=data['event_type'],
            entity_type=data['entity_type'],
            entity_id=data.get('entity_id'),
            data=data.get('data', {}),
            user_id=data.get('user_id')
        )
        
        return {"audit_id": audit_id}
    except KeyError as e:
        logger.error("audit_create_missing_field", field=str(e))
        raise HTTPException(status_code=400, detail=f"Missing required field: {e}")
    except Exception as e:
        logger.error("audit_create_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@audit_bp.get("/audit/{audit_id}")
async def get_audit_log(audit_id: int):
    """Get a specific audit log entry."""
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT audit_id, event_type, entity_type, entity_id, user_id, 
                   timestamp, data_json, signature, created_at
            FROM AuditLog WHERE audit_id = ?
        """, (audit_id,)).fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Audit log not found")
        
        return {
            "audit_id": row[0],
            "event_type": row[1],
            "entity_type": row[2],
            "entity_id": row[3],
            "user_id": row[4],
            "timestamp": row[5],
            "data": row[6],
            "signature": row[7][:16] + "...",  # Truncate for security
            "created_at": row[8]
        }
    finally:
        conn.close()

@audit_bp.get("/audit/{audit_id}/verify")
async def verify_audit_log(audit_id: int):
    """Verify audit log signature to detect tampering."""
    audit = get_audit_logger()
    is_valid = audit.verify(audit_id)
    
    return {
        "audit_id": audit_id,
        "valid": is_valid,
        "message": "Signature valid" if is_valid else "⚠️ Tamper detected!"
    }

@audit_bp.post("/audit/verify-all")
async def verify_all_logs(request: Request):
    """Verify all recent audit logs for integrity checking."""
    try:
        data = await request.json() if await request.body() else {}
        limit = data.get('limit', 1000)
        audit = get_audit_logger()
        results = audit.verify_all(limit)
        
        return results
    except Exception as e:
        logger.error("audit_verify_all_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@audit_bp.get("/audit")
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """List audit logs with optional filters."""
    conn = get_db_connection()
    try:
        query = """
            SELECT audit_id, event_type, entity_type, entity_id, user_id, 
                   timestamp, data_json, signature, created_at
            FROM AuditLog WHERE 1=1
        """
        params = []
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY audit_id DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        logs = [
            {
                "audit_id": row[0],
                "event_type": row[1],
                "entity_type": row[2],
                "entity_id": row[3],
                "user_id": row[4],
                "timestamp": row[5],
                "data": row[6],
                "signature": row[7][:16] + "...",  # Truncate for display
                "created_at": row[8]
            }
            for row in rows
        ]
        
        return {
            "count": len(logs),
            "logs": logs
        }
    finally:
        conn.close()

@audit_bp.get("/audit/stats")
async def get_audit_stats():
    """Get audit log statistics."""
    conn = get_db_connection()
    try:
        # Total count
        total = conn.execute("SELECT COUNT(*) FROM AuditLog").fetchone()[0]
        
        # By entity type
        by_entity = conn.execute("""
            SELECT entity_type, COUNT(*) as count 
            FROM AuditLog 
            GROUP BY entity_type
        """).fetchall()
        
        # By event type
        by_event = conn.execute("""
            SELECT event_type, COUNT(*) as count 
            FROM AuditLog 
            GROUP BY event_type
        """).fetchall()
        
        # Recent activity (last 24 hours)
        import time
        day_ago = time.time() - 86400
        recent = conn.execute("""
            SELECT COUNT(*) FROM AuditLog 
            WHERE timestamp > ?
        """, (day_ago,)).fetchone()[0]
        
        return {
            "total_logs": total,
            "recent_24h": recent,
            "by_entity_type": {row[0]: row[1] for row in by_entity},
            "by_event_type": {row[0]: row[1] for row in by_event}
        }
    finally:
        conn.close()
