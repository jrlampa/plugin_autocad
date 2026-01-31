"""
Database Migration System for sisRUA
=====================================
Provides backward-compatible schema migrations with version tracking.
Ensures zero-downtime upgrades by using non-destructive ALTER statements.

Usage:
    from backend.core.migrations import migrate_database
    migrate_database()  # Auto-applies pending migrations
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

# Database path (same as seed.py)
DB_PATH = Path(os.environ.get("LOCALAPPDATA", ".")) / "sisRUA" / "projects.db"

# Current schema version
CURRENT_VERSION = 2

# Migration definitions: version -> (description, sql_statements)
# Each migration must be backward-compatible (ADD columns, CREATE tables, etc.)
MIGRATIONS = {
    1: (
        "v0.5.0 - Add indexes for query optimization",
        [
            """
            CREATE INDEX IF NOT EXISTS idx_cadfeatures_project_id 
            ON CadFeatures(project_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_cadfeatures_feature_type 
            ON CadFeatures(feature_type)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_cadfeatures_project_type 
            ON CadFeatures(project_id, feature_type)
            """,
        ]
    ),
    2: (
        "v0.5.0 - Add color, elevation, and slope columns",
        [
            "ALTER TABLE CadFeatures ADD COLUMN color TEXT",
            "ALTER TABLE CadFeatures ADD COLUMN elevation REAL",
            "ALTER TABLE CadFeatures ADD COLUMN slope REAL",
        ]
    ),
}


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get current schema version from database."""
    cursor = conn.cursor()
    
    # Create schema_version table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    )
    """)
    conn.commit()
    
    # Get latest version
    cursor.execute("SELECT MAX(version) FROM schema_version")
    result = cursor.fetchone()[0]
    return result or 0


def apply_migration(conn: sqlite3.Connection, version: int, description: str, statements: list):
    """Apply a single migration."""
    cursor = conn.cursor()
    
    print(f"  Applying migration {version}: {description}")
    
    for sql in statements:
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError as e:
            # Handle "already exists" and "duplicate column name" gracefully for idempotency
            err_msg = str(e).lower()
            if "already exists" in err_msg or "duplicate column name" in err_msg:
                print(f"    (skipped - already exists: {e})")
            else:
                raise
    
    # Record migration
    cursor.execute(
        "INSERT INTO schema_version (version, description) VALUES (?, ?)",
        (version, description)
    )
    conn.commit()
    print(f"    ✓ Migration {version} applied successfully")


def migrate_database(db_path: Path = None) -> int:
    """
    Apply all pending migrations to the database.
    
    Returns:
        Number of migrations applied
    """
    path = db_path or DB_PATH
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if not path.exists():
        print(f"[migrations] Database not found: {path}")
        print("[migrations] Skipping migrations (database will be created by seed.py)")
        return 0
    
    print(f"[migrations] Checking database: {path}")
    
    conn = sqlite3.connect(str(path))
    try:
        current_version = get_schema_version(conn)
        print(f"[migrations] Current schema version: {current_version}")
        
        applied = 0
        for version in sorted(MIGRATIONS.keys()):
            if version > current_version:
                description, statements = MIGRATIONS[version]
                apply_migration(conn, version, description, statements)
                applied += 1
        
        if applied == 0:
            print("[migrations] Database is up to date")
        else:
            print(f"[migrations] Applied {applied} migration(s)")
        
        return applied
        
    finally:
        conn.close()


def check_migration_status(db_path: Path = None) -> dict:
    """
    Check migration status without applying changes.
    
    Returns:
        dict with current_version, target_version, pending_migrations
    """
    path = db_path or DB_PATH
    
    if not path.exists():
        return {
            "database_exists": False,
            "current_version": 0,
            "target_version": CURRENT_VERSION,
            "pending_migrations": list(MIGRATIONS.keys()),
        }
    
    conn = sqlite3.connect(str(path))
    try:
        current = get_schema_version(conn)
        pending = [v for v in sorted(MIGRATIONS.keys()) if v > current]
        
        return {
            "database_exists": True,
            "current_version": current,
            "target_version": CURRENT_VERSION,
            "pending_migrations": pending,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    # Run migrations from command line
    print("=" * 50)
    print("sisRUA Database Migration Tool")
    print("=" * 50)
    
    status = check_migration_status()
    print(f"\nStatus: {status}")
    
    if status.get("pending_migrations"):
        print("\nApplying migrations...")
        migrate_database()
    else:
        print("\nNo pending migrations.")
