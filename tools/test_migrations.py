import sqlite3
import os
import shutil
import tempfile
from pathlib import Path
from backend.core.migrations import migrate_database, get_schema_version, CURRENT_VERSION

def test_migration_flow():
    print("--- Phase 22: Migration Idempotency & Flow Test ---")
    
    # 1. Setup temp environment
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test_projects.db"
    print(f"Using temp DB: {db_path}")

    try:
        # Scenario A: Clean Install (Simulating v0.4.x state before migrations)
        print("\n[Scenario A] Clean Install...")
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE Projects (project_id TEXT PRIMARY KEY, project_name TEXT)")
        conn.execute("""
            CREATE TABLE CadFeatures (
                feature_id TEXT PRIMARY KEY, 
                project_id TEXT,
                feature_type TEXT,
                layer TEXT,
                name TEXT,
                highway TEXT
            )
        """)
        conn.commit()
        conn.close()
        
        applied = migrate_database(db_path)
        print(f"Applied {applied} migrations.")
        assert applied >= 2
        
        # Scenario B: Idempotency (Re-run)
        print("\n[Scenario B] Idempotency (Immediate re-run)...")
        applied = migrate_database(db_path)
        print(f"Applied {applied} migrations.")
        assert applied == 0
        
        # Scenario C: v0.4.x Migration (Manual half-applied state)
        print("\n[Scenario C] v0.4.x Migration (Upgrading existing DB)...")
        # Reset version in DB but keep columns
        conn = sqlite3.connect(str(db_path))
        conn.execute("DELETE FROM schema_version")
        conn.commit()
        conn.close()
        
        # This will trigger migrations again. They should skip the ALTER TABLEs because columns exist.
        applied = migrate_database(db_path)
        print(f"Applied {applied} migrations (should have skipped actual SQL errors).")
        assert applied == 2
        
        # Verify final state
        conn = sqlite3.connect(str(db_path))
        v = get_schema_version(conn)
        print(f"Final Schema Version: {v}")
        assert v == CURRENT_VERSION
        
        # Check if color column exists
        cursor = conn.execute("PRAGMA table_info(CadFeatures)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Columns in CadFeatures: {columns}")
        assert "color" in columns
        assert "elevation" in columns
        assert "slope" in columns
        conn.close()

        print("\n--- PASSED: Migrations are idempotent and tested. ---")

    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_migration_flow()
