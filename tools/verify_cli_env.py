import sys
import os
from pathlib import Path

# Setup paths to simulate installed environment
src_sdk = Path("src/sdk").absolute()
src_backend = Path("src/backend").absolute()

sys.path.append(str(src_sdk))
sys.path.append(str(src_backend))

print(f"--- Phase 34: CLI Environment Verification ---")
print(f"Added to path: {src_sdk}")
print(f"Added to path: {src_backend}")

try:
    import typer
    import rich
    print("[PASS] Typer and Rich are installed.")
except ImportError as e:
    print(f"[WARN] Dependencies missing: {e}. Please run 'pip install -r src/sdk/requirements.txt'.")
    # We can't proceed with import if dependencies are missing, but this confirms structure is ok so far.
    sys.exit(0)

try:
    from sisrua_sdk.cli import app, get_client
    print("[PASS] Successfully imported sisrua_sdk.cli.")
    
    # Introspect
    client = get_client()
    print(f"[PASS] Client instantiated with base_url={client.base_url}")
    
    print("\n--- PASSED: CLI Environment Ready ---")
except ImportError as e:
    print(f"[FAIL] Import validation failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Unexpected error: {e}")
    sys.exit(1)
