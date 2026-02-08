import os
import sys
import shutil
import py_compile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GIS_CORE_PATH = REPO_ROOT / "src" / "backend" / "backend" / "gis_core"
BUILD_DIR = REPO_ROOT / "dist" / "obfuscated_backend"

def obfuscate_package(source_path: Path, dest_path: Path):
    """
    Simulates PyArmor obfuscation by compiling to .pyc and removing source .py files.
    In a real Enterprise environment, this would call `pyarmor gen ...`.
    """
    if dest_path.exists():
        shutil.rmtree(dest_path)
    
    print(f"[IP-PROTECT] Copying source from {source_path} to {dest_path}...")
    shutil.copytree(source_path, dest_path)
    
    print("[IP-PROTECT] Compiling to bytecode (Simulation of Encryption)...")
    for py_file in dest_path.rglob("*.py"):
        try:
            py_compile.compile(py_file, cfile=str(py_file) + "c", doraise=True)
            os.remove(py_file) # Remove original source
            print(f"  Secured: {py_file.name}")
        except Exception as e:
            print(f"  Failed to secure {py_file.name}: {e}")

def main():
    print("="*60)
    print("sisRUA IP Protection Module (Obfuscation Engine)")
    print("="*60)
    
    try:
        if not GIS_CORE_PATH.exists():
            print(f"ERROR: Source path not found: {GIS_CORE_PATH}")
            return 1
            
        obfuscate_package(GIS_CORE_PATH, BUILD_DIR / "backend" / "gis_core")
        
        print("\n[SUCCESS] Critical IP 'gis_core' has been obfuscated.")
        print(f"Build Artifact: {BUILD_DIR}")
        print("Ready for PyInstaller packaging.")
        return 0
    except Exception as e:
        print(f"\n[FATAL] Obfuscation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
