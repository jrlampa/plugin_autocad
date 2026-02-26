"""
backend.domain/blocks.py
Biblioteca de blocos CAD para infraestrutura elétrica de distribuição MT/BT.

Nomenclatura conforme práticas das distribuidoras brasileiras (Light/Enel).
Os blocos são definidos como símbolos técnicos 2D em escala 1:1000.

BIM-LITE: cada bloco carrega metadados semânticos (XDATA APPID SISRUA)
  - sisrua:class  → "block"
  - sisrua:block  → nome do bloco (ex.: "POSTE_CONCRETO_BF")
  - sisrua:layer  → camada DXF
  - sisrua:tensao → classe de tensão (BT / MT / AT)

Referências:
  - PRODIST Módulo 3 §3.4 (faixas de segurança)
  - NR-10:2016 Tabela 1 (distâncias mínimas)
  - NBR 5419:2015 (para-raios)
  - Padrão de projeto Light S.A. / Enel Distribuição
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------

class TipoBloco(str, Enum):
    """Categoria funcional do bloco CAD."""
    POSTE = "poste"
    TRANSFORMADOR = "transformador"
    MEDIDOR = "medidor"
    CHAVE = "chave"
    CAIXA = "caixa"
    PROTECAO = "protecao"


class TensaoBloco(str, Enum):
    """Classe de tensão do bloco CAD (PRODIST Módulo 3 §3.1)."""
    BT = "BT"   # ≤ 1 kV
    MT = "MT"   # 1 kV < V ≤ 36,2 kV
    AT = "AT"   # > 36,2 kV
    MULTI = "MULTI"  # MT/BT (transformadores)


# ---------------------------------------------------------------------------
# Dataclass principal
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BlocoDefinicao:
    """
    Metadados de um bloco CAD de infraestrutura elétrica.

    Attributes:
        nome:        Identificador único do bloco (usado como chave no DXF).
        descricao:   Descrição técnica legível (pt-BR).
        tipo:        Categoria funcional do bloco.
        tensao:      Classe de tensão associada.
        layer:       Camada DXF padrão para inserção.
        escala:      Fator de escala padrão para inserção 1:1000.
        rotacao:     Rotação padrão (graus) para inserção.
        simbolo_svg: Caminho relativo ao SVG de referência UI (opcional).
        norma_ref:   Norma de referência para o componente.
    """
    nome: str
    descricao: str
    tipo: TipoBloco
    tensao: TensaoBloco
    layer: str
    escala: float = 1.0
    rotacao: float = 0.0
    simbolo_svg: Optional[str] = None
    norma_ref: str = "PRODIST Módulo 3"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialização para API REST."""
        return {
            "nome": self.nome,
            "descricao": self.descricao,
            "tipo": self.tipo.value,
            "tensao": self.tensao.value,
            "layer": self.layer,
            "escala": self.escala,
            "rotacao": self.rotacao,
            "norma_ref": self.norma_ref,
            "tags": list(self.tags),
        }


# ---------------------------------------------------------------------------
# Catálogo de blocos
# ---------------------------------------------------------------------------

