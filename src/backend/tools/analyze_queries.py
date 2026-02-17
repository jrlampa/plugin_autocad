"""
Database Query Analysis Tool
Runs EXPLAIN QUERY PLAN on all queries to verify index usage.
"""
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.environ.get("LOCALAPPDATA", "."), "sisRUA", "projects.db")

def analyze_query(conn, name, query, params=()):
    """Run EXPLAIN QUERY PLAN on a query and print results."""
    cursor = conn.cursor()
    explain_query = f"EXPLAIN QUERY PLAN {query}"
    
    print(f"\n{'='*60}")
    print(f"Query: {name}")
    print(f"{'='*60}")
    print(f"SQL: {query}")
    if params:
        print(f"Params: {params}")
    print(f"\nQuery Plan:")
    
    result = cursor.execute(explain_query, params).fetchall()
    for row in result:
        # SQLite EXPLAIN QUERY PLAN output: (id, parent, notused, detail)
        print(f"  {row[3]}")
    
    # Check if using index
    plan_text = " ".join([str(row[3]) for row in result])
    if "USING INDEX" in plan_text:
        print("✅ Using index")
    elif "SCAN TABLE" in plan_text:
        print("⚠️  Full table scan detected!")
    
    return result

def run_analysis():
    """Analyze all queries used in v0.8.0."""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        print("   Run seed.py first to create the database.")
        sys.exit(1)
    
    print(f"Connecting to database: {DB_PATH}")
    print(f"Running EXPLAIN QUERY PLAN analysis...\n")
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Query 1: Projects by ID (PRIMARY KEY lookup)
        analyze_query(
            conn,
            "Projects by ID",
            "SELECT project_id, project_name, crs_out, creation_date FROM Projects WHERE project_id = ?",
            ("test-id",)
        )
        
        # Query 2: Projects by creation date
        analyze_query(
            conn,
            "Recent Projects",
            "SELECT * FROM Projects WHERE creation_date > ? ORDER BY creation_date DESC LIMIT 10",
            ("2024-01-01",)
        )
        
        # Query 3: JobHistory cleanup query
        analyze_query(
            conn,
            "JobHistory Cleanup",
            "SELECT * FROM JobHistory WHERE status = 'completed' AND updated_at < ?",
            (1234567890.0,)
        )
        
        # Query 4: JobHistory by kind
        analyze_query(
            conn,
            "JobHistory by Kind",
            "SELECT * FROM JobHistory WHERE kind = ? ORDER BY created_at DESC",
            ("osm_generation",)
        )
        
        # Query 5: CadFeatures composite index
        analyze_query(
            conn,
            "CadFeatures by Project+Type",
            "SELECT * FROM CadFeatures WHERE project_id = ? AND feature_type = ?",
            ("test-id", "Polyline")
        )
        
        # Query 6: CadFeatures by project only
        analyze_query(
            conn,
            "CadFeatures by Project",
            "SELECT * FROM CadFeatures WHERE project_id = ?",
            ("test-id",)
        )
        
        print(f"\n{'='*60}")
        print("Analysis Complete")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_analysis()
