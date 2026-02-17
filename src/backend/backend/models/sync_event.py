"""
Sync Event Model for Data Synchronization

Tracks changes made to entities for bidirectional sync between C# plugin and Python backend.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SyncEvent(BaseModel):
    """
    Represents a change event for synchronization.
    
    Used to track modifications to entities (projects, elements, etc.)
    and synchronize them between the C# plugin and Python backend.
    """
    
    id: Optional[int] = None
    entity_type: str = Field(..., description="Type of entity (e.g., 'project', 'element')")
    entity_id: str = Field(..., description="Unique identifier of the entity")
    action: str = Field(..., description="Action performed: 'create', 'update', 'delete'")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Entity data (for create/update)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the change occurred")
    user_id: Optional[str] = Field(default=None, description="User who made the change")
    source: str = Field(default="backend", description="Origin of the change: 'backend' or 'plugin'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_type": "project",
                "entity_id": "proj_123",
                "action": "update",
                "data": {"name": "New Project Name", "status": "active"},
                "timestamp": "2026-02-17T09:00:00Z",
                "user_id": "user_456",
                "source": "plugin"
            }
        }


class SyncChangeset(BaseModel):
    """Represents a batch of changes to sync"""
    
    changes: list[SyncEvent] = Field(default_factory=list)
    client_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    
class SyncConflict(BaseModel):
    """Represents a conflict between two versions of the same entity"""
    
    entity_type: str
    entity_id: str
    local_change: SyncEvent
    remote_change: SyncEvent
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    
class SyncResult(BaseModel):
    """Result of a synchronization operation"""
    
    success: bool
    pushed_count: int = 0
    pulled_count: int = 0
    conflicts: list[SyncConflict] = Field(default_factory=list)
    message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "pushed_count": 5,
                "pulled_count": 3,
                "conflicts": [],
                "message": "Sync completed successfully"
            }
        }
