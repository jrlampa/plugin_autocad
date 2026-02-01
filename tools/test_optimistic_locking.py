import os
import uuid
import unittest
import time
from pathlib import Path
from backend.core.database import get_db_connection
from backend.services.projects import project_service, ConflictError

DB_PATH = Path("test_locking.db")

class TestOptimisticLocking(unittest.TestCase):
    def setUp(self):
        if DB_PATH.exists():
            try: DB_PATH.unlink()
            except: pass
        
        # Override DB path for service (monkey patch or dependency injection would be better, 
        # but for this script we just rely on the fact that get_db_connection can take a path)
        # However, calling project_service calls get_db_connection() without args (uses DB_PATH global).
        # We need to monkey patch backend.services.projects.get_db_connection
        
        # Setup schema
        self.conn = get_db_connection(DB_PATH)
        self.conn.execute("""
            CREATE TABLE Projects (
                project_id TEXT PRIMARY KEY, 
                project_name TEXT, 
                crs_out TEXT, 
                version INTEGER DEFAULT 1, 
                creation_date REAL
            )
        """)
        self.conn.commit()
        self.conn.close()
        
        # Monkey patch service
        import backend.services.projects
        self.original_get_conn = backend.services.projects.get_db_connection
        backend.services.projects.get_db_connection = lambda: get_db_connection(DB_PATH)

    def tearDown(self):
        import backend.services.projects
        backend.services.projects.get_db_connection = self.original_get_conn
        
        if DB_PATH.exists():
            try: 
                DB_PATH.unlink()
                Path("test_locking.db-shm").unlink(missing_ok=True)
                Path("test_locking.db-wal").unlink(missing_ok=True)
            except: pass

    def test_optimistic_locking_flow(self):
        print("--- Testing Optimistic Locking ---")
        
        # 1. Create Project
        pid = str(uuid.uuid4())
        conn = get_db_connection(DB_PATH)
        conn.execute(
            "INSERT INTO Projects (project_id, project_name, version) VALUES (?, ?, ?)",
            (pid, "Project A", 1)
        )
        conn.commit()
        conn.close()
        
        # 2. User A reads (V1)
        proj_a = project_service.get_project(pid)
        self.assertEqual(proj_a['version'], 1)
        print("[1] Created Project V1")

        # 3. User B reads (V1)
        proj_b = project_service.get_project(pid)
        self.assertEqual(proj_b['version'], 1)

        # 4. User A updates -> V2
        updated_a = project_service.update_project(pid, {"project_name": "Project A Updated"}, proj_a['version'])
        self.assertEqual(updated_a['version'], 2)
        self.assertEqual(updated_a['project_name'], "Project A Updated")
        print("[2] User A updated to V2")

        # 5. User B tries to update using old V1 -> FAIL
        print("[3] User B trying to update with V1 (stale)...")
        with self.assertRaises(ConflictError):
            project_service.update_project(pid, {"project_name": "Project B Overwrite"}, proj_b['version'])
        print("[PASS] User B blocked (ConflictError raised).")

        # 6. User B re-reads (V2) and retries -> V3
        proj_b_fresh = project_service.get_project(pid)
        self.assertEqual(proj_b_fresh['version'], 2)
        self.assertEqual(proj_b_fresh['project_name'], "Project A Updated")
        
        updated_b = project_service.update_project(pid, {"project_name": "Project B Fixed"}, proj_b_fresh['version'])
        self.assertEqual(updated_b['version'], 3)
        print("[4] User B re-read and updated to V3")

if __name__ == "__main__":
    unittest.main()
