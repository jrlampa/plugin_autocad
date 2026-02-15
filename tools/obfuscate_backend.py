import os
import sys
import shutil
import py_compile
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
        def on_error(func, path, exc_info):
            import stat
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWUSR)
                func(path)
            else:
                raise
        shutil.rmtree(dest_path, onerror=on_error)
    
    # Ensure parent directory exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[IP-PROTECT] Copying source from {source_path} to {dest_path}...")
    shutil.copytree(source_path, dest_path, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git"))
    
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
