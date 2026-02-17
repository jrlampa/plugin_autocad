"""
Project Versioning System (Foundation)

Implements git-like versioning for projects with snapshots and rollback capability.
Each snapshot captures the complete state of a project at a point in time.

Usage:
    from backend.services.versioning import versioning_service
    
    # Create snapshot
    snapshot_id = versioning_service.create_snapshot(project_id, "Initial version")
    
    # List versions
    versions = versioning_service.list_versions(project_id)
    
    # Rollback
    versioning_service.rollback(project_id, snapshot_id)
"""
import logging
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProjectSnapshot:
    """Represents a project snapshot at a point in time"""
    
    def __init__(
        self,
        snapshot_id: str,
        project_id: str,
        state: Dict[str, Any],
        message: str,
        created_at: datetime,
        created_by: Optional[str] = None,
        parent_id: Optional[str] = None
    ):
        self.snapshot_id = snapshot_id
        self.project_id = project_id
        self.state = state
        self.message = message
        self.created_at = created_at
        self.created_by = created_by
        self.parent_id = parent_id
    
    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "project_id": self.project_id,
            "state": self.state,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "parent_id": self.parent_id
        }


class VersioningService:
    """
    Service for project versioning and rollback.
    
    Implements:
    - Snapshot creation
    - Version history
    - Rollback to any version
    - Diff between versions
    """
    
    def __init__(self, storage_backend=None):
        """
        Initialize versioning service.
        
        Args:
            storage_backend: Optional storage backend (DB, filesystem, etc.)
        """
        self.storage = storage_backend
        # In-memory storage for MVP (replace with DB in production)
        self._snapshots: Dict[str, List[ProjectSnapshot]] = {}
    
    def create_snapshot(
        self,
        project_id: str,
        message: str,
        state: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> str:
        """
        Create a snapshot of the current project state.
        
        Args:
            project_id: Project identifier
            message: Commit message
            state: Complete project state
            created_by: User who created the snapshot
            
        Returns:
            Snapshot ID (hash of state)
        """
        # Generate snapshot ID (hash of state)
        state_json = json.dumps(state, sort_keys=True)
        snapshot_id = hashlib.sha256(state_json.encode()).hexdigest()[:12]
        
        # Get parent (latest snapshot)
        parent_id = None
        if project_id in self._snapshots and self._snapshots[project_id]:
            parent_id = self._snapshots[project_id][-1].snapshot_id
        
        # Create snapshot
        snapshot = ProjectSnapshot(
            snapshot_id=snapshot_id,
            project_id=project_id,
            state=state,
            message=message,
            created_at=datetime.utcnow(),
            created_by=created_by,
            parent_id=parent_id
        )
        
        # Store
        if project_id not in self._snapshots:
            self._snapshots[project_id] = []
        self._snapshots[project_id].append(snapshot)
        
        logger.info(f"Created snapshot {snapshot_id} for project {project_id}: {message}")
        return snapshot_id
    
    def list_versions(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List all snapshots for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of snapshot metadata (without full state)
        """
        if project_id not in self._snapshots:
            return []
        
        return [
            {
                "snapshot_id": s.snapshot_id,
                "message": s.message,
                "created_at": s.created_at.isoformat(),
                "created_by": s.created_by,
                "parent_id": s.parent_id
            }
            for s in self._snapshots[project_id]
        ]
    
    def get_snapshot(self, project_id: str, snapshot_id: str) -> Optional[ProjectSnapshot]:
        """
        Get a specific snapshot.
        
        Args:
            project_id: Project identifier
            snapshot_id: Snapshot identifier
            
        Returns:
            ProjectSnapshot or None if not found
        """
        if project_id not in self._snapshots:
            return None
        
        for snapshot in self._snapshots[project_id]:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        
        return None
    
    def rollback(self, project_id: str, snapshot_id: str) -> Dict[str, Any]:
        """
        Rollback project to a previous snapshot.
        
        Args:
            project_id: Project identifier
            snapshot_id: Snapshot to rollback to
            
        Returns:
            The restored project state
        """
        snapshot = self.get_snapshot(project_id, snapshot_id)
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found for project {project_id}")
        
        logger.info(f"Rolling back project {project_id} to snapshot {snapshot_id}")
        
        # In production, this would apply the state to the database
        # For now, return the state
        return snapshot.state
    
    def diff(
        self,
        project_id: str,
        snapshot_id1: str,
        snapshot_id2: str
    ) -> Dict[str, Any]:
        """
        Calculate diff between two snapshots.
        
        Args:
            project_id: Project identifier
            snapshot_id1: First snapshot
            snapshot_id2: Second snapshot
            
        Returns:
            Dictionary showing differences
        """
        snap1 = self.get_snapshot(project_id, snapshot_id1)
        snap2 = self.get_snapshot(project_id, snapshot_id2)
        
        if not snap1 or not snap2:
            raise ValueError("One or both snapshots not found")
        
        # Simple diff (in production, use more sophisticated diff)
        return {
            "snapshot1": snapshot_id1,
            "snapshot2": snapshot_id2,
            "changes": self._calculate_diff(snap1.state, snap2.state)
        }
    
    def _calculate_diff(self, state1: dict, state2: dict) -> list:
        """Calculate simple diff between two states"""
        changes = []
        
        # Added keys
        for key in state2:
            if key not in state1:
                changes.append({"type": "added", "key": key, "value": state2[key]})
        
        # Removed keys
        for key in state1:
            if key not in state2:
                changes.append({"type": "removed", "key": key, "value": state1[key]})
        
        # Modified keys
        for key in state1:
            if key in state2 and state1[key] != state2[key]:
                changes.append({
                    "type": "modified",
                    "key": key,
                    "old_value": state1[key],
                    "new_value": state2[key]
                })
        
        return changes
    
    def get_history(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get complete version history for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of snapshots in chronological order
        """
        return self.list_versions(project_id)


# Global versioning service instance
versioning_service = VersioningService()
