import os
import sys
from pathlib import Path

import pytest

# Garante que `backend` (src/backend/backend) seja importável quando pytest roda a partir do repo.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Ativa modo de teste: desativa IPC e elimina esperas de retry (sem rede em CI)
os.environ.setdefault("SISRUA_TESTING", "true")


@pytest.fixture(autouse=True)
def _restore_auth_token():
    """Restaura SISRUA_AUTH_TOKEN após cada teste para evitar poluição entre testes.

    Alguns testes (ex.: test_api_auth_and_jobs) modificam SISRUA_AUTH_TOKEN diretamente via
    os.environ sem usar monkeypatch, o que afeta testes subsequentes.
    """
    original = os.environ.get("SISRUA_AUTH_TOKEN")
    yield
    if original is not None:
        os.environ["SISRUA_AUTH_TOKEN"] = original
    elif "SISRUA_AUTH_TOKEN" in os.environ:
        del os.environ["SISRUA_AUTH_TOKEN"]
