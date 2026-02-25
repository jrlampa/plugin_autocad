"""
tests/test_prodist.py
Testes de conformidade ANEEL/PRODIST para o módulo gis_core/prodist.py.

Normas cobertas:
  - PRODIST Módulo 1 (ANEEL REN 956/2021) — identificação do levantamento
  - PRODIST Módulo 3 §3.4 — faixas de segurança por classe de tensão
  - NR-10:2016 Tabela 1 — distâncias mínimas de segurança

Coordenadas de referência (conforme MEMORY.MD):
  REF_2 — Projeto: lat -22.15018°, lon -42.92185°  →  E≈714316, N≈7549084 (UTM 23S)
"""
from __future__ import annotations

import os
import pytest
from pathlib import Path

from backend.domain.prodist import (
    TensaoClasse,
    ProdistMetadata,
    buffer_de_seguranca_m,
    faixa_servidao_m,
    camada_aneel,
    camada_buffer_aneel,
    build_prodist_metadata,
    BUFFER_SEGURANCA_M,
    FAIXA_SERVIDAO_M,
    TOAST_NORMA_OVERRIDE,
    TOAST_NORMA_ABNT_RESTAURADA,
)


# ---------------------------------------------------------------------------
# Constantes de referência (PRODIST Módulo 3 §3.4 / NR-10:2016 Tabela 1)
# ---------------------------------------------------------------------------

class TestBufferSeguranca:
    """Testa distâncias mínimas de segurança conforme NR-10:2016 Tabela 1."""

    def test_bt_buffer_1m(self):
        """BT (≤ 1 kV): buffer mínimo de 1,0 m — NR-10:2016 Tabela 1."""
        assert buffer_de_seguranca_m(TensaoClasse.BT) == 1.0

    def test_mt_buffer_3m(self):
        """MT (1–36,2 kV): buffer mínimo de 3,0 m — NR-10:2016 Tabela 1."""
        assert buffer_de_seguranca_m(TensaoClasse.MT) == 3.0

    def test_at_buffer_10m(self):
        """AT (> 36,2 kV): buffer mínimo de 10,0 m — NR-10:2016 Tabela 1."""
        assert buffer_de_seguranca_m(TensaoClasse.AT) == 10.0

    def test_all_classes_have_buffer(self):
        """Todas as classes de tensão têm buffer definido."""
        for classe in TensaoClasse:
            assert buffer_de_seguranca_m(classe) > 0.0

    def test_at_buffer_maior_que_mt(self):
        """Buffer AT deve ser maior que MT (relação hierárquica de tensão)."""
        assert buffer_de_seguranca_m(TensaoClasse.AT) > buffer_de_seguranca_m(TensaoClasse.MT)

    def test_mt_buffer_maior_que_bt(self):
        """Buffer MT deve ser maior que BT."""
        assert buffer_de_seguranca_m(TensaoClasse.MT) > buffer_de_seguranca_m(TensaoClasse.BT)


class TestFaixaServidao:
    """Testa faixas de servidão conforme Resolução ANEEL 156/1997."""

    def test_bt_servidao_zero(self):
        """BT não tem faixa de servidão formal em redes urbanas."""
        assert faixa_servidao_m(TensaoClasse.BT) == 0.0

    def test_mt_servidao_5m(self):
        """MT: faixa de servidão de 5,0 m de cada lado."""
        assert faixa_servidao_m(TensaoClasse.MT) == 5.0

    def test_at_servidao_20m(self):
        """AT: faixa de servidão de 20,0 m de cada lado."""
        assert faixa_servidao_m(TensaoClasse.AT) == 20.0


