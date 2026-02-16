import subprocess
import os
import sys
import tempfile
import time
from pathlib import Path

def find_accoreconsole():
    """Tries to find accoreconsole.exe in common AutoCAD installation paths."""
    base_paths = [
        os.environ.get("ProgramFiles", "C:\\Program Files") + "\\Autodesk",
    ]
    
    candidates = []
    for base in base_paths:
        if not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            if "accoreconsole.exe" in files:
                candidates.append(os.path.join(root, "accoreconsole.exe"))
    
    # Sort by version (descending) if multiple found
    candidates.sort(reverse=True)
    return candidates[0] if candidates else None

def run_test_command(accore_path, dll_path, command):
    """Generates a .scr file and runs it via accoreconsole."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.scr', delete=False) as tf:
        scr_path = tf.name
        # Use direct NETLOAD with quotes. Disable SECURELOAD first.
        # We also set TRUSTEDPATHS to include the DLL directory just in case.
        dll_dir = os.path.dirname(dll_path)
        tf.write(f"FILEDIA 0\nCMDDIA 0\nSECURELOAD 0\nTRUSTEDPATHS \"{dll_dir}\"\nNETLOAD\n\"{dll_path}\"\n{command}\nQUIT\n")
    
    print(f"[*] Executing headless test: {command}")
    print(f"[*] DLL: {dll_path}")
    start_time = time.time()
    
    try:
        # accoreconsole /s <script>
        result = subprocess.run(
            [accore_path, "/s", scr_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        duration = time.time() - start_time
        print(f"[*] Test finished in {duration:.2f}s")
        
        output = str(result.stdout or "") + str(result.stderr or "")
        
        if "TEST_SUCCESS" in output:
            print("[PASS] Command executed successfully.")
            return True, output
        else:
            print("[FAIL] Command failed or success signal not found.")
            return False, output
            
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] accoreconsole took too long.")
        return False, "TIMEOUT"
    finally:
        if os.path.exists(scr_path):
            try:
                os.remove(scr_path)
            except Exception:
                pass

def main():
    print("=== sisRUA Headless QA Orchestrator ===")
    
    accore = find_accoreconsole()
    if not accore:
        print("[ERROR] accoreconsole.exe not found. Please ensure AutoCAD is installed.")
        sys.exit(1)
        
    print(f"[*] Found AutoCAD Core Console: {accore}")
    
    # Locate the built DLL
    # Modern AutoCAD (2025+) uses .NET 8, older use .NET 4.8
    root = Path(__file__).resolve().parent.parent
    
    # Check if it's a modern AutoCAD (e.g., path contains '2025' or '2026')
    is_modern = "2025" in str(accore) or "2026" in str(accore)
    
    if is_modern:
        print("[*] Detected modern AutoCAD (2025+), targeting net8.0-windows")
        dll_path = root / "src" / "plugin" / "bin" / "x64" / "Release" / "net8.0-windows" / "sisRUA.dll"
    else:
        print("[*] Detected older AutoCAD, targeting net48")
        dll_path = root / "src" / "plugin" / "bin" / "x64" / "Release" / "net48" / "sisRUA.dll"
    
    if not dll_path.exists():
        # Fallback to try whichever exists
        alt_path = root / "src" / "plugin" / "bin" / "x64" / "Release" / ("net48" if is_modern else "net8.0-windows") / "sisRUA.dll"
        if alt_path.exists():
            print(f"[*] Fallback to alternate path: {alt_path}")
            dll_path = alt_path
        else:
            print(f"[ERROR] DLL not found. Build the project first.")
            sys.exit(1)

    # Run smoke test
    success, output = run_test_command(str(accore), str(dll_path), "SISRUA_HEADLESS_SMOKE")
    
    if success:
        print("\n[RESULT] SMOKE TEST: PASSED")
        sys.exit(0)
    else:
        print("\n[RESULT] SMOKE TEST: FAILED")
        print("--- FULL CONSOLE OUTPUT ---")
        print(output)
        sys.exit(1)

if __name__ == "__main__":
    main()
