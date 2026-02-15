
import subprocess
import os
from pathlib import Path

ACCORE_BIN = r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe"

def run_headless_test(dwg_path: str, script_path: str):
    """
    Executes a .scr script on a .dwg file using AutoCAD Core Console.
    """
    if not os.path.exists(ACCORE_BIN):
        print(f"ERROR: accoreconsole.exe not found at {ACCORE_BIN}")
        return False

    cmd = [
        ACCORE_BIN,
        "/i", dwg_path,
        "/s", script_path,
        "/l", "en-US"
    ]
    
    print(f"Running Headless CAD Test: {dwg_path} with {script_path}")
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    
    if process.returncode == 0:
        print("Headless Test Completed Successfully.")
        # Check for error keywords in output
        if "ERROR" in stdout.upper() or "FATAL" in stdout.upper():
            print("CAD Output contains errors!")
            return False
        return True
    else:
        print(f"Headless Test Failed with exit code {process.returncode}")
        print(stderr)
        return False

if __name__ == "__main__":
    # Example verification
    test_dwg = r"c:\plugin_autocad\tests\integration\sample.dwg"
    test_scr = r"c:\plugin_autocad\tests\integration\scripts\verify_precision.scr"
    
    if os.path.exists(test_dwg) and os.path.exists(test_scr):
        run_headless_test(test_dwg, test_scr)
    else:
        print("Test files not found. Skipping execution.")
