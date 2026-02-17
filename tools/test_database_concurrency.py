import threading
import time
import sqlite3
import queue
from pathlib import Path
from backend.core.database import get_db_connection
from backend.core.buffer import PersistenceBuffer

DB_PATH = Path("test_concurrency.db")

def setup_db():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = get_db_connection(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS stress_test (id INTEGER PRIMARY KEY, data TEXT)")
    conn.close()

def worker_writer(worker_id, count):
    conn = get_db_connection(DB_PATH)
    for i in range(count):
        try:
            conn.execute("INSERT INTO stress_test (data) VALUES (?)", (f"worker-{worker_id}-{i}",))
            conn.commit()
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print(f"LOCKED: Worker {worker_id}")
            else:
                raise e
    conn.close()

def test_wal_mode():
    print("--- Testing WAL Mode ---")
    setup_db()
    conn = get_db_connection(DB_PATH)
    cursor = conn.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0]
    conn.close()
    
    print(f"Journal Mode: {mode}")
    if mode.upper() == "WAL":
        print("[PASS] WAL mode enabled.")
    else:
        print(f"[FAIL] Expected WAL, got {mode}")

    # Stress Test
    print("--- Stress Testing Concurrency ---")
    threads = []
    num_workers = 10
    writes_per_worker = 100
    
    start = time.time()
    for i in range(num_workers):
        t = threading.Thread(target=worker_writer, args=(i, writes_per_worker))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
    duration = time.time() - start
    
    conn = get_db_connection(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM stress_test").fetchone()[0]
    conn.close()
    
    print(f"Writes: {count}/{num_workers * writes_per_worker} in {duration:.2f}s")
    if count == num_workers * writes_per_worker:
        print("[PASS] All writes succeeded without locking.")
    else:
        print("[FAIL] Missing writes.")

def test_buffer():
    print("\n--- Testing Persistence Buffer ---")
    results = []
    
    def callback(batch):
        print(f"Flushing batch of size {len(batch)}")
        results.extend(batch)
        
    buf = PersistenceBuffer(flush_callback=callback, batch_size=5, flush_interval=0.5)
    
    for i in range(12):
        buf.add(i)
        
    # Wait for background flush (interval or batch size)
    time.sleep(1.0)
    
    buf.stop() 
    
    print(f"Total flushed items: {len(results)}")
    if len(results) == 12:
        print("[PASS] Buffer flushed all items.")
    else:
        print(f"[FAIL] Expected 12 items, got {len(results)}")

if __name__ == "__main__":
    try:
        test_wal_mode()
        test_buffer()
    finally:
        if DB_PATH.exists():
            try:
                DB_PATH.unlink() # Cleanup
                Path("test_concurrency.db-shm").unlink(missing_ok=True)
                Path("test_concurrency.db-wal").unlink(missing_ok=True)
            except: pass
