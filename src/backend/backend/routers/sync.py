"""
Synchronization API Endpoints

Provides REST API for bidirectional data synchronization between C# plugin and Python backend.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from ..models.sync_event import SyncEvent, SyncChangeset, SyncConflict, SyncResult
from ..services.sync_service import sync_service
from ..core.security import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("/push", response_model=SyncResult, dependencies=[Depends(verify_token)])
async def push_changes(changeset: SyncChangeset):
    """
    Push changes from client to server.
    
    The client sends a batch of changes it has made locally.
    Server applies changes and detects conflicts.
    
    Returns:
        SyncResult with number of applied changes and any conflicts
    """
    try:
        logger.info(f"Pushing {len(changeset.changes)} changes from client")
        
        applied_count, conflicts = sync_service.push_changes(
            changeset.changes,
            source="plugin"
        )
        
        return SyncResult(
            success=True,
            pushed_count=applied_count,
            pulled_count=0,
            conflicts=conflicts,
            message=f"Pushed {applied_count} changes, {len(conflicts)} conflicts detected"
        )
    
    except Exception as e:
        logger.error(f"Error pushing changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pull", response_model=List[SyncEvent], dependencies=[Depends(verify_token)])
async def pull_changes(
    since: str,
    entity_type: Optional[str] = None
):
    """
    Pull changes from server since a given timestamp.
    
    The client requests all changes that happened after its last sync.
    
    Args:
        since: ISO 8601 timestamp (e.g., "2026-02-17T09:00:00Z")
        entity_type: Optional filter by entity type
        
    Returns:
        List of sync events that occurred after the timestamp
    """
    try:
        # Parse timestamp
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        
        logger.info(f"Pulling changes since {since_dt}")
        
        changes = sync_service.get_changes_since(
            since=since_dt,
            entity_type=entity_type
        )
        
        # Filter out changes from the same source (plugin) to avoid echo
        changes = [c for c in changes if c.source != "plugin"]
        
        logger.info(f"Returning {len(changes)} changes")
        return changes
    
    except ValueError as e:
        logger.error(f"Invalid timestamp format: {since}")
        raise HTTPException(status_code=400, detail=f"Invalid timestamp format: {e}")
    except Exception as e:
        logger.error(f"Error pulling changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve-conflict", response_model=SyncEvent, dependencies=[Depends(verify_token)])
async def resolve_conflict(
    conflict: SyncConflict,
    strategy: str = "last_write_wins",
    chosen_version: Optional[str] = None
):
    """
    Resolve a synchronization conflict.
    
    Args:
        conflict: The conflict to resolve
        strategy: "last_write_wins" (automatic) or "manual" (requires chosen_version)
        chosen_version: For manual resolution, "local" or "remote"
        
    Returns:
        The winning SyncEvent that was applied
    """
    try:
        logger.info(f"Resolving conflict for {conflict.entity_type}:{conflict.entity_id} using {strategy}")
        
        winner = sync_service.resolve_conflict(
            conflict=conflict,
            strategy=strategy,
            chosen_version=chosen_version
        )
        
        return winner
    
    except ValueError as e:
        logger.error(f"Invalid conflict resolution: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resolving conflict: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{entity_type}/{entity_id}", response_model=List[SyncEvent], dependencies=[Depends(verify_token)])
async def get_entity_history(entity_type: str, entity_id: str):
    """
    Get complete change history for an entity.
    
    Args:
        entity_type: Type of entity (e.g., "project")
        entity_id: Unique identifier of the entity
        
    Returns:
        List of all sync events for this entity, ordered by timestamp
    """
    try:
        history = sync_service.get_entity_history(entity_type, entity_id)
        logger.info(f"Retrieved {len(history)} events for {entity_type}:{entity_id}")
        return history
    
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
