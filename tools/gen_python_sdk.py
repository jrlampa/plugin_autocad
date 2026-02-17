import json
import os
import re
from pathlib import Path

def to_snake_case(name):
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    return name

def to_pascal_case(name):
    return ''.join(x.title() for x in name.replace('_', ' ').split())

def generate_python_sdk(openapi_path, output_dir):
    with open(openapi_path, 'r') as f:
        spec = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    
    # Generate Models (simplified Pydantic)
    models_content = "from pydantic import BaseModel, Field\nfrom typing import Optional, List, Any, Dict\nfrom datetime import datetime\n\n"
    
    if 'components' in spec and 'schemas' in spec['components']:
        for name, schema in spec['components']['schemas'].items():
            class_name = name
            models_content += f"class {class_name}(BaseModel):\n"
            
            props = schema.get('properties', {})
            required = schema.get('required', [])
            
            if not props:
                models_content += "    pass\n\n"
                continue

            for prop_name, prop_schema in props.items():
                py_type = "Any"
                if 'type' in prop_schema:
                    t = prop_schema['type']
                    if t == 'string': py_type = 'str'
                    elif t == 'integer': py_type = 'int'
                    elif t == 'boolean': py_type = 'bool'
                    elif t == 'number': py_type = 'float'
                    elif t == 'array': py_type = 'List[Any]' # Simplified
                
                is_optional = prop_name not in required
                field_args = ""
                if is_optional:
                    default = "None"
                    py_type = f"Optional[{py_type}]"
                else:
                    default = "..."
                
                models_content += f"    {prop_name}: {py_type} = Field({default})\n"
            models_content += "\n"

    with open(os.path.join(output_dir, "models.py"), "w") as f:
        f.write(models_content)

    # Generate Client
    client_content = "import httpx\nfrom typing import Optional, Dict, Any\nfrom .models import *\n\nclass SisRuaClient:\n    def __init__(self, base_url: str, token: Optional[str] = None):\n        self.base_url = base_url.rstrip('/')\n        self.headers = {'X-SisRua-Token': token} if token else {}\n        self.client = httpx.Client(base_url=self.base_url, headers=self.headers)\n\n"

    for path, methods in spec.get('paths', {}).items():
        for method, details in methods.items():
            op_id = details.get('operationId')
            if not op_id: continue
            
            func_name = to_snake_case(op_id)
            # Simplified args parsing - assume json body for POST
            args = ""
            if method in ['post', 'put']:
                args = ", body: Dict[str, Any]"
            
            client_content += f"    def {func_name}(self{args}) -> Any:\n"
            client_content += f"        '''{details.get('summary', '')}'''\n"
            if method in ['post', 'put']:
                 client_content += f"        resp = self.client.{method}('{path}', json=body)\n"
            else:
                 client_content += f"        resp = self.client.{method}('{path}')\n"
            client_content += "        resp.raise_for_status()\n"
            client_content += "        return resp.json()\n\n"

    with open(os.path.join(output_dir, "client.py"), "w") as f:
        f.write(client_content)
        
    # Init
    with open(os.path.join(output_dir, "__init__.py"), "w") as f:
        f.write("from .client import SisRuaClient\nfrom .models import *\n")

    print(f"Generated Python SDK in {output_dir}")

if __name__ == "__main__":
    generate_python_sdk("openapi_v0.8.0.json", "sdk_python/sisrua")