_CATALOGO: List[BlocoDefinicao] = [
    # ------------------------------------------------------------------ POSTES
    BlocoDefinicao(
        nome="POSTE_CONCRETO_BF",
        descricao="Poste de concreto bifásico 9m (Tipo A)",
        tipo=TipoBloco.POSTE,
        tensao=TensaoBloco.BT,
        layer="SISRUA_BT",
        norma_ref="ABNT NBR 8451 / Padrão Light",
        tags=["poste", "concreto", "bifásico", "9m", "bt"],
    ),
    BlocoDefinicao(
        nome="POSTE_CONCRETO_TF",
        descricao="Poste de concreto trifásico 11m (Tipo B)",
        tipo=TipoBloco.POSTE,
        tensao=TensaoBloco.BT,
        layer="SISRUA_BT",
        norma_ref="ABNT NBR 8451 / Padrão Light",
        tags=["poste", "concreto", "trifásico", "11m", "bt"],
    ),
    BlocoDefinicao(
        nome="POSTE_CONCRETO_MT",
        descricao="Poste de concreto para rede MT 13,2 kV",
        tipo=TipoBloco.POSTE,
        tensao=TensaoBloco.MT,
        layer="SISRUA_ANEEL_MT",
        norma_ref="PRODIST Módulo 3 §3.4 / ABNT NBR 8451",
        tags=["poste", "concreto", "mt", "13.2kv"],
    ),
    BlocoDefinicao(
        nome="POSTE_MADEIRA",
        descricao="Poste de madeira tratada (eucalipto) 9m",
        tipo=TipoBloco.POSTE,
        tensao=TensaoBloco.BT,
        layer="SISRUA_BT",
        norma_ref="ABNT NBR 8456",
        tags=["poste", "madeira", "eucalipto", "bt"],
    ),
    BlocoDefinicao(
        nome="POSTE_METALICO",
        descricao="Poste metálico (perfil) 10m",
        tipo=TipoBloco.POSTE,
        tensao=TensaoBloco.BT,
        layer="SISRUA_BT",
        norma_ref="ABNT NBR 8451",
        tags=["poste", "metálico", "bt"],
    ),
    # ---------------------------------------------------- TRANSFORMADORES
    BlocoDefinicao(
        nome="TRAFO_AEREO_MF",
        descricao="Transformador aéreo monofásico (1Φ) — 5 a 25 kVA",
        tipo=TipoBloco.TRANSFORMADOR,
        tensao=TensaoBloco.MULTI,
        layer="SISRUA_ANEEL_MT",
        norma_ref="PRODIST Módulo 3 / ABNT NBR 5416",
        tags=["trafo", "transformador", "monofásico", "aéreo", "mt", "bt"],
    ),
    BlocoDefinicao(
        nome="TRAFO_AEREO_TF",
        descricao="Transformador aéreo trifásico (3Φ) — 30 a 300 kVA",
        tipo=TipoBloco.TRANSFORMADOR,
        tensao=TensaoBloco.MULTI,
        layer="SISRUA_ANEEL_MT",
        norma_ref="PRODIST Módulo 3 / ABNT NBR 5416",
        tags=["trafo", "transformador", "trifásico", "aéreo", "mt", "bt"],
    ),
    BlocoDefinicao(
        nome="TRAFO_CABINA_TF",
        descricao="Transformador em cabina abrigada (pad-mounted) 500 kVA",
        tipo=TipoBloco.TRANSFORMADOR,
        tensao=TensaoBloco.MULTI,
        layer="SISRUA_ANEEL_MT",
        norma_ref="PRODIST Módulo 3 / ABNT NBR 5416",
        tags=["trafo", "cabina", "pad-mounted", "mt", "bt"],
    ),
    # --------------------------------------------------------- MEDIDORES
    BlocoDefinicao(
        nome="MEDIDOR_CAIXA",
        descricao="Caixa de medição padrão (unidade consumidora BT)",
        tipo=TipoBloco.MEDIDOR,
        tensao=TensaoBloco.BT,
        layer="SISRUA_BT",
        norma_ref="PRODIST Módulo 7 / Padrão Light",
        tags=["medidor", "caixa", "uc", "bt"],
    ),
    BlocoDefinicao(
        nome="MEDIDOR_COLETIVO",
        descricao="Banco de medidores coletivo (edifício / condomínio)",
        tipo=TipoBloco.MEDIDOR,
        tensao=TensaoBloco.BT,
        layer="SISRUA_BT",
        norma_ref="PRODIST Módulo 7 / Padrão Light",
        tags=["medidor", "coletivo", "condomínio", "bt"],
    ),
    # ------------------------------------------------------------ CHAVES
    BlocoDefinicao(
        nome="CHAVE_FACA_MT",
        descricao="Chave facas fusível (CFF) 13,2 kV",
        tipo=TipoBloco.CHAVE,
        tensao=TensaoBloco.MT,
        layer="SISRUA_ANEEL_MT",
        norma_ref="PRODIST Módulo 3 / ABNT NBR IEC 60282-2",
        tags=["chave", "fusível", "cff", "mt", "manobra"],
    ),
    BlocoDefinicao(
        nome="CHAVE_SECCIONADORA",
        descricao="Chave seccionadora a óleo (CSO) 13,2 kV",
        tipo=TipoBloco.CHAVE,
        tensao=TensaoBloco.MT,
        layer="SISRUA_ANEEL_MT",
        norma_ref="PRODIST Módulo 3 / ABNT NBR IEC 62271-102",
        tags=["chave", "seccionadora", "cso", "mt"],
    ),
    BlocoDefinicao(
        nome="CHAVE_RELIGADORA",
        descricao="Religadora automática (recloser) 13,2 kV",
        tipo=TipoBloco.CHAVE,
        tensao=TensaoBloco.MT,
        layer="SISRUA_ANEEL_MT",
        norma_ref="PRODIST Módulo 3 / ABNT NBR IEC 62271-111",
        tags=["chave", "religadora", "recloser", "mt", "automático"],
    ),
    # ------------------------------------------------ CAIXAS / DUTOS
    BlocoDefinicao(
        nome="CAIXA_PASSAGEM",
        descricao="Caixa de passagem subterrânea (dutos de BT/MT)",
        tipo=TipoBloco.CAIXA,
        tensao=TensaoBloco.MULTI,
        layer="SISRUA_BT",
        norma_ref="ABNT NBR 5597 / Padrão Light",
        tags=["caixa", "passagem", "subterrâneo", "duto"],
    ),
    BlocoDefinicao(
        nome="CAIXA_PASSAGEM_MT",
        descricao="Caixa de passagem subterrânea para dutos MT",
        tipo=TipoBloco.CAIXA,
        tensao=TensaoBloco.MT,
        layer="SISRUA_ANEEL_MT",
        norma_ref="ABNT NBR 5597 / Padrão Light",
        tags=["caixa", "passagem", "subterrâneo", "mt"],
    ),
    # ------------------------------------------------------ PROTEÇÃO
    BlocoDefinicao(
        nome="PARA_RAIOS_MT",
        descricao="Para-raios de óxido de zinco (ZnO) 13,2 kV — NR-10 / NBR 5419",
        tipo=TipoBloco.PROTECAO,
        tensao=TensaoBloco.MT,
        layer="SISRUA_ANEEL_MT",
        norma_ref="NBR 5419:2015 / PRODIST Módulo 3",
        tags=["para-raios", "znO", "mt", "proteção", "surto"],
    ),
    BlocoDefinicao(
        nome="ATERRAMENTO",
        descricao="Ponto de aterramento (haste copperweld)",
        tipo=TipoBloco.PROTECAO,
        tensao=TensaoBloco.MULTI,
        layer="SISRUA_BT",
        norma_ref="NBR 5410:2004 / NR-10:2016",
        tags=["aterramento", "haste", "copperweld", "proteção"],
    ),
]

