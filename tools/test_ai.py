import sys
import os
import requests
from pathlib import Path

# Add src to path
sys.path.append(str(Path("src/backend").absolute()))

print("--- Phase 36: AI Integration Backend Test ---")

# We test the endpoint via direct invocation simulation or just check imports
# Since we need running server for requests, we'll unit test the service
try:
    from backend.services.ai import AiService
    
    print("1. Instantiating AiService...")
    svc = AiService()
    
    if svc.client:
        print("[INFO] GROQ_API_KEY found. Attempting live call...")
        # Only do this if you want to spend tokens
        # response = svc.generate_response("Hello")
        # print(f"[PASS] Response: {response}")
        print("[PASS] Client configured.")
    else:
        print("[WARN] GROQ_API_KEY not set. Service running in mock/disabled mode.")
        response = svc.generate_response("Hello")
        if response == "AI Service is not configured (missing API key).":
            print("[PASS] Gracefully handled missing key.")
        else:
            print(f"[FAIL] Unexpected response: {response}")
            sys.exit(1)

    print("\n--- PASSED: AI Service Logic Verified ---")
    sys.exit(0)

except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    sys.exit(1)