class TestCamadas:
    """Testa nomenclatura de camadas DXF conforme convenção sisRUA/ANEEL."""

    def test_camada_bt(self):
        assert camada_aneel(TensaoClasse.BT) == "SISRUA_ANEEL_BT"

    def test_camada_mt(self):
        assert camada_aneel(TensaoClasse.MT) == "SISRUA_ANEEL_MT"

    def test_camada_at(self):
        assert camada_aneel(TensaoClasse.AT) == "SISRUA_ANEEL_AT"

    def test_camada_max_31_chars(self):
        """Compatibilidade DXF R14+: nome de camada ≤ 31 caracteres."""
        for classe in TensaoClasse:
            assert len(camada_aneel(classe)) <= 31

    def test_buffer_camada_bt(self):
        assert camada_buffer_aneel(TensaoClasse.BT) == "SISRUA_ANEEL_BUFFER_BT"

    def test_buffer_camada_mt(self):
        assert camada_buffer_aneel(TensaoClasse.MT) == "SISRUA_ANEEL_BUFFER_MT"

    def test_buffer_camada_at(self):
        assert camada_buffer_aneel(TensaoClasse.AT) == "SISRUA_ANEEL_BUFFER_AT"

    def test_buffer_camada_max_31_chars(self):
        """Compatibilidade DXF R14+: nome de camada de buffer ≤ 31 caracteres."""
        for classe in TensaoClasse:
            assert len(camada_buffer_aneel(classe)) <= 31


class TestProdistMetadata:
    """Testa o dataclass ProdistMetadata e seus métodos."""

    def test_defaults(self):
        meta = ProdistMetadata()
        assert meta.classe_tensao == TensaoClasse.MT
        assert meta.concessionaria == "Não informada"
        assert meta.norma_ativa == "ANEEL/PRODIST"

    def test_buffer_delegado(self):
        """ProdistMetadata.buffer_m() deve delegar para buffer_de_seguranca_m."""
        meta = ProdistMetadata(classe_tensao=TensaoClasse.AT)
        assert meta.buffer_m() == 10.0

    def test_camada_rede(self):
        meta = ProdistMetadata(classe_tensao=TensaoClasse.MT)
        assert meta.camada_rede() == "SISRUA_ANEEL_MT"

    def test_camada_buffer(self):
        meta = ProdistMetadata(classe_tensao=TensaoClasse.BT)
        assert meta.camada_buffer() == "SISRUA_ANEEL_BUFFER_BT"

    def test_dxf_header_vars_keys(self):
        """Variáveis de cabeçalho DXF devem incluir norma e concessionária."""
        meta = ProdistMetadata(concessionaria="Light S.A.")
        vars_ = meta.to_dxf_header_vars()
        all_values = " ".join(vars_.values())
        assert "ANEEL/PRODIST" in all_values
        assert "Light S.A." in all_values

    def test_dxf_header_vars_buffer(self):
        """Variáveis DXF devem incluir o buffer de segurança."""
        meta = ProdistMetadata(classe_tensao=TensaoClasse.MT)
        vars_ = meta.to_dxf_header_vars()
        assert "3.0 m" in " ".join(vars_.values())

    def test_comment_lines_abnt_override_note(self):
        """Linhas de comentário devem informar que ABNT foi substituída."""
        meta = ProdistMetadata(concessionaria="Enel SP")
        lines = meta.to_comment_lines()
        full = " ".join(lines)
        assert "ABNT" in full
        assert "concessionária" in full.lower() or "Enel SP" in full

    def test_fingerprint_contains_classe(self):
        meta = ProdistMetadata(classe_tensao=TensaoClasse.AT, concessionaria="CEMIG")
        fp = meta.to_fingerprint()
        assert "PRODIST" in fp
        assert "AT" in fp
        assert "CEMIG" in fp

    def test_fingerprint_pipe_sanitized(self):
        """Concessionária com pipe não deve quebrar o fingerprint."""
        meta = ProdistMetadata(concessionaria="Test|Conc")
        fp = meta.to_fingerprint()
        # Pipe sanitizado para '-' na concessionária
        assert "Test-Conc" in fp

    def test_frozen(self):
        """ProdistMetadata deve ser imutável (frozen dataclass)."""
        meta = ProdistMetadata()
        with pytest.raises((AttributeError, TypeError)):
            meta.concessionaria = "changed"  # type: ignore[misc]


