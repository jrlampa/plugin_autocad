import os
import sys
from pathlib import Path

# Garante que `backend` (src/backend/backend) seja importável quando pytest roda a partir do repo.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

for _cov_file in _ROOT.glob(".coverage*"):
    # Skip .coveragerc — that is configuration, not a stale data file
    if _cov_file.name == ".coveragerc":
        continue
    try:
        _cov_file.unlink(missing_ok=True)
    except Exception:
        pass

# Ativa modo de teste: desativa IPC e elimina esperas de retry (sem rede em CI)
os.environ["SISRUA_TESTING"] = "true"

# Define um token padrão para testes que importam a API antes de sobrescrever via monkeypatch
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-token")

