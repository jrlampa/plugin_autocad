"""
backend/domain/prodist.py
Re-exporta metadados e funções ANEEL/PRODIST de `backend.gis_core.prodist`.
"""
from backend.gis_core.prodist import (
    TensaoClasse,
    BUFFER_SEGURANCA_M,
    FAIXA_SERVIDAO_M,
    camada_aneel,
    camada_buffer_aneel,
    buffer_de_seguranca_m,
    faixa_servidao_m,
    ProdistMetadata,
    build_prodist_metadata,
    TOAST_NORMA_OVERRIDE,
    TOAST_NORMA_ABNT_RESTAURADA,
)

__all__ = [
    "TensaoClasse",
    "BUFFER_SEGURANCA_M",
    "FAIXA_SERVIDAO_M",
    "camada_aneel",
    "camada_buffer_aneel",
    "buffer_de_seguranca_m",
    "faixa_servidao_m",
    "ProdistMetadata",
    "build_prodist_metadata",
    "TOAST_NORMA_OVERRIDE",
    "TOAST_NORMA_ABNT_RESTAURADA",
]
