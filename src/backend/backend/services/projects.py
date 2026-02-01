from typing import Optional, Dict, Any, List
from backend.core.database import get_db_connection
from backend.core.logger import get_logger

logger = get_logger(__name__)

class GenericError(Exception): pass
class NotFoundError(GenericError): pass
class ConflictError(GenericError): pass

from backend.core.interfaces import IEventBus

class ProjectService:
    def __init__(self, event_bus: Optional[IEventBus] = None):
        self.event_bus = event_bus

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
                # No actual updates, but we might want to just bump version?
                # For now, require at least one update or just force bump
                pass

            set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
            if set_clause:
                set_clause += ", "
            
            # Always increment version
            sql = f"UPDATE Projects SET {set_clause} version = version + 1 WHERE project_id = ? AND version = ?"
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
            
            updated_project = self.get_project(project_id)
            
            if self.event_bus and updated_project:
                self.event_bus.publish("project_updated", updated_project)
                
            return updated_project
            
        finally:
            conn.close()
