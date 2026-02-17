import os
import json
import sys
from pathlib import Path

# Add src/backend to path to import backend.models
sys.path.append(str(Path(__file__).parent.parent / "src" / "backend"))

from pydantic import BaseModel
import backend.models as models

def export_schemas():
    output_dir = Path(__file__).parent.parent / "schema" / "v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Exporting schemas to {output_dir}...")
    
    count = 0
    # Iterate through all members of backend.models
    for name in dir(models):
        obj = getattr(models, name)
        
        # Check if it's a Pydantic model (and not BaseModel itself)
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
            schema = obj.model_json_schema()
            
            output_file = output_dir / f"{name}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            
            print(f" - {name}.json")
            count += 1
            
    print(f"Done. Exported {count} schemas.")

if __name__ == "__main__":
    export_schemas()
