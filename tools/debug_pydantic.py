
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/backend')))

import json
from backend.models import PrepareJobRequest

print("Imported models successfully.")

try:
    req = PrepareJobRequest(kind="osm", latitude=0, longitude=0, radius=100)
    print(f"Created request: {req}")
    
    print("Attempting model_dump()...")
    try:
        data = req.model_dump()
        print(f"model_dump() success: {data}")
    except AttributeError:
        print("model_dump() FAILED. Trying dict()...")
        data = req.dict()
        print(f"dict() success: {data}")

    print("Attempting json.dumps...")
    json_str = json.dumps(data, sort_keys=True)
    print(f"Final JSON: {json_str}")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
