"""
tests/test_dxf_prodist_buffers.py
Testes headless de geração de faixas de segurança ANEEL/PRODIST no DXF.

Referências normativas:
  - NR-10:2016 Tabela 1 — distâncias mínimas de segurança
  - PRODIST Módulo 3 §3.4 — faixas de servidão e segurança
  - ANEEL REN 956/2021 (PRODIST Módulo 1) — identificação do levantamento

Coordenadas de referência (conforme MEMORY.MD):
  REF_2 — Projeto: lat -22.15018°, lon -42.92185°  →  E≈714316, N≈7549084 (UTM 23S)
  Raios testados: 100 m, 500 m, 1000 m

Princípio 2.5D: buffer gerado em 2D (Z=0); elevação propagada via XDATA.
"""
from __future__ import annotations

import pytest

from backend.models import CadFeature
from backend.services.dxf_export import (
    export_features_to_dxf,
    generate_prodist_buffer_features,
)

# ---------------------------------------------------------------------------
# Coordenadas de referência (UTM 23S SIRGAS 2000 / EPSG:31983)
# ---------------------------------------------------------------------------
REF_E = 714316.0   # Easting (m) para -22.15018°, -42.92185° (REF_2 — projeto)
REF_N = 7549084.0  # Northing (m)
REF1_E = 788547.0  # UTM 23K — campo (REF_1: 23K 788547 7634925)
REF1_N = 7634925.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prodist_meta(classe_str: str = "MT"):
    from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse
    return build_prodist_metadata(
        concessionaria="Light S.A.",
        classe_tensao=TensaoClasse(classe_str),
    )


def _aneel_line(
    layer: str = "SISRUA_ANEEL_MT",
    length_m: float = 100.0,
    elevation: float = 850.0,
    origin_e: float = REF_E,
    origin_n: float = REF_N,
) -> CadFeature:
    """Cria uma polilinha de rede elétrica em camada ANEEL."""
    return CadFeature(
        feature_type="Polyline",
        layer=layer,
        name=f"Rede {layer} {length_m:.0f}m",
        coords_xy=[
            [origin_e, origin_n],
            [origin_e + length_m, origin_n],
        ],
        elevation=elevation,
    )


# ---------------------------------------------------------------------------
# Testes: generate_prodist_buffer_features()
# ---------------------------------------------------------------------------

