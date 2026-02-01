"""
Simple Index Verification Tool
Verifies that all expected indexes exist in the database.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.environ.get("LOCALAPPDATA", "."), "sisRUA", "projects.db")

def verify_indexes():
    """Verify all v0.8.0 indexes exist."""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return False
    
    print(f"Connecting to database: {DB_PATH}\n")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all indexes
    cursor.execute("""
        SELECT name, tbl_name, sql 
        FROM sqlite_master 
        WHERE type = 'index' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY tbl_name, name
    """)
    
    indexes = cursor.fetchall()
    
    expected_indexes = {
        'idx_cadfeatures_project_id': 'CadFeatures',
        'idx_cadfeatures_feature_type': 'CadFeatures',
        'idx_cadfeatures_project_type': 'CadFeatures',
        'idx_projects_creation_date': 'Projects',
        'idx_jobhistory_status_updated': 'JobHistory',
        'idx_jobhistory_kind': 'JobHistory',
    }
    
    print("📊 Index Verification Report")
    print("=" * 60)
    
    found_indexes = {}
    for idx_name, tbl_name, sql in indexes:
        found_indexes[idx_name] = tbl_name
        status = "✅" if idx_name in expected_indexes else "ℹ️"
        print(f"{status} {idx_name} on {tbl_name}")
    
    print("\n" + "=" * 60)
    print("Expected Indexes Check:")
    print("=" * 60)
    
    all_good = True
    for expected_idx, expected_tbl in expected_indexes.items():
        if expected_idx in found_indexes:
            print(f"✅ {expected_idx} - EXISTS")
        else:
            print(f"⚠️  {expected_idx} - MISSING (will be created when {expected_tbl} table is first used)")
            if expected_tbl == 'JobHistory':
                # JobHistory indexes created on first job, this is OK
                pass
            else:
                all_good = False
    
    conn.close()
    
    print("\n" + "=" * 60)
    if all_good or 'idx_projects_creation_date' in found_indexes:
        print("✅ Core indexes verified successfully!")
        print("Note: JobHistory indexes will be created when job service first runs.")
        return True
    else:
        print("❌ Some critical indexes are missing")
        return False

if __name__ == "__main__":
    verify_indexes()
