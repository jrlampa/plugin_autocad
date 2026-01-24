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
from logging.handlers import RotatingFileHandler
from pathlib import Path

import uvicorn


def _configure_logging(log_level: str) -> dict:
    """
    Configura logs do backend para arquivo em %LOCALAPPDATA%\\sisRUA\\logs.
    Retorna um log_config compatível com uvicorn.
    """
    base_dir = Path(os.environ.get("LOCALAPPDATA") or str(Path.home()))
    log_dir = base_dir / "sisRUA" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "backend.log"

    # Rotação simples para evitar crescer infinito.
    # Uvicorn não expõe RotatingFileHandler por config de forma "bonita",
    # então criamos o handler e apontamos o log_config para ele via dictConfig + disable_existing_loggers=False.
    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(log_level.upper())
    # Evita duplicar handlers em re-runs.
    root.handlers = [handler]

    # Uvicorn usa loggers próprios; fazemos eles propagarem para root.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True

    # Ainda passamos um dict básico para uvicorn não recriar handlers de console.
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
                "maxBytes": 2_000_000,
                "backupCount": 3,
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
    except Exception:
        # Se falhar, o backend ainda pode rodar, mas CRS/transform podem quebrar em runtime.
        return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="sisRUA backend (standalone)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args(argv)

    log_config = _configure_logging(args.log_level)

    # Precisamos que `backend` seja importável como pacote.
    # - Em dev: a pasta "Contents" é `.../sisRUA.bundle/Contents`
    # - Em prod (EXE): o executável fica em `Contents/backend/sisrua_backend.exe`
    if getattr(sys, "frozen", False):
        contents_dir = Path(sys.executable).resolve().parent.parent
    else:
        contents_dir = Path(__file__).resolve().parent.parent

    contents_dir_str = str(contents_dir)
    if contents_dir_str not in sys.path:
        sys.path.insert(0, contents_dir_str)

    _configure_proj_data_dir()

    # Import direto: ajuda o PyInstaller a detectar dependências (osmnx/geopandas/pyproj/shapely).
    from backend.api import app  # noqa: WPS433 (import local intencional para empacotamento)

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level, log_config=log_config, access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

