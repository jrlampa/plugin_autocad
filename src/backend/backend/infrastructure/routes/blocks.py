"""
backend/infrastructure/routes/blocks.py
Router de blocos CAD de infraestrutura elétrica (catálogo sisRUA).

Expõe o catálogo de blocos disponíveis para:
  - Frontend (paleta de símbolos da sidebar)
  - Plugin C# (autocompletar ao inserir blocos via SISRUA_INSERIR)
  - Exportação DXF headless (define_electrical_blocks)

BIM-LITE: cada bloco retornado inclui metadados semânticos
(classe, tensão, camada, norma de referência).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from backend.shared.auth import require_token
from backend.shared.logger import get_logger
from backend.domain.blocks import (
    TipoBloco,
    TensaoBloco,
    listar_blocos,
    obter_bloco,
    nomes_disponiveis,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/v1/blocks", tags=["Blocos CAD"])
async def list_blocks(
    tipo: Optional[str] = Query(None, description="Filtro por tipo (poste, transformador, medidor, chave, caixa, protecao)"),
    tensao: Optional[str] = Query(None, description="Filtro por classe de tensão (BT, MT, AT, MULTI)"),
    _: None = Depends(require_token),
) -> dict:
    """
    Lista todos os blocos CAD disponíveis no catálogo sisRUA.

    Filtros opcionais por `tipo` e `tensao` permitem ao frontend popular
    a paleta de símbolos conforme a norma ativa (ABNT/PRODIST).

    **Tipos disponíveis:** poste, transformador, medidor, chave, caixa, protecao
    **Classes de tensão:** BT, MT, AT, MULTI

    Returns:
        JSON com lista de blocos e contagem total.
    """
    tipo_enum: Optional[TipoBloco] = None
    tensao_enum: Optional[TensaoBloco] = None

    if tipo is not None:
        try:
            tipo_enum = TipoBloco(tipo.lower())
        except ValueError:
            tipos_validos = [t.value for t in TipoBloco]
            raise HTTPException(
                status_code=422,
                detail=f"Tipo inválido: '{tipo}'. Valores válidos: {tipos_validos}",
            )

    if tensao is not None:
        try:
            tensao_enum = TensaoBloco(tensao.upper())
        except ValueError:
            tensoes_validas = [t.value for t in TensaoBloco]
            raise HTTPException(
                status_code=422,
                detail=f"Tensão inválida: '{tensao}'. Valores válidos: {tensoes_validas}",
            )

    blocos = listar_blocos(tipo=tipo_enum, tensao=tensao_enum)
    logger.info("blocks_listed", count=len(blocos), tipo=tipo, tensao=tensao)

    return {
        "blocos": [b.to_dict() for b in blocos],
        "total": len(blocos),
    }


@router.get("/api/v1/blocks/names", tags=["Blocos CAD"])
async def list_block_names(
    _: None = Depends(require_token),
) -> List[str]:
    """
    Retorna apenas os nomes dos blocos disponíveis.

    Útil para o plugin C# popular autocompletar de INSERT sem carregar
    todos os metadados.
    """
    names = nomes_disponiveis()
    logger.info("block_names_listed", count=len(names))
    return names


@router.get("/api/v1/blocks/{nome}", tags=["Blocos CAD"])
async def get_block(
    nome: str,
    _: None = Depends(require_token),
) -> dict:
    """
    Retorna os metadados de um bloco específico pelo nome.

    Args:
        nome: Nome exato do bloco (ex.: POSTE_CONCRETO_BF).

    Returns:
        Metadados do bloco ou 404 se não encontrado.
    """
    bloco = obter_bloco(nome.upper())
    if bloco is None:
        raise HTTPException(
            status_code=404,
            detail=f"Bloco '{nome}' não encontrado. Use GET /api/v1/blocks/names para listar os disponíveis.",
        )
    logger.info("block_fetched", nome=nome)
    return bloco.to_dict()
