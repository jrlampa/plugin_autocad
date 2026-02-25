"""
tests/test_topology.py
Testes unitários do TopologyHealer (gis_core/topology.py).

Validação do algoritmo Union-Find de node snapping:
  - Endpoints distantes não devem ser alterados
  - Endpoints dentro da tolerância devem ser snapped ao centróide
  - Junções com 3+ polilínias (T/X) devem ser corretamente snap
  - Features do tipo Point passam sem alteração
  - Contador healed_nodes deve ser atualizado

Coordenadas de referência (conforme MEMORY.MD):
  REF_E = 714316.0 m  (UTM 23S — -22.15018°, -42.92185°)
  REF_N = 7549084.0 m
"""
from __future__ import annotations

import math
import pytest
from typing import List

from backend.domain.topology import TopologyHealer
from backend.domain.dto import CadFeature


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REF_E = 714316.0
REF_N = 7549084.0


def _polyline(coords: List[List[float]], layer: str = "TEST") -> CadFeature:
    """Cria um CadFeature do tipo Polyline com as coordenadas dadas."""
    return CadFeature(
        feature_type="Polyline",
        layer=layer,
        coords_xy=coords,
    )


def _point(x: float, y: float) -> CadFeature:
    """Cria um CadFeature do tipo Point."""
    return CadFeature(
        feature_type="Point",
        layer="TEST_PONTOS",
        insertion_point_xy=[x, y],
        block_name="POSTE",
    )


# ---------------------------------------------------------------------------
# Testes de passthrough (sem snap)
# ---------------------------------------------------------------------------

def test_topology_healer_single_feature_passthrough():
    """Com apenas 1 polilinha não há endpoints para snap; deve retornar inalterada."""
    healer = TopologyHealer(snap_tolerance=0.05)
    feat = _polyline([[0.0, 0.0], [100.0, 0.0]])
    result = healer.heal_network([feat])
    assert result[0].coords_xy[0] == [0.0, 0.0]
    assert result[0].coords_xy[-1] == [100.0, 0.0]
    assert healer.stats["healed_nodes"] == 0


def test_topology_healer_far_endpoints_not_snapped():
    """Endpoints separados por >tolerância não devem ser snapped."""
    healer = TopologyHealer(snap_tolerance=0.05)
    a = _polyline([[REF_E, REF_N], [REF_E + 100.0, REF_N]])
    b = _polyline([[REF_E + 500.0, REF_N], [REF_E + 600.0, REF_N]])

    result = healer.heal_network([a, b])

    # Nenhum endpoint foi alterado
    assert result[0].coords_xy[0] == [REF_E, REF_N]
    assert result[0].coords_xy[-1] == [REF_E + 100.0, REF_N]
    assert result[1].coords_xy[0] == [REF_E + 500.0, REF_N]
    assert healer.stats["healed_nodes"] == 0


# ---------------------------------------------------------------------------
# Testes de snapping
# ---------------------------------------------------------------------------

def test_topology_healer_snaps_close_endpoints():
    """
    Dois endpoints separados por menos que snap_tolerance devem ser snapped
    ao centróide (posição média entre eles).
    """
    healer = TopologyHealer(snap_tolerance=0.10)

    # Road A termina em (100.0, 0.0)
    a = _polyline([[0.0, 0.0], [100.0, 0.0]])
    # Road B começa em (100.04, 0.0) — 4 cm de gap (< 10 cm de tolerância)
    b = _polyline([[100.04, 0.0], [200.0, 0.0]])

    result = healer.heal_network([a, b])

    end_a = result[0].coords_xy[-1]
    start_b = result[1].coords_xy[0]

    # Centróide de (100.0, 0.0) e (100.04, 0.0) = (100.02, 0.0)
    assert abs(end_a[0] - 100.02) < 1e-9, f"end_a.x esperado 100.02, obteve {end_a[0]}"
    assert abs(start_b[0] - 100.02) < 1e-9, f"start_b.x esperado 100.02, obteve {start_b[0]}"
    assert healer.stats["healed_nodes"] == 1


def test_topology_healer_does_not_snap_above_tolerance():
    """Endpoints separados por mais que snap_tolerance não devem ser snapped."""
    tol = 0.10
    healer = TopologyHealer(snap_tolerance=tol)

    a = _polyline([[0.0, 0.0], [100.0, 0.0]])
    # Separados por 2× a tolerância — claramente fora do intervalo
    b = _polyline([[100.0 + tol * 2, 0.0], [200.0, 0.0]])

    healer.heal_network([a, b])
    assert healer.stats["healed_nodes"] == 0


