"""
Audit Log Verification Tests
Tests secret generation, signing, verification, and tamper detection.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.audit import get_audit_logger
from backend.core.database import get_db_connection

def test_secret_generation():
    """Test 1: Secret key generation."""
    print("\n=== Test 1: Secret Key Generation ===")
    
    audit = get_audit_logger()
    secret_path = os.path.join(
        os.environ.get("LOCALAPPDATA", "."),
        "sisRUA", 
        ".audit_secret"
    )
    
    assert os.path.exists(secret_path), f"Secret file not found: {secret_path}"
    
    file_size = os.path.getsize(secret_path)
    assert file_size == 32, f"Expected 32 bytes, got {file_size}"
    
    print(f"✅ Secret key generated: {secret_path}")
    print(f"✅ File size: {file_size} bytes")

def test_audit_create_and_verify():
    """Test 2: Create audit log and verify signature."""
    print("\n=== Test 2: Create & Verify Audit Log ===")
    
    audit = get_audit_logger()
    
    # Create audit log
    audit_id = audit.log(
        event_type="UPDATE",
        entity_type="Project",
        entity_id="test-123",
        data={"project_name": "Test Project", "crs_out": "EPSG:31983"}
    )
    
    print(f"Created audit_id: {audit_id}")
    
    # Verify signature
    is_valid = audit.verify(audit_id)
    assert is_valid, "Signature verification failed!"
    
    print(f"✅ Signature valid: {is_valid}")

def test_tamper_detection():
    """Test 3: Tamper detection (manual verification)."""
    print("\n=== Test 3: Tamper Detection ===")
    
    audit = get_audit_logger()
    
    # Create a log
    audit_id = audit.log(
        event_type="CREATE",
        entity_type="Project",
        entity_id="tamper-test",
        data={"test": "original"}
    )
    
    print(f"Created audit_id: {audit_id}")
    
    # Tamper with the database
    conn = get_db_connection()
    try:
        print("\n⚠️  Simulating tamper: modifying data_json...")
        conn.execute("""
            UPDATE AuditLog 
            SET data_json = '{"test": "tampered!!!"}' 
            WHERE audit_id = ?
        """, (audit_id,))
        conn.commit()
    finally:
        conn.close()
    
    # Verify should fail
    is_valid = audit.verify(audit_id)
    assert not is_valid, "Tamper detection failed! Signature should be invalid."
    
    print(f"✅ Tamper detected successfully: valid = {is_valid}")

def test_batch_verification():
    """Test 4: Batch verification."""
    print("\n=== Test 4: Batch Verification ===")
    
    audit = get_audit_logger()
    
    # Create multiple logs
    for i in range(5):
        audit.log(
            event_type="CREATE",
            entity_type="Project",
            entity_id=f"batch-test-{i}",
            data={"index": i}
        )
    
    # Verify all
    results = audit.verify_all(limit=10)
    
    print(f"Total logs verified: {results['total']}")
    print(f"Valid: {results['valid']}")
    print(f"Invalid: {results['invalid']}")
    print(f"Integrity: {results['integrity']:.2%}")
    
    # Should have at least 1 invalid (from tamper test)
    assert results['invalid'] >= 1, "Should have detected tampered log"
    
    print(f"✅ Batch verification complete")

def test_audit_log_storage():
    """Test 5: Verify audit logs are persisted."""
    print("\n=== Test 5: Audit Log Storage ===")
    
    conn = get_db_connection()
    try:
        # Count total logs
        count = conn.execute("SELECT COUNT(*) FROM AuditLog").fetchone()[0]
        print(f"Total audit logs in database: {count}")
        
        # Get recent logs
        rows = conn.execute("""
            SELECT audit_id, event_type, entity_type, entity_id 
            FROM AuditLog 
            ORDER BY audit_id DESC 
            LIMIT 5
        """).fetchall()
        
        print("\nRecent audit logs:")
        for row in rows:
            print(f"  #{row[0]}: {row[1]} {row[2]} {row[3]}")
        
        assert count > 0, "No audit logs found"
        print(f"✅ Audit logs persisted correctly")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("AUDIT LOG VERIFICATION TESTS")
    print("=" * 60)
    
    try:
        test_secret_generation()
        test_audit_create_and_verify()
        test_tamper_detection()
        test_batch_verification()
        test_audit_log_storage()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
