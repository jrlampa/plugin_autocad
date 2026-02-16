"""
Entry-point para empacotamento (ex.: PyInstaller).

Este script inicia o Uvicorn apontando para `backend.api:app`.
Ele existe para gerar um `sisrua_backend.exe` que roda sem Python instalado.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any
from logging.handlers import RotatingFileHandler
from pathlib import Path

import uvicorn


def _configure_logging(log_level: str) -> dict:
    """
    Configura logs do backend para arquivo em %TEMP%\\sisRuaBackendDebug.log
    para facilitar o debug em máquinas de clientes.
    """
    import tempfile
    log_file = Path(tempfile.gettempdir()) / "sisRuaBackendDebug.log"
    
    # Absolute path log for forensics
    print(f"DEBUG: sisRUA Backend starting. Log: {log_file}")
    print(f"DEBUG: sys.executable: {sys.executable}")
    print(f"DEBUG: sys._MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")

    # Rotação simples
    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=5_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(log_level.upper())
    root.handlers = [handler]

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": str(log_file),
                "maxBytes": 5_000_000,
                "backupCount": 2,
                "encoding": "utf-8",
            }
        },
        "loggers": {
            "uvicorn": {"handlers": ["file"], "level": log_level.upper(), "propagate": False},
            "uvicorn.error": {"handlers": ["file"], "level": log_level.upper(), "propagate": False},
            "uvicorn.access": {"handlers": ["file"], "level": log_level.upper(), "propagate": False},
        },
    }


def _configure_proj_data_dir() -> None:
    """
    Em modo PyInstaller, garantir que o PROJ consiga achar seus dados.
    """
    try:
        from pyproj import datadir as _pyproj_datadir
        data_dir = _pyproj_datadir.get_data_dir()
        if data_dir:
            os.environ.setdefault("PROJ_LIB", data_dir)
            print(f"DEBUG: PROJ_LIB set to {data_dir}")
    except Exception as e:
        print(f"DEBUG: Failed to set PROJ_LIB: {e}")
        return


def _ensure_single_instance() -> Any:
    if os.name != "nt":
        return None
    try:
        import win32event
        import win32api
        import winerror
        
        mutex_name = "sisRUA_Backend_Mutex_v2"
        mutex = win32event.CreateMutex(None, False, mutex_name)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            sys.exit(0)
        return mutex
    except ImportError:
        return None

def main(argv: list[str] | None = None) -> int:
    _backend_mutex = _ensure_single_instance()
    parser = argparse.ArgumentParser(description="sisRUA backend (standalone)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args(argv)

    log_config = _configure_logging(args.log_level)

    # Path discovery for imports
    if getattr(sys, "frozen", False):
        contents_dir = Path(sys._MEIPASS).resolve()
    else:
        contents_dir = Path(__file__).resolve().parent

    sys.path.insert(0, str(contents_dir))

    _configure_proj_data_dir()

    from backend.api import app
    from backend.core.config import get_resource_path
    from backend.core.database import get_db_path
    from backend.core.logger import logger
    
    # Debug logging: Log all resolved paths for troubleshooting on client machines
    logger.info(
        "pyinstaller_paths_resolved",
        frozen=getattr(sys, "frozen", False),
        base_path=str(contents_dir),
        frontend_dist=str(get_resource_path("frontend/dist")),
        resources_dir=str(get_resource_path("Resources")),
        database_path=str(get_db_path()),
        executable=sys.executable,
        host=args.host,
        port=args.port
    ) 

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level, log_config=log_config, access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

