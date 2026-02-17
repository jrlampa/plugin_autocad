"""
Database Index Migration for v0.8.0
Adds optimized indexes to Projects and JobHistory tables.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.environ.get("LOCALAPPDATA", "."), "sisRUA", "projects.db")

def apply_v080_indexes():
    """Apply v0.8.0 index optimizations to the database."""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        print("   Run seed.py first to create the database.")
        sys.exit(1)
    
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("\n🔧 Applying v0.8.0 index optimizations...\n")
        
        # Projects table - creation_date index for date filtering
        print("  Creating idx_projects_creation_date...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_projects_creation_date 
            ON Projects(creation_date DESC)
        ''')
        print("  ✓ idx_projects_creation_date")
        
        # JobHistory table - composite index for cleanup queries
        print("\n  Creating idx_jobhistory_status_updated...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_jobhistory_status_updated 
            ON JobHistory(status, updated_at)
        ''')
        print("  ✓ idx_jobhistory_status_updated")
        
        # JobHistory table - kind index for job type filtering
        print("\n  Creating idx_jobhistory_kind...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_jobhistory_kind 
            ON JobHistory(kind)
        ''')
        print("  ✓ idx_jobhistory_kind")
        
        conn.commit()
        print("\n✅ Index migration complete!")
        
        # Verify indexes were created
        print("\n📊 Verifying indexes...")
        cursor.execute("""
            SELECT name, tbl_name 
            FROM sqlite_master 
            WHERE type = 'index' 
            AND name LIKE 'idx_%'
            ORDER BY tbl_name, name
        """)
        
        indexes = cursor.fetchall()
        print(f"\n   Total indexes: {len(indexes)}")
        for idx_name, tbl_name in indexes:
            print(f"   - {idx_name} on {tbl_name}")
        
    except Exception as e:
        print(f"\n❌ Error applying indexes: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    apply_v080_indexes()
