"""
Async Task Processing with Celery (Foundation)

This module provides the foundation for async task processing using Celery.
In production, configure with Redis broker and scale workers horizontally.

Installation:
    pip install celery[redis]
    
Configuration:
    Set CELERY_BROKER_URL environment variable (default: redis://localhost:6379/0)
    
Usage:
    celery -A backend.celery_app worker --loglevel=info
"""
import os
import logging
from celery import Celery
from datetime import datetime

logger = logging.getLogger(__name__)

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Initialize Celery app
celery_app = Celery(
    "sisrua",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["backend.tasks"]  # Import tasks module
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,  # Disable prefetching for long tasks
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory management)
)


# Example tasks (implement in backend/tasks.py)
@celery_app.task(bind=True, max_retries=3)
def process_osm_async(self, job_id: str, request_data: dict):
    """
    Process OSM data asynchronously.
    
    Args:
        job_id: Unique job identifier
        request_data: OSM request parameters
        
    Returns:
        Result data or raises exception for retry
    """
    try:
        logger.info(f"Processing OSM job {job_id}")
        
        # Import here to avoid circular dependencies
        from backend.services.geojson import prepare_osm_compute
        
        # Process (this can be slow)
        result = prepare_osm_compute(request_data)
        
        logger.info(f"OSM job {job_id} completed successfully")
        return result
    
    except Exception as exc:
        logger.error(f"OSM job {job_id} failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def process_elevation_async(self, job_id: str, coordinates: list):
    """
    Process elevation queries asynchronously.
    
    Args:
        job_id: Unique job identifier
        coordinates: List of (lat, lon) tuples
        
    Returns:
        Elevation data
    """
    try:
        logger.info(f"Processing elevation job {job_id} for {len(coordinates)} points")
        
        from backend.services.elevation import ElevationService
        
        elevation_service = ElevationService()
        results = [elevation_service.get_elevation(lat, lon) for lat, lon in coordinates]
        
        logger.info(f"Elevation job {job_id} completed")
        return results
    
    except Exception as exc:
        logger.error(f"Elevation job {job_id} failed: {exc}")
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@celery_app.task
def cleanup_old_cache(before_timestamp: str):
    """
    Cleanup old cache entries (scheduled task).
    
    Args:
        before_timestamp: ISO timestamp to clean before
    """
    try:
        from datetime import datetime
        from backend.services.sync_service import sync_service
        
        before_dt = datetime.fromisoformat(before_timestamp)
        removed = sync_service.clear_old_events(before=before_dt)
        
        logger.info(f"Cleaned up {removed} old events")
        return {"removed": removed}
    
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        return {"error": str(exc)}


# Periodic task configuration (using Celery Beat)
celery_app.conf.beat_schedule = {
    "cleanup-old-cache-daily": {
        "task": "backend.celery_app.cleanup_old_cache",
        "schedule": 86400.0,  # Daily (24 hours in seconds)
        "args": [(datetime.utcnow().isoformat(),)]
    },
}


# Health check for Celery workers
@celery_app.task
def health_check():
    """Simple health check task"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    """
    Run Celery worker:
        python -m backend.celery_app worker --loglevel=info
        
    Run Celery beat (scheduler):
        python -m backend.celery_app beat --loglevel=info
    """
    celery_app.start()
