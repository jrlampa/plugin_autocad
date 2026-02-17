import os
import sys

def verify_sync():
    print("=== sisRUA v0.5.0 Environment Sync Audit ===")
    
    # Required Secrets
    required = ["SISRUA_AUTH_TOKEN"]
    # Optional Secrets
    optional = [
        "SENTRY_DSN", 
        "SENTRY_ENVIRONMENT", 
        "OPENTOPOGRAPHY_API_KEY", 
        "GROQ_API_KEY",
        "VITE_SENTRY_DSN"
    ]
    
    print("\n[Required Secrets]")
    all_req_present = True
    for var in required:
        val = os.environ.get(var)
        status = "PRESENT" if val else "MISSING"
        print(f"{var:25}: {status}")
        if not val:
            all_req_present = False
            
    print("\n[Optional Secrets/Config]")
    for var in optional:
        val = os.environ.get(var)
        status = "PRESENT" if val else "MISSING (Using Default/None)"
        print(f"{var:25}: {status}")

    print("\n[System Info]")
    print(f"Platform       : {sys.platform}")
    print(f"Python Version : {sys.version.split()[0]}")
    print(f"PWD            : {os.getcwd()}")

    if not all_req_present:
        print("\nCRITICAL: One or more required secrets are missing!")
        sys.exit(1)
    else:
        print("\nSUCCESS: Essential environment synchronization verified.")

if __name__ == "__main__":
    verify_sync()