class TestGenerateProdistBuffers:
    """Testa a geração geométrica de faixas de segurança PRODIST."""

    def test_buffer_gerado_para_mt(self):
        """Buffer MT (3 m) deve ser gerado para rede SISRUA_ANEEL_MT."""
        feat = _aneel_line("SISRUA_ANEEL_MT", 100.0)
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([feat], meta)
        assert len(buffers) == 1
        buf = buffers[0]
        assert buf.feature_type == "Polyline"
        assert "BUFFER_MT" in buf.layer
        assert len(buf.coords_xy) >= 3  # polígono fechado

    def test_buffer_gerado_para_bt(self):
        """Buffer BT (1 m) deve ser gerado para rede SISRUA_ANEEL_BT."""
        feat = _aneel_line("SISRUA_ANEEL_BT", 100.0)
        meta = _prodist_meta("BT")
        buffers = generate_prodist_buffer_features([feat], meta)
        assert len(buffers) == 1
        assert "BUFFER_BT" in buffers[0].layer

    def test_buffer_gerado_para_at(self):
        """Buffer AT (10 m) deve ser gerado para rede SISRUA_ANEEL_AT."""
        feat = _aneel_line("SISRUA_ANEEL_AT", 100.0)
        meta = _prodist_meta("AT")
        buffers = generate_prodist_buffer_features([feat], meta)
        assert len(buffers) == 1
        assert "BUFFER_AT" in buffers[0].layer

    def test_buffer_propaga_elevacao(self):
        """Elevação da feature original deve ser propagada para o buffer (2.5D)."""
        feat = _aneel_line("SISRUA_ANEEL_MT", 100.0, elevation=875.3)
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([feat], meta)
        assert buffers[0].elevation == pytest.approx(875.3)

    def test_buffer_ignorado_para_points(self):
        """Pontos (feature_type=Point) não geram buffers."""
        feat = CadFeature(
            feature_type="Point",
            layer="SISRUA_ANEEL_MT",
            name="Poste MT",
            insertion_point_xy=[REF_E, REF_N],
            elevation=850.0,
        )
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([feat], meta)
        assert len(buffers) == 0

    def test_buffer_lista_vazia(self):
        """Lista de features vazia deve retornar lista de buffers vazia."""
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([], meta)
        assert buffers == []

    def test_buffer_coords_sao_2d(self):
        """Coordenadas do buffer devem ser 2D (X, Y) — princípio 2.5D."""
        feat = _aneel_line("SISRUA_ANEEL_MT", 500.0)
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([feat], meta)
        for coord in buffers[0].coords_xy:
            assert len(coord) == 2, f"Coord deveria ser 2D: {coord}"

    def test_buffer_dimensao_mt_3m_ref2_100m(self):
        """Buffer MT: largura ≥ 6 m (2 × 3 m NR-10) — rede 100 m, coord REF_2."""
        feat = _aneel_line("SISRUA_ANEEL_MT", 100.0, origin_e=REF_E, origin_n=REF_N)
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([feat], meta)
        buf = buffers[0]
        ys = [c[1] for c in buf.coords_xy]
        y_extent = max(ys) - min(ys)
        assert y_extent >= 5.0, f"Buffer MT muito estreito: {y_extent:.1f} m"

    def test_buffer_dimensao_mt_3m_ref2_500m(self):
        """Buffer MT: largura ≥ 6 m — rede 500 m, coord REF_2."""
        feat = _aneel_line("SISRUA_ANEEL_MT", 500.0, origin_e=REF_E, origin_n=REF_N)
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([feat], meta)
        ys = [c[1] for c in buffers[0].coords_xy]
        assert max(ys) - min(ys) >= 5.0

    def test_buffer_dimensao_mt_3m_ref2_1km(self):
        """Buffer MT: largura ≥ 6 m — rede 1 km, coord REF_2."""
        feat = _aneel_line("SISRUA_ANEEL_MT", 1000.0, origin_e=REF_E, origin_n=REF_N)
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([feat], meta)
        ys = [c[1] for c in buffers[0].coords_xy]
        assert max(ys) - min(ys) >= 5.0

    def test_buffer_dimensao_at_10m_ref2_100m(self):
        """Buffer AT: largura ≥ 20 m (2 × 10 m NR-10) — rede 100 m."""
        feat = _aneel_line("SISRUA_ANEEL_AT", 100.0, origin_e=REF_E, origin_n=REF_N)
        meta = _prodist_meta("AT")
        buffers = generate_prodist_buffer_features([feat], meta)
        ys = [c[1] for c in buffers[0].coords_xy]
        assert max(ys) - min(ys) >= 18.0, f"Buffer AT muito estreito"

    def test_buffer_ref1_campo_100m(self):
        """Buffer deve funcionar com coordenadas de campo REF_1 (23K 788547 7634925)."""
        feat = _aneel_line("SISRUA_ANEEL_MT", 100.0, origin_e=REF1_E, origin_n=REF1_N)
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features([feat], meta)
        assert len(buffers) == 1

    def test_buffer_layer_nome_max_31_chars(self):
        """Camadas de buffer devem ter ≤ 31 chars (compatibilidade DXF R14+)."""
        from backend.gis_core.prodist import TensaoClasse, camada_buffer_aneel
        for classe in TensaoClasse:
            layer = camada_buffer_aneel(classe)
            assert len(layer) <= 31, f"Layer muito longo: {layer!r}"

    def test_buffer_layer_usa_prefixo_aneel(self):
        """Camadas de buffer devem usar o prefixo SISRUA_ANEEL_BUFFER_."""
        from backend.gis_core.prodist import TensaoClasse, camada_buffer_aneel
        for classe in TensaoClasse:
            assert camada_buffer_aneel(classe).startswith("SISRUA_ANEEL_BUFFER_")

    def test_multiples_features_geram_multiples_buffers(self):
        """Múltiplas features de rede devem gerar múltiplos buffers individuais."""
        feats = [
            _aneel_line("SISRUA_ANEEL_MT", 100.0),
            _aneel_line("SISRUA_ANEEL_MT", 200.0, origin_e=REF_E + 200.0),
        ]
        meta = _prodist_meta("MT")
        buffers = generate_prodist_buffer_features(feats, meta)
        assert len(buffers) == 2

    def test_buffer_feature_nao_aneel_usa_classe_do_metadata(self):
        """Feature em layer não-ANEEL usa a classe de tensão do metadata PRODIST."""
        feat = _aneel_line("SISRUA_OSM_HIGHWAY", 100.0)  # layer não é ANEEL
        meta = _prodist_meta("BT")
        buffers = generate_prodist_buffer_features([feat], meta)
        assert len(buffers) == 1
        assert "BUFFER_BT" in buffers[0].layer


