import os
import time
import shutil
from pathlib import Path
from typing import List, Union
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class HousekeeperService:
    """
    Automated Data Lifecycle Management.
    Enforces retention policies by deleting old files from specified directories.
    """
    
    def __init__(self, retention_days: int = 7):
        self.retention_seconds = retention_days * 86400
        self.dry_run = False # Set to True for testing locally without deletion

    def cleanup_directory(self, directory_path: Union[str, Path], recursive: bool = False) -> int:
        """
        Scans a directory and deletes files older than retention_days.
        Returns the count of deleted files.
        """
        dir_path = Path(directory_path)
        if not dir_path.exists():
            logger.warning("housekeeper_directory_not_found", path=str(dir_path))
            return 0

        deleted_count = 0
        now = time.time()
        
        try:
            # Walk if recursive, else just list dir
            if recursive:
                files = dir_path.rglob('*')
            else:
                files = dir_path.glob('*')

            for file_path in files:
                if not file_path.is_file():
                    continue

                try:
                    stat = file_path.stat()
                    # Check modification time
                    age = now - stat.st_mtime
                    
                    if age > self.retention_seconds:
                        if not self.dry_run:
                            file_path.unlink()
                        deleted_count += 1
                        logger.info("file_deleted_retention_policy", path=str(file_path), age_days=round(age/86400, 1))
                except Exception as e:
                    logger.error("housekeeper_delete_failed", path=str(file_path), error=str(e))
                    
        except Exception as e:
            logger.error("housekeeper_scan_failed", path=str(dir_path), error=str(e))

        return deleted_count

    def run_daily_cleanup(self, target_directories: List[Union[str, Path]]):
        """
        Executes the cleanup routine on a list of directories.
        """
        logger.info("housekeeper_started", targets=[str(t) for t in target_directories])
        total_deleted = 0
        
        for d in target_directories:
            total_deleted += self.cleanup_directory(d, recursive=True)
            
        logger.info("housekeeper_finished", total_deleted=total_deleted)
        return total_deleted

housekeeper_service = HousekeeperService(retention_days=7)
