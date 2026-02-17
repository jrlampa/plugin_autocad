import os
import shutil
from pathlib import Path

def sanitize():
    repo_root = Path(__file__).resolve().parent.parent
    folders_to_purge = ["history", "backup", ".tmp"]
    
    print(f"Starting repository sanitization at: {repo_root}")
    
    purged_count = 0
    for folder in folders_to_purge:
        path = repo_root / folder
        if path.exists() and path.is_dir():
            print(f"Purging legacy folder: {folder}...")
            try:
                shutil.rmtree(path)
                purged_count += 1
            except Exception as e:
                print(f"Failed to purge {folder}: {e}")
                
    # Also look for any large .zip or .log files in the root that shouldn't be there
    root_files = list(repo_root.glob("*.zip")) + list(repo_root.glob("*.log"))
    for file in root_files:
        if file.name.startswith("evidence_") or file.name == "debug.log":
            print(f"Removing artifact: {file.name}")
            file.unlink()
            purged_count += 1

    print(f"Sanitization complete. {purged_count} legacy items removed.")

if __name__ == "__main__":
    sanitize()
