"""
Tests for Data Synchronization Service

Tests push/pull operations, conflict detection, and resolution strategies.
"""
import pytest
from datetime import datetime, timedelta
from backend.models.sync_event import SyncEvent, SyncChangeset, SyncConflict
from backend.services.sync_service import SyncService


@pytest.fixture
def sync_service():
    """Create a fresh sync service for each test"""
    return SyncService()


def test_create_sync_event():
    """Test creating a sync event"""
    event = SyncEvent(
        entity_type="project",
        entity_id="proj_123",
        action="create",
        data={"name": "Test Project"},
        source="plugin"
    )
    
    assert event.entity_type == "project"
    assert event.entity_id == "proj_123"
    assert event.action == "create"
    assert event.source == "plugin"


def test_push_changes(sync_service):
    """Test pushing changes to server"""
    changes = [
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="create",
            data={"name": "Project 1"}
        )
    ]
    
    applied, conflicts = sync_service.push_changes(changes, source="plugin")
    
    assert applied == 1
    assert len(conflicts) == 0


def test_pull_changes(sync_service):
    """Test pulling changes from server"""
    # Push some changes first
    now = datetime.utcnow()
    changes = [
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="create",
            data={"name": "Project 1"},
            timestamp=now + timedelta(seconds=10)
        )
    ]
    
    sync_service.push_changes(changes, source="backend")
    
    # Pull changes since before they were pushed
    pulled = sync_service.pull_changes(since=now)
    
    assert len(pulled) == 1
    assert pulled[0].entity_id == "proj_1"


def test_get_changes_since(sync_service):
    """Test getting changes after a specific timestamp"""
    now = datetime.utcnow()
    
    # Add changes at different times
    changes = [
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="create",
            data={"name": "Project 1"},
            timestamp=now + timedelta(seconds=5)
        ),
        SyncEvent(
            entity_type="project",
            entity_id="proj_2",
            action="create",
            data={"name": "Project 2"},
            timestamp=now + timedelta(seconds=15)
        )
    ]
    
    sync_service.push_changes(changes)
    
    # Get changes since 10 seconds from now
    recent = sync_service.get_changes_since(since=now + timedelta(seconds=10))
    
    assert len(recent) == 1
    assert recent[0].entity_id == "proj_2"


def test_conflict_detection(sync_service):
    """Test that conflicts are detected"""
    now = datetime.utcnow()
    
    # Backend makes a change
    backend_change = SyncEvent(
        entity_type="project",
        entity_id="proj_1",
        action="update",
        data={"name": "Backend Version"},
        timestamp=now,
        source="backend"
    )
    sync_service.push_changes([backend_change], source="backend")
    
    # Plugin makes a conflicting change (within 5 minutes)
    plugin_change = SyncEvent(
        entity_type="project",
        entity_id="proj_1",
        action="update",
        data={"name": "Plugin Version"},
        timestamp=now + timedelta(seconds=60),  # 1 minute later
        source="plugin"
    )
    
    applied, conflicts = sync_service.push_changes([plugin_change], source="plugin")
    
    assert applied == 0
    assert len(conflicts) == 1
    assert conflicts[0].entity_id == "proj_1"


def test_last_write_wins(sync_service):
    """Test last-write-wins conflict resolution"""
    now = datetime.utcnow()
    
    conflict = SyncConflict(
        entity_type="project",
        entity_id="proj_1",
        local_change=SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="update",
            data={"name": "Local"},
            timestamp=now + timedelta(seconds=10)
        ),
        remote_change=SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="update",
            data={"name": "Remote"},
            timestamp=now
        )
    )
    
    winner = sync_service.resolve_conflict(conflict, strategy="last_write_wins")
    
    # Local is more recent, should win
    assert winner.data["name"] == "Local"


def test_manual_conflict_resolution(sync_service):
    """Test manual conflict resolution"""
    conflict = SyncConflict(
        entity_type="project",
        entity_id="proj_1",
        local_change=SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="update",
            data={"name": "Local"}
        ),
        remote_change=SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="update",
            data={"name": "Remote"}
        )
    )
    
    # Choose remote manually
    winner = sync_service.resolve_conflict(
        conflict, 
        strategy="manual", 
        chosen_version="remote"
    )
    
    assert winner.data["name"] == "Remote"


