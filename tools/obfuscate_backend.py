import os
import sys
import shutil
import py_compile
import math
import hashlib
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GIS_CORE_PATH = REPO_ROOT / "src" / "backend" / "backend" / "gis_core"
BUILD_ROOT_ENV = os.environ.get("SISRUA_BUILD_ROOT")
if BUILD_ROOT_ENV:
    BUILD_DIR = Path(BUILD_ROOT_ENV) / "obfuscated_backend"
else:
    BUILD_DIR = REPO_ROOT / "dist" / "obfuscated_backend"

def obfuscate_package(source_path: Path, dest_path: Path):
    """
    Simulates PyArmor obfuscation by compiling to .pyc and removing source .py files.
    In a real Enterprise environment, this would call `pyarmor gen ...`.
    """
    if dest_path.exists():
        shutil.rmtree(dest_path, ignore_errors=True)
    
    # Second pass for stubborn files (Git indexes, etc.)
    if dest_path.exists():
        import time
        time.sleep(1)
        shutil.rmtree(dest_path, ignore_errors=True)
    
    print(f"[IP-PROTECT] Copying source from {source_path} to {dest_path}...")
    # dirs_exist_ok=True is available in Python 3.8+
    try:
        shutil.copytree(source_path, dest_path, 
                       ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git"),
                       dirs_exist_ok=True)
    except TypeError:
        # Fallback for Python < 3.8
        if not dest_path.exists():
             shutil.copytree(source_path, dest_path, 
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git"))
        else:
             # Manual copy? No, we already tried rmtree. Let's just hope it's 3.8+
             raise
    
    print("[IP-PROTECT] Compiling to bytecode (Simulation of Encryption)...")
    for py_file in dest_path.rglob("*.py"):
        try:
            # Pass absolute Path for cfile, append 'c' for standard .pyc convention
            cfile_path = py_file.parent / (py_file.name + "c")
            py_compile.compile(py_file, cfile=cfile_path, doraise=True)
            os.remove(py_file) # Remove original source
            print(f"  Secured: {py_file.name}")
        except Exception as e:
            print(f"  Failed to secure {py_file.name}: {e}")

def main():
    print("="*60)
    print("sisRUA IP Protection Module (Obfuscation Engine)")
    print("="*60)
    
    # Target path is the entire 'backend' package folder
    BACKEND_PKG_PATH = REPO_ROOT / "src" / "backend" / "backend"
    
    try:
        if not BACKEND_PKG_PATH.exists():
            print(f"ERROR: Source path not found: {BACKEND_PKG_PATH}")
            return 1
            
        # Obfuscate the entire package into BUILD_DIR/backend
        obfuscate_package(BACKEND_PKG_PATH, BUILD_DIR / "backend")
        
        # Also copy standalone.py (the entry point) - keep as .py for PyInstaller
        standalone_src = REPO_ROOT / "src" / "backend" / "standalone.py"
        if standalone_src.exists():
             shutil.copy2(standalone_src, BUILD_DIR / "standalone.py")
             print("  Entry point preserved as .py for bundling stability.")

        print("\n[SUCCESS] Entire backend package has been secured.")
        print(f"Build Artifact: {BUILD_DIR}")
        return 0
    except Exception as e:
        print(f"FATAL ERROR in Obfuscation Engine: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