def test_topology_healer_snaps_t_junction():
    """
    Junção em T (3 polilínias compartilhando o mesmo endpoint) deve ser
    corretamente snapped: os 3 endpoints devem convergir para o centróide.
    """
    healer = TopologyHealer(snap_tolerance=0.10)

    # Rua principal: de (0, 0) até (100, 0)
    main_road = _polyline([[0.0, 0.0], [100.0, 0.0]])
    # Rua lateral começa em (100.03, 0.0) — gap < tol
    side_a = _polyline([[100.03, 0.0], [100.03, 50.0]])
    # Outra lateral começa em (99.98, 0.0) — gap < tol
    side_b = _polyline([[99.98, 0.0], [99.98, -50.0]])

    result = healer.heal_network([main_road, side_a, side_b])

    # Todos os endpoints próximos de (100, 0) devem convergir para o centróide
    # centróide de (100.0, 0.0), (100.03, 0.0), (99.98, 0.0)
    expected_x = (100.0 + 100.03 + 99.98) / 3
    end_main = result[0].coords_xy[-1]
    start_a = result[1].coords_xy[0]
    start_b = result[2].coords_xy[0]

    assert abs(end_main[0] - expected_x) < 1e-9
    assert abs(start_a[0] - expected_x) < 1e-9
    assert abs(start_b[0] - expected_x) < 1e-9
    assert healer.stats["healed_nodes"] == 2  # 3 endpoints snapped → healed = len(group) - 1 = 2


# ---------------------------------------------------------------------------
# Testes de preservação de Points
# ---------------------------------------------------------------------------

def test_topology_healer_preserves_point_features():
    """Point features devem passar pelo heal_network sem alteração."""
    healer = TopologyHealer(snap_tolerance=0.10)

    poly = _polyline([[0.0, 0.0], [100.0, 0.0]])
    pt = _point(REF_E, REF_N)

    result = healer.heal_network([poly, pt])

    # O Point deve estar na mesma posição
    point_in_result = next(f for f in result if f.feature_type == "Point")
    assert point_in_result.insertion_point_xy == [REF_E, REF_N]


def test_topology_healer_empty_features():
    """Lista vazia não deve lançar exceção."""
    healer = TopologyHealer()
    result = healer.heal_network([])
    assert result == []


# ---------------------------------------------------------------------------
# Testes de assinaturas de integridade
# ---------------------------------------------------------------------------

def test_topology_healer_integrity_signature_deterministic():
    """A assinatura deve ser determinística para o mesmo conjunto de features."""
    healer = TopologyHealer()
    features = [_polyline([[0.0, 0.0], [100.0, 0.0]])]
    sig1 = healer.get_integrity_signature(features)
    sig2 = healer.get_integrity_signature(features)
    assert sig1 == sig2
    assert sig1.startswith("SIS-")


def test_topology_healer_robust_signature_deterministic():
    """A assinatura robusta deve ser determinística para a mesma geometria."""
    healer = TopologyHealer()
    features = [
        _polyline([[0.0, 0.0], [100.0, 0.0]]),
        _polyline([[100.0, 0.0], [100.0, 50.0]]),
    ]
    sig1 = healer.get_robust_integrity_signature(features)
    sig2 = healer.get_robust_integrity_signature(features)
    assert sig1 == sig2
    assert sig1.startswith("SIS-AUDIT-")


def test_topology_healer_signature_changes_with_geometry():
    """Assinaturas diferentes para geometrias diferentes."""
    healer = TopologyHealer()
    features_a = [_polyline([[0.0, 0.0], [100.0, 0.0]])]
    features_b = [_polyline([[0.0, 0.0], [200.0, 0.0]])]
    assert healer.get_integrity_signature(features_a) != healer.get_integrity_signature(features_b)


# ---------------------------------------------------------------------------
# Testes de stats e relatório
# ---------------------------------------------------------------------------

def test_topology_healer_stats_reset_between_instances():
    """Cada instância de TopologyHealer começa com stats zeradas."""
    h1 = TopologyHealer(snap_tolerance=0.10)
    a = _polyline([[0.0, 0.0], [100.0, 0.0]])
    b = _polyline([[100.04, 0.0], [200.0, 0.0]])
    h1.heal_network([a, b])
    assert h1.stats["healed_nodes"] == 1

    h2 = TopologyHealer(snap_tolerance=0.10)
    assert h2.stats["healed_nodes"] == 0


def test_topology_healer_get_report():
    """get_report deve retornar dict com summary e metrics."""
    healer = TopologyHealer()
    report = healer.get_report()
    assert "summary" in report
    assert "metrics" in report
    assert "healed_nodes" in report["metrics"]
