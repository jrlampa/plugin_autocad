import pytest
import time
import shutil
import os
from pathlib import Path
from backend.core.logger import sanitize_log_data
from backend.services.housekeeper import HousekeeperService

class TestLogSanitization:
    def test_sanitize_pii_keys(self):
        event_dict = {
            "event": "login_attempt",
            "username": "jdoe",
            "password": "supersecretpassword",
            "token": "ey12345",
            "nested": {
                "Audit": {
                    "details": "User login",
                    "Secret": "DoNotShare"
                }
            }
        }
        sanitized = sanitize_log_data(None, None, event_dict)
        
        assert sanitized["username"] == "*****"
        assert sanitized["password"] == "*****"
        assert sanitized["token"] == "*****"
        assert sanitized["nested"]["Audit"]["Secret"] == "*****"
        assert sanitized["event"] == "login_attempt"

    def test_sanitize_windows_paths(self):
        # Simulate a log containing a user path
        input_dict = {
            "event": "file_opened",
            "path": r"C:\Users\Jonatas Lampa\AppData\Local\Temp\sisrua.log",
            "list": [r"D:\Backups\Users\Admin\data.zip"]
        }
        
        sanitized = sanitize_log_data(None, None, input_dict)
        
        # Expect "Jonatas Lampa" to be replaced by "***"
        assert r"C:\Users\***\AppData" in sanitized["path"]
        assert "Jonatas Lampa" not in sanitized["path"]
        
        # Expect "Admin" to be replaced
        assert r"D:\Backups\Users\***\data.zip" in sanitized["list"][0]

class TestHousekeeper:
    @pytest.fixture
    def temp_dir(self, tmp_path):
        d = tmp_path / "housekeeper_test"
        d.mkdir()
        return d

    def test_cleanup_files(self, temp_dir):
        # Create an old file
        old_file = temp_dir / "old.log"
        old_file.touch()
        # Set mtime to 8 days ago
        eight_days_ago = time.time() - (8 * 86400)
        os.utime(old_file, (eight_days_ago, eight_days_ago))
        
        # Create a new file
        new_file = temp_dir / "new.log"
        new_file.touch()
        
        # Run Housekeeper (retention 7 days)
        svc = HousekeeperService(retention_days=7)
        deleted = svc.cleanup_directory(temp_dir)
        
        assert deleted == 1
        assert not old_file.exists()
        assert new_file.exists()


