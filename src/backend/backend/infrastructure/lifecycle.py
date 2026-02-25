import threading
import time
from pathlib import Path
from backend.application.jobs import cleanup_expired_jobs
from backend.application.housekeeper import housekeeper_service

def start_background_tasks():
    """Inicia threads de manutenção em background."""
    def run_cleanup():
        while True:
            try:
                count = cleanup_expired_jobs(max_age_seconds=3600)
            except Exception:
                pass
            time.sleep(600)

    threading.Thread(target=run_cleanup, daemon=True).start()

    def run_housekeeping():
        try:
            targets = []
            for name in ("logs", "cache"):
                d = Path(name).resolve()
                if d.exists():
                    targets.append(d)
                # Check root level too if running from backend dir
                d_up = Path("..") / name
                if d_up.exists():
                    targets.append(d_up.resolve())
                    
            housekeeper_service.run_daily_cleanup(targets)
        except Exception:
            pass

    # Rodar housekeeping uma vez no startup
    threading.Thread(target=run_housekeeping, daemon=True).start()
