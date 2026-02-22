"""
backend/gis_core/prodist.py
Conformidade ANEEL/PRODIST — Procedimentos de Distribuição de Energia Elétrica.

Normas aplicáveis:
  - PRODIST Módulo 1: Introdução (ANEEL REN 956/2021)
  - PRODIST Módulo 3: Acesso ao Sistema de Distribuição (§3.4 — faixas de segurança)
  - PRODIST Módulo 8: Qualidade da Energia Elétrica
  - NR-10:2016 — Segurança em Instalações e Serviços em Eletricidade
    (Tabela 1 — distâncias mínimas de segurança em relação a partes energizadas)

Quando regras da concessionária estão ativas, as normas ABNT são substituídas
conforme instrução do operador. A interface exibe notificação toast informando
sobre a sobreposição (ABNT suprimido pela norma da concessionária).

Responsabilidade única: geração de metadados PRODIST, faixas de segurança
e nomenclatura de camadas DXF para infraestrutura elétrica.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict


# ---------------------------------------------------------------------------
# Classe de tensão (PRODIST Módulo 3, §3.1)
# ---------------------------------------------------------------------------

class TensaoClasse(str, Enum):
    """Classe de tensão conforme PRODIST Módulo 3 §3.1."""
    BT = "BT"   # Baixa tensão: ≤ 1 kV
    MT = "MT"   # Média tensão: 1 kV < V ≤ 36,2 kV
    AT = "AT"   # Alta tensão:  > 36,2 kV


# ---------------------------------------------------------------------------
# Distâncias mínimas de segurança (NR-10:2016, Tabela 1 / PRODIST Mód. 3 §3.4)
# ---------------------------------------------------------------------------

# Distância mínima de aproximação (em metros) para condutores energizados
# em trabalho de campo. Serve como base para faixas de buffer GIS.
BUFFER_SEGURANCA_M: Dict[TensaoClasse, float] = {
    TensaoClasse.BT: 1.0,    # ≤ 1 kV        — NR-10 Tabela 1
    TensaoClasse.MT: 3.0,    # 1–36,2 kV     — NR-10 Tabela 1
    TensaoClasse.AT: 10.0,   # > 36,2 kV     — NR-10 Tabela 1
}

# Faixa de servidão padrão ANEEL por classe de tensão (Resolução 156/1997)
FAIXA_SERVIDAO_M: Dict[TensaoClasse, float] = {
    TensaoClasse.BT: 0.0,    # Não se aplica formalmente em redes urbanas BT
    TensaoClasse.MT: 5.0,    # Margem lateral de cada lado da linha MT
    TensaoClasse.AT: 20.0,   # Margem lateral de cada lado da linha AT (≥ 138 kV)
}


# ---------------------------------------------------------------------------
# Nomenclatura de camadas DXF (convenção sisRUA/ANEEL)
# ---------------------------------------------------------------------------

# Prefixo padrão para camadas de infraestrutura elétrica
_PREFIX_ANEEL = "SISRUA_ANEEL"


def camada_aneel(classe: TensaoClasse) -> str:
    """
    Retorna o nome da camada DXF para a classe de tensão informada.

    Convenção sisRUA/ANEEL:
        SISRUA_ANEEL_BT — Rede de baixa tensão
        SISRUA_ANEEL_MT — Rede de média tensão
        SISRUA_ANEEL_AT — Rede de alta tensão

    Args:
        classe: Classe de tensão (BT, MT ou AT).

    Returns:
        Nome da camada DXF (string, máx. 31 chars para compatibilidade DXF R14+).
    """
    return f"{_PREFIX_ANEEL}_{classe.value}"


def camada_buffer_aneel(classe: TensaoClasse) -> str:
    """
    Retorna o nome da camada DXF da faixa de buffer de segurança.

    Convenção: SISRUA_ANEEL_BUFFER_{BT|MT|AT}

    Args:
        classe: Classe de tensão.

    Returns:
        Nome da camada DXF para a faixa de buffer.
    """
    return f"{_PREFIX_ANEEL}_BUFFER_{classe.value}"


def buffer_de_seguranca_m(classe: TensaoClasse) -> float:
    """
    Retorna a distância mínima de segurança em metros conforme NR-10:2016.

    Usada para geração de faixas de buffer GIS ao redor de condutores
    energizados (PRODIST Módulo 3 §3.4).

    Args:
        classe: Classe de tensão (BT, MT ou AT).

    Returns:
        Distância em metros (float).
    """
    return BUFFER_SEGURANCA_M[classe]


def faixa_servidao_m(classe: TensaoClasse) -> float:
    """
    Retorna a largura da faixa de servidão em metros (Resolução ANEEL 156/1997).

    A faixa de servidão é a área reservada de cada lado da linha para
    manutenção e segurança, de uso restrito por terceiros.

    Args:
        classe: Classe de tensão.

    Returns:
        Largura lateral em metros (valor de cada lado da linha).
    """
    return FAIXA_SERVIDAO_M[classe]


# ---------------------------------------------------------------------------
# Metadados PRODIST para cabeçalho DXF / rastreabilidade
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProdistMetadata:
    """
    Metadados de conformidade ANEEL/PRODIST para exportação DXF.

    Campos registrados conforme PRODIST Módulo 1 §4 (identificação
    do levantamento) e Módulo 3 §3.1 (classe de tensão).

    Attributes:
        concessionaria: Nome da distribuidora de energia elétrica (ex.: "Light S.A.")
        classe_tensao:  Classe de tensão dominante do projeto (BT/MT/AT)
        numero_processo: Nº do processo ANEEL (opcional, ex.: "48500.004321/2024-01")
        resolucao_ref:  Resolução normativa de referência (padrão: REN 956/2021)
        data_coleta:    Data de coleta em campo (ISO 8601, AAAA-MM-DD)
        versao:         Versão do arquivo gerado
        orgao:          Órgão responsável (padrão: sisRUA GIS Engine)
        norma_ativa:    Identificação da norma ativa (padrão: "ANEEL/PRODIST")
    """
    concessionaria: str = "Não informada"
    classe_tensao: TensaoClasse = TensaoClasse.MT
    numero_processo: str = ""
    resolucao_ref: str = "ANEEL REN 956/2021 (PRODIST)"
    data_coleta: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    versao: str = "0.1.0"
    orgao: str = "sisRUA GIS Engine"
    norma_ativa: str = "ANEEL/PRODIST"

    def buffer_m(self) -> float:
        """Distância mínima de segurança para a classe de tensão configurada."""
        return buffer_de_seguranca_m(self.classe_tensao)

    def camada_rede(self) -> str:
        """Nome da camada DXF para a rede elétrica deste projeto."""
        return camada_aneel(self.classe_tensao)

    def camada_buffer(self) -> str:
        """Nome da camada DXF para a faixa de buffer de segurança."""
        return camada_buffer_aneel(self.classe_tensao)

    def to_dxf_header_vars(self) -> dict:
        """
        Gera variáveis de cabeçalho DXF compatíveis com R2010+.
        Sobrepõe os metadados ABNT quando norma da concessionária está ativa.
        """
        return {
            "$CUSTOMPROPERTYTAG0": "sisrua:norma",
            "$CUSTOMPROPERTYVALUE0": self.norma_ativa,
            "$CUSTOMPROPERTYTAG1": "sisrua:concessionaria",
            "$CUSTOMPROPERTYVALUE1": self.concessionaria,
            "$CUSTOMPROPERTYTAG2": "sisrua:classe_tensao",
            "$CUSTOMPROPERTYVALUE2": self.classe_tensao.value,
            "$CUSTOMPROPERTYTAG3": "sisrua:buffer_seguranca_m",
            "$CUSTOMPROPERTYVALUE3": f"{self.buffer_m():.1f} m",
            "$CUSTOMPROPERTYTAG4": "sisrua:resolucao",
            "$CUSTOMPROPERTYVALUE4": self.resolucao_ref,
            "$CUSTOMPROPERTYTAG5": "sisrua:orgao",
            "$CUSTOMPROPERTYVALUE5": self.orgao,
            "$CUSTOMPROPERTYTAG6": "sisrua:data_coleta",
            "$CUSTOMPROPERTYVALUE6": self.data_coleta,
        }

    def to_comment_lines(self) -> list:
        """
        Linhas de comentário para blocos de título e auditoria.
        Informa que normas ABNT foram substituídas pela norma da concessionária.
        """
        return [
            f"sisRUA v{self.versao} — Motor GIS Urbano",
            f"Norma: {self.norma_ativa}",
            f"Concessionária: {self.concessionaria}",
            f"Classe de Tensão: {self.classe_tensao.value}",
            f"Buffer de Segurança: {self.buffer_m():.1f} m (NR-10:2016)",
            f"Faixa de Servidão: {faixa_servidao_m(self.classe_tensao):.1f} m "
            f"(ANEEL RES 156/1997)",
            f"Camada Rede: {self.camada_rede()}",
            f"Resolução: {self.resolucao_ref}",
            f"Órgão: {self.orgao}",
            f"Data Coleta: {self.data_coleta}",
            "NOTA: Normas ABNT substituídas por regras da concessionária.",
        ]

    def to_fingerprint(self) -> str:
        """Identificador de rastreabilidade para $FINGERPRINTGUID do DXF."""
        conc_safe = self.concessionaria.replace("|", "-")
        return (
            f"sisrua|PRODIST|{conc_safe}|{self.classe_tensao.value}"
            f"|buffer={self.buffer_m():.1f}m"
        )


# ---------------------------------------------------------------------------
# Fábrica de ProdistMetadata
# ---------------------------------------------------------------------------

def build_prodist_metadata(
    concessionaria: str = "Não informada",
    classe_tensao: TensaoClasse = TensaoClasse.MT,
    numero_processo: str = "",
) -> ProdistMetadata:
    """
    Constrói metadados PRODIST para exportação.

    Args:
        concessionaria:  Nome da distribuidora de energia elétrica.
        classe_tensao:   Classe de tensão dominante do projeto.
        numero_processo: Nº do processo ANEEL (opcional).

    Returns:
        ProdistMetadata pronto para uso no cabeçalho DXF.
    """
    return ProdistMetadata(
        concessionaria=concessionaria,
        classe_tensao=classe_tensao,
        numero_processo=numero_processo,
    )


# ---------------------------------------------------------------------------
# Toast message — norma override notification
# ---------------------------------------------------------------------------

TOAST_NORMA_OVERRIDE = (
    "Normas da concessionária ativas — regras ABNT substituídas por ANEEL/PRODIST."
)

TOAST_NORMA_ABNT_RESTAURADA = "Normas ABNT restauradas. Regras ANEEL/PRODIST desativadas."