class TestBuildProdistMetadata:
    """Testa a função factory build_prodist_metadata."""

    def test_defaults(self):
        meta = build_prodist_metadata()
        assert meta.concessionaria == "Não informada"
        assert meta.classe_tensao == TensaoClasse.MT

    def test_custom_concessionaria(self):
        meta = build_prodist_metadata(concessionaria="Light S.A.", classe_tensao=TensaoClasse.AT)
        assert meta.concessionaria == "Light S.A."
        assert meta.classe_tensao == TensaoClasse.AT
        assert meta.buffer_m() == 10.0

    def test_numero_processo(self):
        meta = build_prodist_metadata(numero_processo="48500.004321/2024-01")
        assert meta.numero_processo == "48500.004321/2024-01"


class TestToastMessages:
    """Testa constantes de mensagem toast para override de norma."""

    def test_override_toast_not_empty(self):
        assert len(TOAST_NORMA_OVERRIDE) > 0

    def test_override_toast_mentions_abnt_and_prodist(self):
        assert "ABNT" in TOAST_NORMA_OVERRIDE
        assert "PRODIST" in TOAST_NORMA_OVERRIDE

    def test_restore_toast_mentions_abnt(self):
        assert "ABNT" in TOAST_NORMA_ABNT_RESTAURADA


class TestDxfExportWithProdist:
    """
    Testa integração PRODIST com a exportação DXF.
    Coordenadas de referência REF_2 (UTM 23S SIRGAS 2000 / EPSG:31983):
      E≈714316, N≈7549084 (lat -22.15018°, lon -42.92185°)
    """

    REF_E = 714316.0
    REF_N = 7549084.0

    def _make_mt_line(self):
        from backend.domain.dto import CadFeature
        return CadFeature(
            feature_type="Polyline",
            layer="SISRUA_ANEEL_MT",
            name="Rede MT — 13,8 kV",
            coords_xy=[
                [self.REF_E, self.REF_N],
                [self.REF_E + 500.0, self.REF_N],  # 500 m conforme MEMORY.MD
            ],
            elevation=850.0,
        )

    def test_dxf_with_prodist_metadata_generated(self, tmp_path):
        """DXF gerado com ProdistMetadata deve conter FINGERPRINTGUID PRODIST."""
        import ezdxf
        from backend.application.dxf_export import export_features_to_dxf
        from backend.domain.prodist import build_prodist_metadata, TensaoClasse

        feat = self._make_mt_line()
        prodist_meta = build_prodist_metadata(
            concessionaria="Light S.A.",
            classe_tensao=TensaoClasse.MT,
        )
        out_path = tmp_path / "test_prodist.dxf"
        result = export_features_to_dxf(
            [feat],
            output_path=out_path,
            prodist_metadata=prodist_meta,
        )
        assert result.exists()
        doc = ezdxf.readfile(str(result))
        guid = doc.header.get("$FINGERPRINTGUID", "")
        assert "PRODIST" in guid
        assert "MT" in guid

    def test_dxf_without_prodist_uses_abnt(self, tmp_path):
        """DXF sem ProdistMetadata deve usar ABNT no FINGERPRINTGUID."""
        import ezdxf
        from backend.application.dxf_export import export_features_to_dxf

        feat = self._make_mt_line()
        out_path = tmp_path / "test_abnt.dxf"
        result = export_features_to_dxf([feat], output_path=out_path)
        assert result.exists()
        doc = ezdxf.readfile(str(result))
        guid = doc.header.get("$FINGERPRINTGUID", "")
        assert "sisrua" in guid
        assert "PRODIST" not in guid

    def test_dxf_prodist_has_correct_layer(self, tmp_path):
        """Feature com camada ANEEL deve ser preservada no DXF."""
        import ezdxf
        from backend.application.dxf_export import export_features_to_dxf
        from backend.domain.prodist import build_prodist_metadata, TensaoClasse

        feat = self._make_mt_line()
        prodist_meta = build_prodist_metadata(classe_tensao=TensaoClasse.MT)
        out_path = tmp_path / "test_layer.dxf"
        export_features_to_dxf([feat], output_path=out_path, prodist_metadata=prodist_meta)
        doc = ezdxf.readfile(str(out_path))
        layer_names = {layer.dxf.name for layer in doc.layers}
        assert "SISRUA_ANEEL_MT" in layer_names