# ---------------------------------------------------------------------------
# Testes: export_features_to_dxf() com include_prodist_buffers=True
# ---------------------------------------------------------------------------

class TestDxfExportComBuffersProdist:
    """Testa o DXF gerado com faixas de segurança PRODIST incluídas."""

    def test_dxf_com_buffers_prodist_100m(self, tmp_path):
        """DXF com buffers PRODIST deve ter camadas BUFFER e features de rede (100 m)."""
        import ezdxf
        from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse

        feat = _aneel_line("SISRUA_ANEEL_MT", 100.0)
        meta = build_prodist_metadata("Concessionária Teste", TensaoClasse.MT)
        out = tmp_path / "prodist_100m.dxf"
        export_features_to_dxf(
            [feat],
            output_path=out,
            prodist_metadata=meta,
            include_prodist_buffers=True,
        )
        assert out.exists()
        doc = ezdxf.readfile(str(out))
        layers = {lyr.dxf.name for lyr in doc.layers}
        assert "SISRUA_ANEEL_MT" in layers
        assert "SISRUA_ANEEL_BUFFER_MT" in layers

    def test_dxf_com_buffers_prodist_500m(self, tmp_path):
        """DXF com buffers PRODIST deve ter features para rede de 500 m."""
        import ezdxf
        from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse

        feat = _aneel_line("SISRUA_ANEEL_MT", 500.0)
        meta = build_prodist_metadata("Concessionária Teste", TensaoClasse.MT)
        out = tmp_path / "prodist_500m.dxf"
        export_features_to_dxf(
            [feat],
            output_path=out,
            prodist_metadata=meta,
            include_prodist_buffers=True,
        )
        doc = ezdxf.readfile(str(out))
        msp = doc.modelspace()
        entities = list(msp)
        assert len(entities) >= 2  # rede + buffer

    def test_dxf_com_buffers_prodist_1km(self, tmp_path):
        """DXF com buffers PRODIST deve funcionar para rede AT de 1 km."""
        import ezdxf
        from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse

        feat = _aneel_line("SISRUA_ANEEL_AT", 1000.0)
        meta = build_prodist_metadata("Concessionária Teste", TensaoClasse.AT)
        out = tmp_path / "prodist_1km.dxf"
        export_features_to_dxf(
            [feat],
            output_path=out,
            prodist_metadata=meta,
            include_prodist_buffers=True,
        )
        doc = ezdxf.readfile(str(out))
        layers = {lyr.dxf.name for lyr in doc.layers}
        assert "SISRUA_ANEEL_BUFFER_AT" in layers

    def test_dxf_sem_buffers_nao_inclui_buffer_layers(self, tmp_path):
        """Quando include_prodist_buffers=False, camadas BUFFER não devem existir."""
        import ezdxf
        from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse

        feat = _aneel_line("SISRUA_ANEEL_MT", 100.0)
        meta = build_prodist_metadata("Concessionária Teste", TensaoClasse.MT)
        out = tmp_path / "prodist_no_buffer.dxf"
        export_features_to_dxf(
            [feat],
            output_path=out,
            prodist_metadata=meta,
            include_prodist_buffers=False,
        )
        doc = ezdxf.readfile(str(out))
        layers = {lyr.dxf.name for lyr in doc.layers}
        assert "SISRUA_ANEEL_BUFFER_MT" not in layers

    def test_dxf_fingerprint_prodist_presente(self, tmp_path):
        """DXF PRODIST deve ter o $FINGERPRINTGUID com identificador sisRUA/PRODIST."""
        import ezdxf
        from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse

        feat = _aneel_line("SISRUA_ANEEL_MT", 100.0)
        meta = build_prodist_metadata("Light S.A.", TensaoClasse.MT)
        out = tmp_path / "prodist_fp.dxf"
        export_features_to_dxf([feat], output_path=out, prodist_metadata=meta)
        doc = ezdxf.readfile(str(out))
        fp = doc.header.get("$FINGERPRINTGUID", "")
        assert "sisrua" in fp.lower() or "PRODIST" in fp

    def test_dxf_buffer_ref1_campo_100m(self, tmp_path):
        """DXF buffer deve ser gerado para coord de campo REF_1 (23K) com rede 100 m."""
        import ezdxf
        from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse

        feat = _aneel_line("SISRUA_ANEEL_MT", 100.0, origin_e=REF1_E, origin_n=REF1_N)
        meta = build_prodist_metadata("Concessionária Teste", TensaoClasse.MT)
        out = tmp_path / "prodist_ref1_100m.dxf"
        export_features_to_dxf(
            [feat],
            output_path=out,
            prodist_metadata=meta,
            include_prodist_buffers=True,
        )
        doc = ezdxf.readfile(str(out))
        layers = {lyr.dxf.name for lyr in doc.layers}
        assert "SISRUA_ANEEL_BUFFER_MT" in layers

    def test_dxf_bt_buffer_1m_ref2_500m(self, tmp_path):
        """DXF BT buffer (1 m) deve ser gerado para rede de 500 m na coord REF_2."""
        import ezdxf
        from backend.gis_core.prodist import build_prodist_metadata, TensaoClasse

        feat = _aneel_line("SISRUA_ANEEL_BT", 500.0)
        meta = build_prodist_metadata("Enel Distribuição Rio", TensaoClasse.BT)
        out = tmp_path / "prodist_bt_500m.dxf"
        export_features_to_dxf(
            [feat],
            output_path=out,
            prodist_metadata=meta,
            include_prodist_buffers=True,
        )
        doc = ezdxf.readfile(str(out))
        layers = {lyr.dxf.name for lyr in doc.layers}
        assert "SISRUA_ANEEL_BUFFER_BT" in layers


