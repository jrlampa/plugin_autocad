import sys
import json
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src', 'backend'))

from backend.api import app

def export_openapi():
    print("Exporting OpenAPI Schema...")
    openapi_data = app.openapi()
    
    output_file = "openapi_v0.8.0.json"
    with open(output_file, "w") as f:
        json.dump(openapi_data, f, indent=2)
    
    print(f"Successfully exported to {output_file}")

if __name__ == "__main__":
    export_openapi()