class TestProdistApiEndpoints:
    """
    Testa os endpoints REST ANEEL/PRODIST.
    GET  /api/v1/normas/ativas
    POST /api/v1/normas/config
    """

    @pytest.fixture
    def client_v2(self):
        """Fixture com estado _norma_config resetado para ABNT."""
        os.environ["SISRUA_TESTING"] = "true"
        os.environ["SISRUA_AUTH_TOKEN"] = "test-token-prodist2"
        from fastapi.testclient import TestClient
        import backend.api as _api
        # Reseta o dict de norma diretamente via import do módulo enterprise
        from backend.routes import enterprise as ent
        ent._norma_config.update({
            "ativa": "ABNT",
            "concessionaria": "",
            "classe_tensao": "MT",
            "numero_processo": "",
            "toast": None,
        })
        return TestClient(_api.app)

    def test_get_norma_ativa_default_abnt(self, client_v2):
        resp = client_v2.get(
            "/api/v1/normas/ativas",
            headers={"X-SisRua-Token": "test-token-prodist2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ativa"] == "ABNT"

    def test_post_config_ativa_prodist(self, client_v2):
        resp = client_v2.post(
            "/api/v1/normas/config",
            json={
                "ativa": True,
                "concessionaria": "Light S.A.",
                "classe_tensao": "MT",
                "numero_processo": "",
            },
            headers={"X-SisRua-Token": "test-token-prodist2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma_ativa"] == "PRODIST"
        assert data["abnt_substituida"] is True
        assert data["buffer_seguranca_m"] == 3.0
        assert "toast" in data
        assert "ABNT" in data["toast"]

    def test_post_config_desativa_prodist(self, client_v2):
        # Ativa primeiro
        client_v2.post(
            "/api/v1/normas/config",
            json={"ativa": True, "concessionaria": "CEMIG", "classe_tensao": "AT", "numero_processo": ""},
            headers={"X-SisRua-Token": "test-token-prodist2"},
        )
        # Desativa
        resp = client_v2.post(
            "/api/v1/normas/config",
            json={"ativa": False, "concessionaria": "", "classe_tensao": "MT", "numero_processo": ""},
            headers={"X-SisRua-Token": "test-token-prodist2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["norma_ativa"] == "ABNT"
        assert data["abnt_substituida"] is False

    def test_post_config_classe_tensao_at(self, client_v2):
        """AT deve retornar buffer de 10,0 m."""
        resp = client_v2.post(
            "/api/v1/normas/config",
            json={"ativa": True, "concessionaria": "Enel SP", "classe_tensao": "AT", "numero_processo": ""},
            headers={"X-SisRua-Token": "test-token-prodist2"},
        )
        assert resp.status_code == 200
        assert resp.json()["buffer_seguranca_m"] == 10.0

    def test_post_config_invalid_classe(self, client_v2):
        """Classe de tensão inválida deve retornar 422."""
        resp = client_v2.post(
            "/api/v1/normas/config",
            json={"ativa": True, "concessionaria": "X", "classe_tensao": "INVALID", "numero_processo": ""},
            headers={"X-SisRua-Token": "test-token-prodist2"},
        )
        assert resp.status_code == 422

    def test_get_norma_requires_auth(self, client_v2):
        resp = client_v2.get("/api/v1/normas/ativas")
        assert resp.status_code == 401

    def test_post_config_requires_auth(self, client_v2):
        resp = client_v2.post(
            "/api/v1/normas/config",
            json={"ativa": True, "concessionaria": "X", "classe_tensao": "BT", "numero_processo": ""},
        )
        assert resp.status_code == 401

    def test_get_norma_prodist_state_returns_toast(self, client_v2):
        """Quando PRODIST ativo, GET /normas/ativas deve retornar toast."""
        client_v2.post(
            "/api/v1/normas/config",
            json={"ativa": True, "concessionaria": "AES", "classe_tensao": "BT", "numero_processo": ""},
            headers={"X-SisRua-Token": "test-token-prodist2"},
        )
        resp = client_v2.get(
            "/api/v1/normas/ativas",
            headers={"X-SisRua-Token": "test-token-prodist2"},
        )
        data = resp.json()
        assert data["ativa"] == "PRODIST"
        assert data["toast"] is not None
