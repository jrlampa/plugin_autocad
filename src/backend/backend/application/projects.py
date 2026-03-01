from typing import Optional, Dict, Any, List
import backend.services.projects as _projects_compat
from backend.shared.logger import get_logger
from backend.shared.audit import get_audit_logger

def get_db_connection():
    return _projects_compat.get_db_connection()

logger = get_logger(__name__)

class GenericError(Exception): pass
class NotFoundError(GenericError): pass
class ConflictError(GenericError): pass

from backend.shared.interfaces import IEventBus

class ProjectService:
    def __init__(self, event_bus: Optional[IEventBus] = None):
        self.event_bus = event_bus
        self.audit = get_audit_logger()

    def create_project(self, project_name: str, crs_out: str = "EPSG:31983") -> dict:
        """
        Cria um novo projeto no banco de dados.

        Args:
            project_name: Nome do projeto (obrigatório, max 255 chars).
            crs_out: CRS de saída (padrão: SIRGAS 2000 Zona 23S).

        Returns:
            Dicionário com os dados do projeto criado.
        """
        import uuid
        from datetime import datetime, timezone

        project_id = str(uuid.uuid4())
        creation_date = datetime.now(timezone.utc).isoformat()

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO Projects (project_id, project_name, crs_out, version, creation_date) VALUES (?, ?, ?, ?, ?)",
                (project_id, project_name.strip(), crs_out, 1, creation_date),
            )
            conn.commit()
        finally:
            conn.close()

        project = {
            "project_id": project_id,
            "project_name": project_name.strip(),
            "crs_out": crs_out,
            "version": 1,
            "creation_date": creation_date,
        }

        try:
            self.audit.log(
                event_type="CREATE",
                entity_type="Project",
                entity_id=project_id,
                data={"project_name": project_name, "crs_out": crs_out},
            )
        except Exception as e:
            logger.error("audit_log_failed", project_id=project_id, error=str(e))

        if self.event_bus:
            self.event_bus.publish("project_saved", project)

        return project

    def list_projects(self) -> list:
        """Retorna todos os projetos do banco de dados."""
        conn = get_db_connection()
        try:
            rows = conn.execute(
                "SELECT project_id, project_name, crs_out, version, creation_date FROM Projects ORDER BY creation_date DESC"
            ).fetchall()
            return [
                {
                    "project_id": row[0],
                    "project_name": row[1],
                    "crs_out": row[2],
                    "version": row[3],
                    "creation_date": row[4],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def delete_project(self, project_id: str) -> None:
        """
        Remove um projeto e todas as suas features do banco de dados.
        Lança NotFoundError se o projeto não existir.
        Emite evento 'project_deleted' no barramento de eventos.
        """
        conn = get_db_connection()
        try:
            # Verify existence before deletion
            row = conn.execute(
                "SELECT project_id FROM Projects WHERE project_id = ?", (project_id,)
            ).fetchone()
            if not row:
                raise NotFoundError(f"Projeto '{project_id}' não encontrado.")

            # Delete features first (cascade manual — sem FK CASCADE configurado)
            conn.execute("DELETE FROM CadFeatures WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
            conn.commit()

            try:
                self.audit.log(
                    event_type="DELETE",
                    entity_type="Project",
                    entity_id=project_id,
                    data={"project_id": project_id},
                )
            except Exception as e:
                logger.error("audit_log_failed", project_id=project_id, error=str(e))

            if self.event_bus:
                self.event_bus.publish("project_deleted", {"project_id": project_id})

        finally:
            conn.close()

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT project_id, project_name, crs_out, version, creation_date FROM Projects WHERE project_id = ?", 
                (project_id,)
            ).fetchone()
            
            if not row:
                return None
                
            return {
                "project_id": row[0],
                "project_name": row[1],
                "crs_out": row[2],
                "version": row[3],
                "creation_date": row[4]
            }
        finally:
            conn.close()

    def update_project(self, project_id: str, updates: Dict[str, Any], expected_version: int) -> Dict[str, Any]:
        """
        Updates project metadata with optimistic locking.
        Raises ConflictError if version mismatch.
        Emits 'project_updated' event on success.
        """
        conn = get_db_connection()
        try:
            # We construct the SQL dynamically based on updates, but careful with injection
            # Only allow specific fields
            allowed_fields = {"project_name", "crs_out"}
            fields_to_update = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not fields_to_update:
                # No valid fields provided — only bump the version (idempotent touch)
                pass

            # Always increment version
            sql = "UPDATE Projects SET "
            sql_parts = []
            for k in fields_to_update.keys():
                sql_parts.append(f"{k} = ?")
            
            sql += ", ".join(sql_parts)
            if sql_parts:
                sql += ", "
            
            sql += "version = version + 1 WHERE project_id = ? AND version = ?"
            params = list(fields_to_update.values()) + [project_id, expected_version]
            
            cursor = conn.execute(sql, params)
            conn.commit()
            
            if cursor.rowcount == 0:
                # Check if it exists
                exists = conn.execute("SELECT version FROM Projects WHERE project_id = ?", (project_id,)).fetchone()
                if not exists:
                    raise NotFoundError(f"Project {project_id} not found")
                else:
                    current_version = exists[0]
                    logger.warning("optimistic_lock_failure", project_id=project_id, expected=expected_version, current=current_version)
                    raise ConflictError(f"Version mismatch. Expected {expected_version}, but found {current_version}.")
            
            # Log audit event AFTER successful commit
            try:
                self.audit.log(
                    event_type="UPDATE",
                    entity_type="Project",
                    entity_id=project_id,
                    data={
                        "updates": fields_to_update,
                        "old_version": expected_version,
                        "new_version": expected_version + 1
                    }
                )
            except Exception as e:
                # Don't fail the update if audit fails, just log
                logger.error("audit_log_failed", project_id=project_id, error=str(e))
            
            updated_project = self.get_project(project_id)
            
            if self.event_bus and updated_project:
                self.event_bus.publish("project_updated", updated_project)
                
            return updated_project
            
        finally:
            conn.close()
