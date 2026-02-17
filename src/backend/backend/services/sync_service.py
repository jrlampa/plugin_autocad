"""
Data Synchronization Service

Handles bidirectional synchronization of data between C# plugin and Python backend.
Implements conflict detection and resolution strategies.
"""
import logging
from datetime import datetime
from typing import List, Optional, Tuple
from ..models.sync_event import SyncEvent, SyncConflict, SyncResult

logger = logging.getLogger(__name__)


class SyncService:
    """
    Service for managing data synchronization between client and server.
    
    Implements:
    - Push/pull changes
    - Conflict detection
    - Conflict resolution (last-write-wins, manual)
    - Change history tracking
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize sync service.
        
        Args:
            db_connection: Optional database connection for persistence
        """
        self.db = db_connection
        # In-memory storage for MVP (replace with DB in production)
        self._events: List[SyncEvent] = []
        self._event_id_counter = 1
        
    def push_changes(self, changes: List[SyncEvent], source: str = "plugin") -> Tuple[int, List[SyncConflict]]:
        """
        Push changes from client to server.
        
        Args:
            changes: List of sync events to push
            source: Source of changes ("plugin" or "backend")
            
        Returns:
            Tuple of (number of changes applied, list of conflicts detected)
        """
        applied_count = 0
        conflicts = []
        
        for change in changes:
            # Set source
            change.source = source
            
            # Check for conflicts
            conflict = self._detect_conflict(change)
            
            if conflict:
                conflicts.append(conflict)
                logger.warning(f"Conflict detected for {change.entity_type}:{change.entity_id}")
            else:
                # Apply change
                change.id = self._event_id_counter
                self._event_id_counter += 1
                self._events.append(change)
                applied_count += 1
                logger.debug(f"Applied change: {change.action} {change.entity_type}:{change.entity_id}")
        
        return applied_count, conflicts
    
    def pull_changes(self, since: datetime, source_filter: Optional[str] = None) -> List[SyncEvent]:
        """
        Pull changes from server since a given timestamp.
        
        Args:
            since: Get changes after this timestamp
            source_filter: Only get changes from this source (optional)
            
        Returns:
            List of sync events that occurred after the timestamp
        """
        changes = [
            event for event in self._events
            if event.timestamp > since
        ]
        
        if source_filter:
            changes = [e for e in changes if e.source == source_filter]
        
        logger.debug(f"Pulled {len(changes)} changes since {since}")
        return changes
    
    def get_changes_since(self, since: datetime, entity_type: Optional[str] = None) -> List[SyncEvent]:
        """
        Get all changes since a timestamp, optionally filtered by entity type.
        
        Args:
            since: Timestamp to get changes after
            entity_type: Optional filter by entity type
            
        Returns:
            List of matching sync events
        """
        changes = [
            event for event in self._events
            if event.timestamp > since
        ]
        
        if entity_type:
            changes = [e for e in changes if e.entity_type == entity_type]
        
        return changes
    
    def _detect_conflict(self, incoming_change: SyncEvent) -> Optional[SyncConflict]:
        """
        Detect if an incoming change conflicts with existing changes.
        
        A conflict occurs when:
        - Same entity has been modified
        - Timestamps are close (concurrent modification)
        - Different sources
        
        Args:
            incoming_change: The change to check for conflicts
            
        Returns:
            SyncConflict if conflict detected, None otherwise
        """
        # Find existing changes for the same entity
        existing_changes = [
            e for e in self._events
            if e.entity_type == incoming_change.entity_type
            and e.entity_id == incoming_change.entity_id
            and e.source != incoming_change.source
        ]
        
        if not existing_changes:
            return None
        
        # Check for recent conflicting changes (within 5 minutes)
        latest_change = max(existing_changes, key=lambda e: e.timestamp)
        time_diff = abs((incoming_change.timestamp - latest_change.timestamp).total_seconds())
        
        if time_diff < 300:  # 5 minutes threshold
            return SyncConflict(
                entity_type=incoming_change.entity_type,
                entity_id=incoming_change.entity_id,
                local_change=incoming_change,
                remote_change=latest_change
            )
        
        return None
    
    def resolve_conflict(
        self, 
        conflict: SyncConflict, 
        strategy: str = "last_write_wins",
        chosen_version: Optional[str] = None
    ) -> SyncEvent:
        """
        Resolve a conflict using specified strategy.
        
        Args:
            conflict: The conflict to resolve
            strategy: Resolution strategy ("last_write_wins" or "manual")
            chosen_version: For manual resolution, "local" or "remote"
            
        Returns:
            The winning SyncEvent
        """
        if strategy == "last_write_wins":
            # Choose the most recent change
            if conflict.local_change.timestamp > conflict.remote_change.timestamp:
                winner = conflict.local_change
                logger.info(f"LWW: Local wins for {conflict.entity_type}:{conflict.entity_id}")
            else:
                winner = conflict.remote_change
                logger.info(f"LWW: Remote wins for {conflict.entity_type}:{conflict.entity_id}")
            
            # Apply the winning change
            winner.id = self._event_id_counter
            self._event_id_counter += 1
            self._events.append(winner)
            return winner
            
        elif strategy == "manual" and chosen_version:
            # Manual resolution
            winner = conflict.local_change if chosen_version == "local" else conflict.remote_change
            winner.id = self._event_id_counter
            self._event_id_counter += 1
            self._events.append(winner)
            logger.info(f"Manual: {chosen_version} wins for {conflict.entity_type}:{conflict.entity_id}")
            return winner
        
        else:
            raise ValueError(f"Unknown strategy or missing chosen_version: {strategy}")
    
    def get_entity_history(self, entity_type: str, entity_id: str) -> List[SyncEvent]:
        """
        Get complete history of changes for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            
        Returns:
            List of all sync events for this entity, ordered by timestamp
        """
        history = [
            e for e in self._events
            if e.entity_type == entity_type and e.entity_id == entity_id
        ]
        return sorted(history, key=lambda e: e.timestamp)
    
    def clear_old_events(self, before: datetime) -> int:
        """
        Remove events older than a specified timestamp (garbage collection).
        
        Args:
            before: Remove events before this timestamp
            
        Returns:
            Number of events removed
        """
        initial_count = len(self._events)
        self._events = [e for e in self._events if e.timestamp >= before]
        removed = initial_count - len(self._events)
        logger.info(f"Cleared {removed} old sync events")
        return removed


# Global sync service instance
sync_service = SyncService()
