import json
import os
from pathlib import Path

def to_camel_case(name):
    components = name.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def to_pascal_case(name):
    return ''.join(x.title() for x in name.replace('_', ' ').split())

def generate_ts_sdk(openapi_path, output_dir):
    with open(openapi_path, 'r') as f:
        spec = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    
    # Generate Types
    types_content = "// Generated TypeScript Interfaces\n\n"
    
    if 'components' in spec and 'schemas' in spec['components']:
        for name, schema in spec['components']['schemas'].items():
            interface_name = name
            types_content += f"export interface {interface_name} {{\n"
            
            props = schema.get('properties', {})
            required = schema.get('required', [])
            
            for prop_name, prop_schema in props.items():
                ts_type = "any"
                if 'type' in prop_schema:
                    t = prop_schema['type']
                    if t == 'string': ts_type = 'string'
                    elif t == 'integer' or t == 'number': ts_type = 'number'
                    elif t == 'boolean': ts_type = 'boolean'
                    elif t == 'array': ts_type = 'any[]' # Simplified
                
                is_optional = prop_name not in required
                suffix = "?" if is_optional else ""
                
                types_content += f"  {prop_name}{suffix}: {ts_type};\n"
            types_content += "}\n\n"

    with open(os.path.join(output_dir, "types.ts"), "w") as f:
        f.write(types_content)

    # Generate Client
    client_content = "import { " + ", ".join(spec['components']['schemas'].keys()) + " } from './types';\n\n"
    client_content += "export class SisRuaClient {\n"
    client_content += "  private baseUrl: string;\n"
    client_content += "  private token?: string;\n\n"
    client_content += "  constructor(baseUrl: string, token?: string) {\n"
    client_content += "    this.baseUrl = baseUrl.replace(/\\/$/, '');\n"
    client_content += "    this.token = token;\n"
    client_content += "  }\n\n"
    client_content += "  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {\n"
    client_content += "    const headers: HeadersInit = { 'Content-Type': 'application/json' };\n"
    client_content += "    if (this.token) headers['X-SisRua-Token'] = this.token;\n"
    client_content += "    const response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });\n"
    client_content += "    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);\n"
    client_content += "    return response.json();\n"
    client_content += "  }\n\n"

    for path, methods in spec.get('paths', {}).items():
        for method, details in methods.items():
            op_id = details.get('operationId')
            if not op_id: continue
            
            func_name = to_camel_case(op_id)
            # Simplified args
            args_sig = ""
            if method in ['post', 'put']:
               args_sig = "body: any"
            
            client_content += f"  async {func_name}({args_sig}): Promise<any> {{\n"
            if method in ['post', 'put']:
                client_content += f"    return this.request('{path}', {{ method: '{method.upper()}', body: JSON.stringify(body) }});\n"
            else:
                client_content += f"    return this.request('{path}', {{ method: '{method.upper()}' }});\n"
            client_content += "  }\n\n"

    client_content += "}\n"

    with open(os.path.join(output_dir, "client.ts"), "w") as f:
        f.write(client_content)
        
    print(f"Generated TypeScript SDK in {output_dir}")

if __name__ == "__main__":
    generate_ts_sdk("openapi_v0.8.0.json", "sdk_ts/src")
