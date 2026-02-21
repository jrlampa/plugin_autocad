"""
Audit Log API Routes
REST endpoints for creating and querying cryptographic audit logs.
Converted to FastAPI APIRouter.

Segurança (ISO 27001): todos os endpoints requerem autenticação via X-SisRua-Token.
"""
import csv
import io
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from backend.core.audit import get_audit_logger
from backend.core.auth import require_token
from backend.core.database import get_db_connection
from backend.core.logger import get_logger
from backend.core.utils import sanitize_jsonable
from typing import Optional

# Comprimento máximo para campos de texto livres (mitigação de DoS/injeção)
_MAX_FIELD_LEN = 256

audit_bp = APIRouter()
logger = get_logger(__name__)


def _safe_str(val, max_len: int = _MAX_FIELD_LEN) -> Optional[str]:
    """Sanitiza e trunca um valor de string para armazenamento seguro."""
    if val is None:
        return None
    return str(val)[:max_len]


@audit_bp.post("/audit", status_code=201)
async def create_audit_log(request: Request, _: None = Depends(require_token)):
    """Cria entrada de log de auditoria (chamado pelo plugin C# ou outros serviços)."""
    try:
        raw = await request.json()
        audit = get_audit_logger()

        audit_id = audit.log(
            event_type=_safe_str(raw["event_type"]),
            entity_type=_safe_str(raw["entity_type"]),
            entity_id=_safe_str(raw.get("entity_id")),
            data=sanitize_jsonable(raw.get("data", {})),
            user_id=_safe_str(raw.get("user_id")),
        )

        return {"audit_id": audit_id}
    except KeyError as e:
        logger.error("audit_create_missing_field", field=str(e))
        raise HTTPException(status_code=400, detail=f"Campo obrigatório ausente: {e}")
    except Exception as e:
        logger.error("audit_create_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@audit_bp.get("/audit")
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    _: None = Depends(require_token),
):
    """Lista logs de auditoria com filtros opcionais."""
    audit = get_audit_logger()
    logs = audit.list_logs(
        _safe_str(entity_type),
        _safe_str(entity_id),
        _safe_str(event_type),
        limit,
    )
    return {"count": len(logs), "logs": logs}


# NOTE: /audit/stats and /audit/export/compliance MUST be registered before
# /audit/{audit_id} so Starlette's first-match router does not treat "stats"
# or "export" as the integer {audit_id} param, which would return 422.

@audit_bp.get("/audit/stats")
async def get_audit_stats(_: None = Depends(require_token)):
    """Retorna estatísticas agregadas do log de auditoria."""
    conn = get_db_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM AuditLog").fetchone()[0]

        by_entity = conn.execute(
            "SELECT entity_type, COUNT(*) FROM AuditLog GROUP BY entity_type"
        ).fetchall()

        by_event = conn.execute(
            "SELECT event_type, COUNT(*) FROM AuditLog GROUP BY event_type"
        ).fetchall()

        day_ago = time.time() - 86400
        recent = conn.execute(
            "SELECT COUNT(*) FROM AuditLog WHERE timestamp > ?", (day_ago,)
        ).fetchone()[0]

        return {
            "total_logs": total,
            "recent_24h": recent,
            "by_entity_type": {row[0]: row[1] for row in by_entity},
            "by_event_type": {row[0]: row[1] for row in by_event},
        }
    finally:
        conn.close()


@audit_bp.get("/valuation/summary")
async def get_valuation_summary(_: None = Depends(require_token)):
    """
    Agrega métricas de mileagem (Km mapeados) a partir dos logs de auditoria.
    Essencial para comprovar o valor do ativo durante due diligence.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT data_json FROM AuditLog
            WHERE event_type = 'UPDATE' AND entity_type = 'Project'
            """
        ).fetchall()

        project_mileages: dict = {}
        extra_mileage = 0.0

        for row in rows:
            try:
                data = json.loads(row[0])
                p_id = data.get("project_id")
                raw_m = data.get("mileage_km", 0.0)
                m = float(raw_m) if isinstance(raw_m, (int, float)) else 0.0
                if p_id:
                    project_mileages[str(p_id)] = m
                else:
                    extra_mileage += m
            except Exception:
                continue

        total_mileage = extra_mileage + sum(project_mileages.values())

        return {
            "total_urban_assets_mapped_km": round(total_mileage, 2),
            "valuation_metric": "Price per Km",
            "estimated_asset_value_usd": round(total_mileage * 500, 2),
            "compliance_status": "ISO 27001 Compliant",
            "data_currency": "Verifiable via Cryptographic Audit Trail",
        }
    finally:
        conn.close()


@audit_bp.get("/audit/export/compliance")
async def export_audit_logs(_: None = Depends(require_token)):
    """
    Gera pacote de evidências para auditoria externa (Autodesk/ISO).
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT audit_id, event_type, entity_type, entity_id, user_id, timestamp, signature
            FROM AuditLog ORDER BY timestamp DESC LIMIT 5000
            """
        ).fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["AuditID", "Event", "Entity", "EntityID", "User", "Timestamp", "Signature_Short"]
        )
        for r in rows:
            writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6][:10]])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.read().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=sisrua_compliance_evidence.csv"
            },
        )
    finally:
        conn.close()


@audit_bp.post("/audit/verify-all")
async def verify_all_logs(request: Request, _: None = Depends(require_token)):
    """Verifica a integridade de todos os logs de auditoria recentes."""
    try:
        body = await request.body()
        data = json.loads(body) if body else {}
        limit = int(data.get("limit", 1000))
        limit = max(1, min(limit, 10000))
        audit = get_audit_logger()
        return audit.verify_all(limit)
    except Exception as e:
        logger.error("audit_verify_all_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Dynamic routes AFTER all static routes so Starlette first-match works correctly.

@audit_bp.get("/audit/{audit_id}")
async def get_audit_log(audit_id: int, _: None = Depends(require_token)):
    """Retorna uma entrada específica do log de auditoria."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT audit_id, event_type, entity_type, entity_id, user_id,
                   timestamp, data_json, signature, created_at
            FROM AuditLog WHERE audit_id = ?
            """,
            (audit_id,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Log de auditoria não encontrado")

        return {
            "audit_id": row[0],
            "event_type": row[1],
            "entity_type": row[2],
            "entity_id": row[3],
            "user_id": row[4],
            "timestamp": row[5],
            "data": row[6],
            "signature": row[7][:16] + "...",  # Truncado por segurança
            "created_at": row[8],
        }
    finally:
        conn.close()


@audit_bp.get("/audit/{audit_id}/verify")
async def verify_audit_log(audit_id: int, _: None = Depends(require_token)):
    """Verifica a assinatura de um log para detectar adulteração."""
    audit = get_audit_logger()
    is_valid = audit.verify(audit_id)

    return {
        "audit_id": audit_id,
        "valid": is_valid,
        "message": "Assinatura válida" if is_valid else "⚠️ Adulteração detectada!",
    }
