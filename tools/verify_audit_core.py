"""
Independent Verification of Audit Logger
Tests signature generation and verification without full API stack.
"""
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath("src/backend"))

from backend.core.audit import get_audit_logger
from backend.core.database import get_db_connection

def test_audit_cycle():
    print("Testing Audit Logger Cycle...")
    logger = get_audit_logger()
    
    # 1. Log something
    audit_id = logger.log(
        event_type="TEST",
        entity_type="Verification",
        entity_id="test-123",
        data={"status": "verifying"},
        user_id="test-user"
    )
    print(f"Created audit log: {audit_id}")
    
    # 2. Verify it
    is_valid = logger.verify(audit_id)
    print(f"Signature valid: {is_valid}")
    assert is_valid == True
    
    # 3. Try to tamper
    print("Simulating tampering...")
    conn = get_db_connection()
    try:
        conn.execute("UPDATE AuditLog SET event_type = 'TAMPERED' WHERE audit_id = ?", (audit_id,))
        conn.commit()
    finally:
        conn.close()
        
    is_valid_after = logger.verify(audit_id)
    print(f"Signature valid after tampering: {is_valid_after}")
    assert is_valid_after == False
    print("Verification Success!")

if __name__ == "__main__":
    try:
        test_audit_cycle()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
