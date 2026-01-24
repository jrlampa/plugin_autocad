"""
Entry-point para empacotamento (ex.: PyInstaller).

Este script inicia o Uvicorn apontando para `backend.api:app`.
Ele existe para gerar um `sisrua_backend.exe` que roda sem Python instalado.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="sisRUA backend (standalone)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="warning")
    args = parser.parse_args(argv)

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

    # Import direto: ajuda o PyInstaller a detectar dependências (osmnx/geopandas/pyproj/shapely).
    from backend.api import app  # noqa: WPS433 (import local intencional para empacotamento)

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

