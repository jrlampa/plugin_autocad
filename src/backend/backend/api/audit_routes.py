"""
Audit Log API Routes
REST endpoints for creating and querying cryptographic audit logs.
"""
from flask import Blueprint, request, jsonify
from backend.core.audit import get_audit_logger
from backend.core.database import get_db_connection
from backend.core.logger import get_logger

audit_bp = Blueprint('audit', __name__)
logger = get_logger(__name__)

@audit_bp.route('/audit', methods=['POST'])
def create_audit_log():
    """Create audit log entry (called from C# plugin or other services)."""
    try:
        data = request.json
        audit = get_audit_logger()
        
        audit_id = audit.log(
            event_type=data['event_type'],
            entity_type=data['entity_type'],
            entity_id=data.get('entity_id'),
            data=data.get('data', {}),
            user_id=data.get('user_id')
        )
        
        return jsonify({"audit_id": audit_id}), 201
    except KeyError as e:
        logger.error("audit_create_missing_field", field=str(e))
        return jsonify({"error": f"Missing required field: {e}"}), 400
    except Exception as e:
        logger.error("audit_create_failed", error=str(e))
        return jsonify({"error": str(e)}), 500

@audit_bp.route('/audit/<int:audit_id>', methods=['GET'])
def get_audit_log(audit_id):
    """Get a specific audit log entry."""
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT audit_id, event_type, entity_type, entity_id, user_id, 
                   timestamp, data_json, signature, created_at
            FROM AuditLog WHERE audit_id = ?
        """, (audit_id,)).fetchone()
        
        if not row:
            return jsonify({"error": "Audit log not found"}), 404
        
        return jsonify({
            "audit_id": row[0],
            "event_type": row[1],
            "entity_type": row[2],
            "entity_id": row[3],
            "user_id": row[4],
            "timestamp": row[5],
            "data": row[6],
            "signature": row[7][:16] + "...",  # Truncate for security
            "created_at": row[8]
        })
    finally:
        conn.close()

@audit_bp.route('/audit/<int:audit_id>/verify', methods=['GET'])
def verify_audit_log(audit_id):
    """Verify audit log signature to detect tampering."""
    audit = get_audit_logger()
    is_valid = audit.verify(audit_id)
    
    return jsonify({
        "audit_id": audit_id,
        "valid": is_valid,
        "message": "Signature valid" if is_valid else "⚠️ Tamper detected!"
    })

@audit_bp.route('/audit/verify-all', methods=['POST'])
def verify_all_logs():
    """Verify all recent audit logs for integrity checking."""
    try:
        limit = request.json.get('limit', 1000) if request.json else 1000
        audit = get_audit_logger()
        results = audit.verify_all(limit)
        
        return jsonify(results)
    except Exception as e:
        logger.error("audit_verify_all_failed", error=str(e))
        return jsonify({"error": str(e)}), 500

@audit_bp.route('/audit', methods=['GET'])
def list_audit_logs():
    """List audit logs with optional filters."""
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id')
    event_type = request.args.get('event_type')
    limit = int(request.args.get('limit', 100))
    
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
        
        return jsonify({
            "count": len(logs),
            "logs": logs
        })
    finally:
        conn.close()

@audit_bp.route('/audit/stats', methods=['GET'])
def get_audit_stats():
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
        
        return jsonify({
            "total_logs": total,
            "recent_24h": recent,
            "by_entity_type": {row[0]: row[1] for row in by_entity},
            "by_event_type": {row[0]: row[1] for row in by_event}
        })
    finally:
        conn.close()
