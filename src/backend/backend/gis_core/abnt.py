"""
backend/gis_core/abnt.py
Conformidade com normas técnicas ABNT para levantamentos urbanos e cartografia.

Normas aplicáveis:
  - ABNT NBR 14166:1998 — Rede de referência cadastral municipal
  - ABNT NBR 13133:2021 — Execução de levantamento topográfico
  - ABNT NBR 15777:2009 — Representação de informação geográfica digital

Responsabilidade única: geração de metadados ABNT e validação de
coordenadas para exportação de arquivos DXF/CAD.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


# ---------------------------------------------------------------------------
# Escalas cartográficas padronizadas — ABNT NBR 13133:2021 Tabela 1
# ---------------------------------------------------------------------------
ABNT_ESCALAS_CADASTRAIS: List[int] = [
    500, 1_000, 2_000, 5_000, 10_000, 25_000, 50_000, 100_000,
]

# Tolerâncias planimétricas por escala (em metros) — ABNT NBR 13133:2021 §8.5
# Valores conservadores: ≤ 0,2 mm × escala
_TOLERANCIAS_M: dict[int, float] = {
    500:     0.10,
    1_000:   0.20,
    2_000:   0.40,
    5_000:   1.00,
    10_000:  2.00,
    25_000:  5.00,
    50_000:  10.0,
    100_000: 20.0,
}


@dataclass(frozen=True)
class AbntDrawingMetadata:
    """
    Metadados de desenho técnico conforme ABNT NBR 14166 e NBR 13133.

    Campos definidos segundo §5 da NBR 14166 (rede de referência cadastral):
        crs_label    — Sistema de referência (ex.: 'SIRGAS 2000 / UTM Zona 23S')
        epsg         — Código EPSG numérico da projeção
        escala       — Escala numérica (ex.: 1000 para 1:1.000)
        orgao        — Órgão ou empresa responsável pelo levantamento
        data_coleta  — Data do levantamento de campo (ISO 8601)
        versao       — Versão do arquivo gerado
        datum        — Datum geodésico (padrão: SIRGAS 2000)
        projecao     — Nome da projeção cartográfica
        unidade      — Unidade linear (padrão: m)
        zona_utm     — Zona UTM (ex.: '23S')
    """

    crs_label: str = "SIRGAS 2000 / UTM Zona 23S (EPSG:31983)"
    epsg: int = 31983
    escala: int = 1_000
    orgao: str = "sisRUA GIS Engine"
    data_coleta: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    versao: str = "0.1.0"
    datum: str = "SIRGAS 2000"
    projecao: str = "Transversa de Mercator (UTM)"
    unidade: str = "m"
    zona_utm: str = "23S"

    def escala_str(self) -> str:
        """Notação ABNT: '1:1.000' (ponto como separador de milhar)."""
        return f"1:{self.escala:,}".replace(",", ".")

    def tolerancia_m(self) -> float:
        """
        Tolerância planimétrica para a escala configurada (NBR 13133:2021 §8.5).
        Retorna o valor conservador (0,2 mm × denominador da escala).
        """
        if self.escala in _TOLERANCIAS_M:
            return _TOLERANCIAS_M[self.escala]
        # Interpolação linear para escalas não tabeladas
        return self.escala * 0.0002  # 0,2 mm em metros

    def to_dxf_header_vars(self) -> dict[str, str]:
        """
        Gera variáveis de cabeçalho DXF compatíveis com o padrão R2010.
        Usadas para rastreabilidade e BIM-LITE (NBR 14166 §7.1).
        """
        return {
            "$CUSTOMPROPERTYTAG0": "sisrua:norma",
            "$CUSTOMPROPERTYVALUE0": "ABNT NBR 14166:1998 / NBR 13133:2021",
            "$CUSTOMPROPERTYTAG1": "sisrua:datum",
            "$CUSTOMPROPERTYVALUE1": self.datum,
            "$CUSTOMPROPERTYTAG2": "sisrua:projecao",
            "$CUSTOMPROPERTYVALUE2": self.projecao,
            "$CUSTOMPROPERTYTAG3": "sisrua:crs",
            "$CUSTOMPROPERTYVALUE3": self.crs_label,
            "$CUSTOMPROPERTYTAG4": "sisrua:escala",
            "$CUSTOMPROPERTYVALUE4": self.escala_str(),
            "$CUSTOMPROPERTYTAG5": "sisrua:orgao",
            "$CUSTOMPROPERTYVALUE5": self.orgao,
            "$CUSTOMPROPERTYTAG6": "sisrua:data_coleta",
            "$CUSTOMPROPERTYVALUE6": self.data_coleta,
        }

    def to_comment_lines(self) -> List[str]:
        """
        Linhas de comentário para inclusão em blocos de título e auditoria.
        Segue a estrutura de carimbos técnicos conforme ABNT NBR 14166 §5.
        """
        return [
            f"sisRUA v{self.versao} — Motor GIS Urbano",
            f"Norma: ABNT NBR 14166:1998 / NBR 13133:2021",
            f"Datum: {self.datum}",
            f"Projecao: {self.projecao}",
            f"Zona UTM: {self.zona_utm}",
            f"CRS: {self.crs_label}",
            f"Escala: {self.escala_str()}",
            f"Tolerancia: {self.tolerancia_m():.3f} m",
            f"Unidade: {self.unidade}",
            f"Orgao: {self.orgao}",
            f"Data Coleta: {self.data_coleta}",
        ]


# ---------------------------------------------------------------------------
# Validação de coordenadas — ABNT NBR 14166:1998 §4.1
# ---------------------------------------------------------------------------

def validate_utm_coordinates(
    easting: float,
    northing: float,
    epsg: int = 31983,
) -> bool:
    """
    Valida se as coordenadas UTM estão dentro dos limites plausíveis do
    território brasileiro conforme ABNT NBR 14166:1998 §4.1.

    Brasil — hemisfério sul, zonas UTM 18 a 25 (EPSG:31978–31985):
      Easting:  100.000 m – 900.000 m
      Northing: 1.000.000 m – 10.000.000 m

    Args:
        easting:  Coordenada Leste em metros.
        northing: Coordenada Norte em metros.
        epsg:     Código EPSG do sistema projetado (não utilizado na
                  validação atual, mas mantido para rastreabilidade).

    Returns:
        True se as coordenadas estão dentro dos limites plausíveis.
    """
    if not (100_000.0 <= easting <= 900_000.0):
        return False
    if not (1_000_000.0 <= northing <= 10_000_000.0):
        return False
    return True


def nearest_abnt_escala(scale_value: int) -> int:
    """
    Retorna a escala ABNT NBR 13133:2021 mais próxima para o valor fornecido.

    Args:
        scale_value: Denominador de escala (ex.: 1500 → retorna 1000 ou 2000).

    Returns:
        Escala padronizada mais próxima da lista ABNT_ESCALAS_CADASTRAIS.
    """
    return min(ABNT_ESCALAS_CADASTRAIS, key=lambda s: abs(s - scale_value))


def build_default_metadata(epsg: int = 31983) -> AbntDrawingMetadata:
    """
    Constrói metadados ABNT padrão a partir do código EPSG da projeção.
    Usado quando o cliente não fornece metadados explícitos.

    Zonas suportadas (SIRGAS 2000 / UTM):
        EPSG:31978–31985 → Zonas 18S–25S (território brasileiro)

    Args:
        epsg: Código EPSG da projeção SIRGAS 2000 UTM.

    Returns:
        AbntDrawingMetadata com zona_utm e crs_label derivados do EPSG.
    """
    zone_num = epsg - 31960  # Zona = EPSG − 31960 (ex.: 31983 → 23)
    zona_utm = f"{zone_num}S"
    crs_label = f"SIRGAS 2000 / UTM Zona {zona_utm} (EPSG:{epsg})"
    return AbntDrawingMetadata(
        crs_label=crs_label,
        epsg=epsg,
        zona_utm=zona_utm,
    )