def test_sync_with_no_conflicts(sync_service):
    """Test synchronization when there are no conflicts"""
    changes = [
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="create",
            data={"name": "Project 1"}
        ),
        SyncEvent(
            entity_type="project",
            entity_id="proj_2",
            action="create",
            data={"name": "Project 2"}
        )
    ]
    
    applied, conflicts = sync_service.push_changes(changes)
    
    assert applied == 2
    assert len(conflicts) == 0


def test_sync_with_multiple_conflicts(sync_service):
    """Test handling multiple conflicts"""
    now = datetime.utcnow()
    
    # Backend changes
    backend_changes = [
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="update",
            data={"name": "Backend 1"},
            timestamp=now,
            source="backend"
        ),
        SyncEvent(
            entity_type="project",
            entity_id="proj_2",
            action="update",
            data={"name": "Backend 2"},
            timestamp=now,
            source="backend"
        )
    ]
    sync_service.push_changes(backend_changes, source="backend")
    
    # Plugin conflicting changes
    plugin_changes = [
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="update",
            data={"name": "Plugin 1"},
            timestamp=now + timedelta(seconds=30)
        ),
        SyncEvent(
            entity_type="project",
            entity_id="proj_2",
            action="update",
            data={"name": "Plugin 2"},
            timestamp=now + timedelta(seconds=30)
        )
    ]
    
    applied, conflicts = sync_service.push_changes(plugin_changes, source="plugin")
    
    assert applied == 0
    assert len(conflicts) == 2


def test_empty_changeset(sync_service):
    """Test pushing an empty changeset"""
    applied, conflicts = sync_service.push_changes([])
    
    assert applied == 0
    assert len(conflicts) == 0


def test_concurrent_modifications(sync_service):
    """Test detection of concurrent modifications"""
    now = datetime.utcnow()
    
    # Two changes to same entity at nearly the same time
    change1 = SyncEvent(
        entity_type="project",
        entity_id="proj_1",
        action="update",
        data={"name": "Version 1"},
        timestamp=now,
        source="backend"
    )
    
    change2 = SyncEvent(
        entity_type="project",
        entity_id="proj_1",
        action="update",
        data={"name": "Version 2"},
        timestamp=now + timedelta(seconds=30),
        source="plugin"
    )
    
    sync_service.push_changes([change1], source="backend")
    applied, conflicts = sync_service.push_changes([change2], source="plugin")
    
    assert len(conflicts) == 1
    assert conflicts[0].entity_type == "project"


def test_get_entity_history(sync_service):
    """Test retrieving complete history of an entity"""
    now = datetime.utcnow()
    
    changes = [
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="create",
            data={"name": "Initial"},
            timestamp=now
        ),
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="update",
            data={"name": "Updated"},
            timestamp=now + timedelta(seconds=10)
        ),
        SyncEvent(
            entity_type="project",
            entity_id="proj_2",
            action="create",
            data={"name": "Other Project"},
            timestamp=now + timedelta(seconds=5)
        )
    ]
    
    sync_service.push_changes(changes)
    
    history = sync_service.get_entity_history("project", "proj_1")
    
    assert len(history) == 2
    assert history[0].action == "create"
    assert history[1].action == "update"


def test_clear_old_events(sync_service):
    """Test garbage collection of old events"""
    now = datetime.utcnow()
    
    changes = [
        SyncEvent(
            entity_type="project",
            entity_id="proj_1",
            action="create",
            timestamp=now - timedelta(days=10)
        ),
        SyncEvent(
            entity_type="project",
            entity_id="proj_2",
            action="create",
            timestamp=now
        )
    ]
    
    sync_service.push_changes(changes)
    
    # Clear events older than 5 days
    removed = sync_service.clear_old_events(before=now - timedelta(days=5))
    
    assert removed == 1