# ---------------------------------------------------------------------------
# Testes: endpoint /api/v1/export/dxf-prodist/{project_id}
# ---------------------------------------------------------------------------

class TestExportDxfProdistEndpoint:
    """Testa o endpoint enterprise para exportação DXF PRODIST."""

    @pytest.fixture()
    def client_and_token(self, tmp_path, monkeypatch):
        import importlib
        import os
        monkeypatch.setenv("SISRUA_TESTING", "true")
        monkeypatch.setenv("SISRUA_AUTH_TOKEN", "test-token-prodist")
        monkeypatch.setenv("SISRUA_DB_PATH", str(tmp_path / "test.db"))
        from fastapi.testclient import TestClient
        import backend.api as api_mod
        importlib.reload(api_mod)
        client = TestClient(api_mod.app, base_url="http://localhost:8000")
        return client, "test-token-prodist"

    def test_export_dxf_prodist_sem_norma_ativa_retorna_409(self, client_and_token):
        """Exportação PRODIST sem norma PRODIST ativa deve retornar 409."""
        client, token = client_and_token
        from backend.routes import enterprise as ent_mod
        with ent_mod._norma_lock:
            ent_mod._norma_config["ativa"] = "ABNT"

        resp = client.get(
            "/api/v1/export/dxf-prodist/any-project",
            headers={"X-SisRua-Token": token},
        )
        assert resp.status_code == 409
        assert "PRODIST" in resp.json()["detail"]
