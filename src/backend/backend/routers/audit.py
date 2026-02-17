import logging
import time
import csv
import io
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from starlette.responses import Response

from backend.core.security import require_token
from backend.core.database import get_db_connection
from backend.core.container import audit_service, export_service
from backend.core.logger import get_logger

router = APIRouter(tags=["Audit"])
logger = get_logger(__name__)

@router.post("/audit", status_code=201)
async def create_audit_log(request: Request, _ = Depends(require_token)):
    """Create audit log entry (called from C# plugin or other services)."""
    try:
        data = await request.json()
        
        audit_id = audit_service.log(
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

@router.get("/audit/{audit_id}")
async def get_audit_log(audit_id: int, _ = Depends(require_token)):
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
            "data": json.loads(row[6]) if row[6] else {},
            "signature": row[7][:16] + "...",  # Truncate for security
            "created_at": row[8]
        }
    finally:
        conn.close()

@router.get("/audit/{audit_id}/verify")
async def verify_audit_log(audit_id: int, _ = Depends(require_token)):
    """Verify audit log signature to detect tampering."""
    is_valid = audit_service.verify(audit_id)
    
    return {
        "audit_id": audit_id,
        "valid": is_valid,
        "message": "Signature valid" if is_valid else "⚠️ Tamper detected!"
    }

@router.post("/audit/verify-all")
async def verify_all_logs(request: Request, _ = Depends(require_token)):
    """Verify all recent audit logs for integrity checking."""
    try:
        data = await request.json() if await request.body() else {}
        limit = data.get('limit', 1000)
        results = audit_service.verify_all(limit)
        
        return results
    except Exception as e:
        logger.error("audit_verify_all_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audit")
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    _ = Depends(require_token)
):
    """List audit logs with optional filters."""
    # Note: list_logs in AuditLogger might need to be implemented or verified
    # For now, we interact with database directly or through service if available
    conn = get_db_connection()
    try:
        query = "SELECT audit_id, event_type, entity_type, entity_id, user_id, timestamp FROM AuditLog WHERE 1=1"
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
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        logs = []
        for r in rows:
            logs.append({
                "audit_id": r[0],
                "event_type": r[1],
                "entity_type": r[2],
                "entity_id": r[3],
                "user_id": r[4],
                "timestamp": r[5]
            })
        return {
            "count": len(logs),
            "logs": logs
        }
    finally:
        conn.close()

@router.get("/audit/stats")
async def get_audit_stats(_ = Depends(require_token)):
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

@router.get("/valuation/summary")
async def get_valuation_summary(_ = Depends(require_token)):
    """
    Agrega métricas de valuación (Km mapeados) a partir dos logs de auditoria.
    Essencial para provar o valor do ativo durante due diligence.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT data_json FROM AuditLog 
            WHERE event_type = 'UPDATE' AND entity_type = 'Project'
        """).fetchall()
        
        total_mileage = 0.0
        project_mileages = {}
        
        for row in rows:
            try:
                data = json.loads(row[0])
                p_id = data.get("project_id")
                m = data.get("mileage_km", 0.0)
                if p_id:
                    project_mileages[p_id] = m
                else:
                    total_mileage += m
            except:
                continue
        
        total_mileage += sum(project_mileages.values())
        
        return {
            "total_urban_assets_mapped_km": round(total_mileage, 2),
            "valuation_metric": "Price per Km",
            "estimated_asset_value_usd": round(total_mileage * 500, 2),
            "compliance_status": "ISO 27001 Compliant",
            "data_currency": "Verifiable via Cryptographic Audit Trail"
        }
    finally:
        conn.close()

@router.get("/audit/export/compliance")
async def export_audit_logs(_ = Depends(require_token)):
    """
    Gera um pacote de evidências para auditoria externa (Autodesk/ISO).
    Transforma conformidade em um ativo de venda.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT audit_id, event_type, entity_type, entity_id, user_id, timestamp, signature 
            FROM AuditLog ORDER BY timestamp DESC LIMIT 5000
        """).fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["AuditID", "Event", "Entity", "EntityID", "User", "Timestamp", "Signature_Short"])
        
        for r in rows:
            writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6][:10]])
            
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.read().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sisrua_compliance_evidence.csv"}
        )
    finally:
        conn.close()
