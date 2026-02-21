import os
import sys
from pathlib import Path

# Garante que `backend` (src/backend/backend) seja importável quando pytest roda a partir do repo.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Ativa modo de teste: desativa IPC e elimina esperas de retry (sem rede em CI)
os.environ.setdefault("SISRUA_TESTING", "true")

