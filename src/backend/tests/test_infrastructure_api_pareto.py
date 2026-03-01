from __future__ import annotations

import importlib
import os
import runpy
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _reload_infra_api():
    import backend.infrastructure.api as api_mod

    return importlib.reload(api_mod)


def _fresh_import_infra_api():
    sys.modules.pop("backend.infrastructure.api", None)
    return importlib.import_module("backend.infrastructure.api")


def _purge_infra_api_module_cache():
    for modname in list(sys.modules.keys()):
        if modname == "backend.infrastructure.api" or modname.startswith("backend.infrastructure.api"):
            sys.modules.pop(modname, None)


def test_infrastructure_api_importerror_branches(monkeypatch, tmp_path):
    monkeypatch.setenv("SISRUA_TESTING", "true")
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "pareto-token")

    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "matplotlib":
            raise ImportError("no matplotlib")
        if name == "sentry_sdk":
            raise ImportError("no sentry")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    api_mod = _reload_infra_api()
    c = TestClient(api_mod.app)
    r = c.get("/api/v1/health")
    assert r.status_code == 200


def test_infrastructure_api_generates_token_when_missing(monkeypatch):
    monkeypatch.setenv("SISRUA_TESTING", "true")
    monkeypatch.delenv("SISRUA_AUTH_TOKEN", raising=False)

    _purge_infra_api_module_cache()
    api_mod = _fresh_import_infra_api()

    assert api_mod.AUTH_TOKEN
    assert os.environ.get("SISRUA_AUTH_TOKEN")


def test_infrastructure_api_sentry_init_exception(monkeypatch, tmp_path):
    monkeypatch.delenv("SISRUA_TESTING", raising=False)
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "pareto-token")
    monkeypatch.setenv("SENTRY_DSN", "http://example.invalid/1")

    sentry_sdk = types.ModuleType("sentry_sdk")

    def _boom_init(**kwargs):
        raise RuntimeError("boom")

    sentry_sdk.init = _boom_init

    integ_fastapi = types.ModuleType("sentry_sdk.integrations.fastapi")

    class FastApiIntegration:  # noqa: N801
        def __init__(self, **kwargs):
            pass

    integ_fastapi.FastApiIntegration = FastApiIntegration

    integ_starlette = types.ModuleType("sentry_sdk.integrations.starlette")

    class StarletteIntegration:  # noqa: N801
        def __init__(self, **kwargs):
            pass

    integ_starlette.StarletteIntegration = StarletteIntegration

    monkeypatch.setitem(sys.modules, "sentry_sdk", sentry_sdk)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.fastapi", integ_fastapi)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.starlette", integ_starlette)

    import backend.shared.config as cfg

    importlib.reload(cfg)

    api_mod = _reload_infra_api()
    c = TestClient(api_mod.app)
    r = c.get("/api/v1/health")
    assert r.status_code == 200


def test_infrastructure_api_lifespan_ipc_and_shutdown_exception(monkeypatch):
    monkeypatch.delenv("SISRUA_TESTING", raising=False)
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "pareto-token")

    import backend.shared.ipc as ipc

    class DummyIpcServer:
        PIPE_NAME = "dummy"

        def __init__(self, token):
            self.token = token

        def start(self):
            return None

    monkeypatch.setattr(ipc, "IpcServer", DummyIpcServer)

    import backend.shared.lifecycle as lifecycle

    def _boom_wait(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(lifecycle.job_registry, "wait_for_completion", _boom_wait)

    api_mod = _reload_infra_api()

    # TestClient must be used as context manager to trigger lifespan exit.
    with TestClient(api_mod.app) as c:
        r = c.get("/api/v1/health")
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_infrastructure_api_lifespan_executes_ipc_block_and_shutdown_except(monkeypatch):
    monkeypatch.delenv("SISRUA_TESTING", raising=False)
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "pareto-token")

    import backend.infrastructure.lifecycle as infra_lifecycle

    monkeypatch.setattr(infra_lifecycle, "start_background_tasks", lambda: None)

    import backend.shared.ipc as ipc

    class FailingIpcServer:
        PIPE_NAME = "dummy"

        def __init__(self, token):
            self.token = token

        def start(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(ipc, "IpcServer", FailingIpcServer)

    import backend.shared.lifecycle as lifecycle

    def _boom_wait(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(lifecycle.job_registry, "wait_for_completion", _boom_wait)

    api_mod = _reload_infra_api()
    async with api_mod._lifespan(api_mod.app):
        pass


def test_infrastructure_api_lifespan_ipc_start_failure_is_swallowed(monkeypatch):
    monkeypatch.delenv("SISRUA_TESTING", raising=False)
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "pareto-token")

    import backend.shared.ipc as ipc

    class FailingIpcServer:
        PIPE_NAME = "dummy"

        def __init__(self, token):
            self.token = token

        def start(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(ipc, "IpcServer", FailingIpcServer)

    api_mod = _reload_infra_api()
    with TestClient(api_mod.app) as c:
        r = c.get("/api/v1/health")
        assert r.status_code == 200


def test_infrastructure_api_maybe_mount_frontend_frozen_meipass(monkeypatch, tmp_path):
    monkeypatch.setenv("SISRUA_TESTING", "true")
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "pareto-token")

    dist_dir = tmp_path / "frontend" / "dist"
    dist_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    api_mod = _reload_infra_api()

    # The mount is performed at import time; ensure app exists
    assert api_mod.app is not None


def test_infrastructure_api_maybe_mount_frontend_frozen_executable_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("SISRUA_TESTING", "true")
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "pareto-token")

    # Force frozen path without _MEIPASS, so it falls back to sys.executable parent/parent.
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    if hasattr(sys, "_MEIPASS"):
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    fake_exe = tmp_path / "bin" / "app.exe"
    fake_exe.parent.mkdir(parents=True, exist_ok=True)
    fake_exe.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", str(fake_exe), raising=False)

    api_mod = _reload_infra_api()
    # Execute again to ensure the frozen sys.executable fallback path is covered.
    api_mod._maybe_mount_frontend()
    assert api_mod.app is not None


def test_infrastructure_api_main_block_runs(monkeypatch):
    monkeypatch.setenv("SISRUA_TESTING", "true")
    monkeypatch.setenv("SISRUA_AUTH_TOKEN", "pareto-token")

    uvicorn = types.ModuleType("uvicorn")
    calls = {"n": 0}

    def _run(*args, **kwargs):
        calls["n"] += 1

    uvicorn.run = _run
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn)

    # Execute module as __main__ to hit the guarded block.
    runpy.run_module("backend.infrastructure.api", run_name="__main__")
    assert calls["n"] == 1