# Índice nome → bloco (lookup rápido)
_INDICE: dict[str, BlocoDefinicao] = {b.nome: b for b in _CATALOGO}


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def listar_blocos(
    tipo: Optional[TipoBloco] = None,
    tensao: Optional[TensaoBloco] = None,
) -> List[BlocoDefinicao]:
    """
    Retorna a lista de blocos disponíveis, opcionalmente filtrada.

    Args:
        tipo:   Filtra por categoria funcional (ex.: TipoBloco.POSTE).
        tensao: Filtra por classe de tensão (ex.: TensaoBloco.MT).

    Returns:
        Lista de BlocoDefinicao correspondentes aos filtros.
    """
    resultado = list(_CATALOGO)
    if tipo is not None:
        resultado = [b for b in resultado if b.tipo == tipo]
    if tensao is not None:
        resultado = [b for b in resultado if b.tensao == tensao]
    return resultado


def obter_bloco(nome: str) -> Optional[BlocoDefinicao]:
    """
    Retorna um bloco pelo nome exato.

    Args:
        nome: Nome do bloco (ex.: "POSTE_CONCRETO_BF").

    Returns:
        BlocoDefinicao ou None se não encontrado.
    """
    return _INDICE.get(nome)


def nomes_disponiveis() -> List[str]:
    """Retorna lista de todos os nomes de blocos disponíveis."""
    return list(_INDICE.keys())
