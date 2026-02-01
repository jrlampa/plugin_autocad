import os
import sqlite3
from pathlib import Path
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Single source of truth for DB Path
DB_PATH = Path(os.environ.get("LOCALAPPDATA", ".")) / "sisRUA" / "projects.db"

def get_db_path() -> Path:
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH

def get_db_connection(db_path: Path = None) -> sqlite3.Connection:
    """
    Returns a configured SQLite connection with WAL mode enabled.
    """
    path = db_path or get_db_path()
    
    conn = sqlite3.connect(str(path))
    
    # helper for WAL mode
    try:
        # Enable Write-Ahead Logging
        conn.execute("PRAGMA journal_mode=WAL;")
        
        # Normal sync is safe enough for most desktop apps and faster than FULL
        conn.execute("PRAGMA synchronous=NORMAL;")
        
        # Increase cache size (default is usually 2000 pages)
        conn.execute("PRAGMA cache_size=-64000;") # ~64MB
        
        # Enforce foreign keys (good practice)
        conn.execute("PRAGMA foreign_keys=ON;")
        
    except Exception as e:
        logger.error("db_config_failed", error=str(e))
        # We don't raise here to allow connection to proceed, but it's risky
        
    return conn
