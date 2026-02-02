"""
Cryptographic Audit Logging Service
Provides tamper-proof audit logs with HMAC-SHA256 signatures.
"""
import hmac
import hashlib
import json
import time
import os
from typing import Dict, Any, Optional
from backend.core.database import get_db_connection
from backend.core.logger import get_logger

logger = get_logger(__name__)

class AuditLogger:
    """Cryptographically signed audit logger using HMAC-SHA256."""
    
    def __init__(self):
        self.secret_key = self._load_or_generate_secret()
    
    def _load_or_generate_secret(self) -> bytes:
        """Load existing secret or generate new 256-bit key."""
        secret_path = os.path.join(
            os.environ.get("LOCALAPPDATA", "."),
            "sisRUA", 
            ".audit_secret"
        )
        
        if os.path.exists(secret_path):
            with open(secret_path, 'rb') as f:
                secret = f.read()
                logger.info("audit_secret_loaded", path=secret_path)
                return secret
        
        # Generate 256-bit random secret
        secret = os.urandom(32)
        os.makedirs(os.path.dirname(secret_path), exist_ok=True)
        
        # Write with user-only permissions
        with open(secret_path, 'wb') as f:
            f.write(secret)
        
        # Set file permissions (Windows: user-only)
        try:
            os.chmod(secret_path, 0o600)
        except Exception as e:
            logger.warning("audit_secret_chmod_failed", error=str(e))
        
        logger.info("audit_secret_generated", path=secret_path, size_bytes=len(secret))
        
        return secret
    
    def _compute_signature(
        self, 
        event_type: str, 
        entity_type: str, 
        entity_id: Optional[str],
        user_id: Optional[str],
        timestamp: float,
        data: Dict[str, Any]
    ) -> str:
        """Compute HMAC-SHA256 signature for audit log entry."""
        # Construct message from all fields in deterministic order
        message_parts = [
            event_type,
            entity_type,
            entity_id or "",
            user_id or "system",
            str(timestamp),
            json.dumps(data, sort_keys=True)  # sort_keys ensures determinism
        ]
        message = "|".join(message_parts).encode('utf-8')
        
        signature = hmac.new(
            self.secret_key, 
            message, 
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def log(
        self,
        event_type: str,  # CREATE, UPDATE, DELETE
        entity_type: str,  # Project, CadFeature, JobHistory
        entity_id: Optional[str],
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> int:
        """
        Log an audit event with cryptographic signature.
        
        Args:
            event_type: Type of mutation (CREATE, UPDATE, DELETE)
            entity_type: Type of entity being mutated (Project, CadFeature, JobHistory)
            entity_id: ID of the specific entity (project_id, feature_id, job_id)
            data: Mutation data (fields changed, old/new values, etc.)
            user_id: User who performed the action (defaults to "system")
        
        Returns:
            audit_id: ID of the created audit log entry
        """
        timestamp = time.time()
        signature = self._compute_signature(
            event_type, entity_type, entity_id, 
            user_id, timestamp, data
        )
        
        conn = get_db_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO AuditLog 
                (event_type, entity_type, entity_id, user_id, timestamp, data_json, signature)
                VALUES (?,?,?,?,?,?,?)
            """, (
                event_type,
                entity_type,
                entity_id,
                user_id or "system",
                timestamp,
                json.dumps(data),
                signature
            ))
            conn.commit()
            audit_id = cursor.lastrowid
            
            logger.info(
                "audit_logged",
                audit_id=audit_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id
            )
            
            return audit_id
        finally:
            conn.close()
    
    def verify(self, audit_id: int) -> bool:
        """
        Verify audit log signature to detect tampering.
        
        Args:
            audit_id: ID of audit log to verify
        
        Returns:
            True if signature is valid, False if tampered or not found
        """
        conn = get_db_connection()
        try:
            row = conn.execute("""
                SELECT event_type, entity_type, entity_id, user_id, 
                       timestamp, data_json, signature
                FROM AuditLog WHERE audit_id = ?
            """, (audit_id,)).fetchone()
            
            if not row:
                logger.warning("audit_verify_not_found", audit_id=audit_id)
                return False
            
            expected_sig = self._compute_signature(
                row[0], row[1], row[2], row[3], row[4], json.loads(row[5])
            )
            
            # Use constant-time comparison to prevent timing attacks
            is_valid = hmac.compare_digest(expected_sig, row[6])
            
            if not is_valid:
                logger.error(
                    "audit_tamper_detected",
                    audit_id=audit_id,
                    expected=expected_sig[:16] + "...",
                    actual=row[6][:16] + "..."
                )
            
            return is_valid
        finally:
            conn.close()
    
    def verify_all(self, limit: int = 1000) -> Dict[str, Any]:
        """
        Verify multiple audit logs for integrity checking.
        
        Args:
            limit: Maximum number of recent logs to verify
        
        Returns:
            Dictionary with verification statistics
        """
        conn = get_db_connection()
        try:
            rows = conn.execute("""
                SELECT audit_id FROM AuditLog 
                ORDER BY audit_id DESC LIMIT ?
            """, (limit,)).fetchall()
            
            total = len(rows)
            valid = sum(1 for row in rows if self.verify(row[0]))
            invalid = total - valid
            
            logger.info(
                "audit_verify_all",
                total=total,
                valid=valid,
                invalid=invalid,
                integrity=valid / total if total > 0 else 1.0
            )
            
            return {
                "total": total,
                "valid": valid,
                "invalid": invalid,
                "integrity": valid / total if total > 0 else 1.0
            }
        finally:
            conn.close()

# Global singleton instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get global AuditLogger instance (singleton pattern)."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
