import sys
import os
import io
import json
import logging
import uuid
from contextvars import copy_context
from backend.core.logger import configure_logging, get_logger, set_trace_id
import structlog

# Mock uvicorn/fastapi environment
def test_structured_logging():
    print("--- Phase 39: Audit Logging Verification ---")
    
    # Capture stdout
    capture = io.StringIO()
    
    # Configure logging to write to our capture stream
    # For structlog+logging, we need to add a handler to the root logger that writes to our stream
    
    configure_logging()
    
    # Remove existing handlers to avoid double printing
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
        
    handler = logging.StreamHandler(capture)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    logger = get_logger("test_logger")
    
    # 1. Test: Trace ID Propagation
    trace_id = str(uuid.uuid4())
    set_trace_id(trace_id)
    structlog.contextvars.bind_contextvars(trace_id=trace_id)
    
    logger.info("test_event", action="verifying_audit", status="ok")
    
    # Flush handler
    handler.flush()
    
    output = capture.getvalue().strip()
    print(f"\n[Raw Output]: {output}")
    
    # Validation logic update: Structlog might print multiple lines or color codes if config leaked
    # We take the last non-empty line which should be our JSON
    lines = [line for line in output.split('\n') if line.strip()]
    last_line = lines[-1] if lines else ""

    try:
        log_entry = json.loads(last_line)
        if log_entry.get("trace_id") == trace_id:
            print("[PASS] Trace ID present in log entry.")
        else:
            print(f"[FAIL] Trace ID missing or mismatch. Expected {trace_id}, got {log_entry.get('trace_id')}")
            
        if log_entry.get("event") == "test_event":
            print("[PASS] Event name correct.")
        else:
            print(f"[FAIL] Event name mismatch.")
            
        if log_entry.get("action") == "verifying_audit":
            print("[PASS] Context fields present.")
            
    except json.JSONDecodeError:
        print("[FAIL] Output is not valid JSON.")

if __name__ == "__main__":
    test_structured_logging()
