"""
tests/test_blocks_library.py
Testes unitários para o catálogo de blocos CAD de infraestrutura elétrica.

Cobre:
  - backend.domain.blocks: TipoBloco, TensaoBloco, BlocoDefinicao, listar_blocos,
    obter_bloco, nomes_disponiveis
  - backend.application.dxf_export: define_electrical_blocks, _draw_block_symbol
  - backend.infrastructure.routes.blocks: endpoints GET /api/v1/blocks
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Domain: blocks.py
# ---------------------------------------------------------------------------


class TestTipoBloco:
    """Enum TipoBloco."""

    def test_valores_validos(self):
        from backend.domain.blocks import TipoBloco

        assert TipoBloco.POSTE.value == "poste"
        assert TipoBloco.TRANSFORMADOR.value == "transformador"
        assert TipoBloco.MEDIDOR.value == "medidor"
        assert TipoBloco.CHAVE.value == "chave"
        assert TipoBloco.CAIXA.value == "caixa"
        assert TipoBloco.PROTECAO.value == "protecao"

    def test_todos_os_tipos(self):
        from backend.domain.blocks import TipoBloco

        nomes = {t.value for t in TipoBloco}
        assert {"poste", "transformador", "medidor", "chave", "caixa", "protecao"} == nomes


class TestTensaoBloco:
    """Enum TensaoBloco."""

    def test_valores_validos(self):
        from backend.domain.blocks import TensaoBloco

        assert TensaoBloco.BT.value == "BT"
        assert TensaoBloco.MT.value == "MT"
        assert TensaoBloco.AT.value == "AT"
        assert TensaoBloco.MULTI.value == "MULTI"


class TestBlocoDefinicao:
    """BlocoDefinicao dataclass."""

    def test_to_dict_tem_campos_obrigatorios(self):
        from backend.domain.blocks import BlocoDefinicao, TipoBloco, TensaoBloco

        b = BlocoDefinicao(
            nome="TESTE_BF",
            descricao="Bloco de teste",
            tipo=TipoBloco.POSTE,
            tensao=TensaoBloco.BT,
            layer="SISRUA_BT",
        )
        d = b.to_dict()
        assert d["nome"] == "TESTE_BF"
        assert d["descricao"] == "Bloco de teste"
        assert d["tipo"] == "poste"
        assert d["tensao"] == "BT"
        assert d["layer"] == "SISRUA_BT"
        assert d["escala"] == 1.0
        assert d["rotacao"] == 0.0
        assert isinstance(d["tags"], list)

    def test_bloco_e_frozen(self):
        from backend.domain.blocks import BlocoDefinicao, TipoBloco, TensaoBloco

        b = BlocoDefinicao(
            nome="X",
            descricao="X",
            tipo=TipoBloco.POSTE,
            tensao=TensaoBloco.BT,
            layer="0",
        )
        with pytest.raises((AttributeError, TypeError)):
            b.nome = "Y"  # type: ignore


class TestListarBlocos:
    """listar_blocos() — catálogo completo e filtros."""

    def test_retorna_lista_nao_vazia(self):
        from backend.domain.blocks import listar_blocos

        resultado = listar_blocos()
        assert len(resultado) > 0

    def test_catálogo_tem_postes(self):
        from backend.domain.blocks import listar_blocos, TipoBloco

        postes = listar_blocos(tipo=TipoBloco.POSTE)
        assert len(postes) >= 3
        nomes = {b.nome for b in postes}
        assert "POSTE_CONCRETO_BF" in nomes
        assert "POSTE_CONCRETO_TF" in nomes
        assert "POSTE_CONCRETO_MT" in nomes

    def test_catálogo_tem_transformadores(self):
        from backend.domain.blocks import listar_blocos, TipoBloco

        trafos = listar_blocos(tipo=TipoBloco.TRANSFORMADOR)
        assert len(trafos) >= 2
        nomes = {b.nome for b in trafos}
        assert "TRAFO_AEREO_MF" in nomes
        assert "TRAFO_AEREO_TF" in nomes

    def test_catálogo_tem_medidores(self):
        from backend.domain.blocks import listar_blocos, TipoBloco

        medidores = listar_blocos(tipo=TipoBloco.MEDIDOR)
        assert len(medidores) >= 1
        nomes = {b.nome for b in medidores}
        assert "MEDIDOR_CAIXA" in nomes

    def test_catálogo_tem_chaves(self):
        from backend.domain.blocks import listar_blocos, TipoBloco

        chaves = listar_blocos(tipo=TipoBloco.CHAVE)
        assert len(chaves) >= 2

    def test_catálogo_tem_caixas(self):
        from backend.domain.blocks import listar_blocos, TipoBloco

        caixas = listar_blocos(tipo=TipoBloco.CAIXA)
        assert len(caixas) >= 1

    def test_catálogo_tem_protecao(self):
        from backend.domain.blocks import listar_blocos, TipoBloco

        protecao = listar_blocos(tipo=TipoBloco.PROTECAO)
        assert len(protecao) >= 1
        nomes = {b.nome for b in protecao}
        assert "PARA_RAIOS_MT" in nomes

    def test_filtro_por_tensao_MT(self):
        from backend.domain.blocks import listar_blocos, TensaoBloco

        mt = listar_blocos(tensao=TensaoBloco.MT)
        assert all(b.tensao == TensaoBloco.MT for b in mt)
        assert len(mt) > 0

    def test_filtro_por_tensao_BT(self):
        from backend.domain.blocks import listar_blocos, TensaoBloco

        bt = listar_blocos(tensao=TensaoBloco.BT)
        assert all(b.tensao == TensaoBloco.BT for b in bt)
        assert len(bt) > 0

    def test_filtro_combinado_tipo_e_tensao(self):
        from backend.domain.blocks import listar_blocos, TipoBloco, TensaoBloco

        resultado = listar_blocos(tipo=TipoBloco.POSTE, tensao=TensaoBloco.BT)
        for b in resultado:
            assert b.tipo == TipoBloco.POSTE
            assert b.tensao == TensaoBloco.BT

    def test_filtro_sem_resultado_retorna_lista_vazia(self):
        from backend.domain.blocks import listar_blocos, TipoBloco, TensaoBloco

        resultado = listar_blocos(tipo=TipoBloco.MEDIDOR, tensao=TensaoBloco.AT)
        assert resultado == []

    def test_sem_filtro_retorna_todos_os_blocos(self):
        from backend.domain.blocks import listar_blocos, nomes_disponiveis

        todos = listar_blocos()
        nomes = nomes_disponiveis()
        assert len(todos) == len(nomes)


class TestObterBloco:
    """obter_bloco() — lookup por nome."""

    def test_retorna_bloco_existente(self):
        from backend.domain.blocks import obter_bloco

        b = obter_bloco("POSTE_CONCRETO_BF")
        assert b is not None
        assert b.nome == "POSTE_CONCRETO_BF"

    def test_retorna_none_para_nome_inexistente(self):
        from backend.domain.blocks import obter_bloco

        assert obter_bloco("BLOCO_INEXISTENTE") is None

    def test_lookup_case_sensitive(self):
        from backend.domain.blocks import obter_bloco

        # O índice é case-sensitive; nome em minúsculas não deve ser encontrado
        assert obter_bloco("poste_concreto_bf") is None

    def test_todos_os_nomes_retornam_bloco(self):
        from backend.domain.blocks import nomes_disponiveis, obter_bloco

        for nome in nomes_disponiveis():
            b = obter_bloco(nome)
            assert b is not None, f"Bloco '{nome}' não encontrado"
            assert b.nome == nome


class TestNomesDisponiveis:
    """nomes_disponiveis() — lista de nomes."""

    def test_retorna_lista_nao_vazia(self):
        from backend.domain.blocks import nomes_disponiveis

        nomes = nomes_disponiveis()
        assert isinstance(nomes, list)
        assert len(nomes) > 0

    def test_nomes_sao_strings(self):
        from backend.domain.blocks import nomes_disponiveis

        nomes = nomes_disponiveis()
        assert all(isinstance(n, str) for n in nomes)

    def test_nomes_sao_unicos(self):
        from backend.domain.blocks import nomes_disponiveis

        nomes = nomes_disponiveis()
        assert len(nomes) == len(set(nomes))


# ---------------------------------------------------------------------------
# DXF: define_electrical_blocks
# ---------------------------------------------------------------------------


class TestDefineElectricalBlocks:
    """define_electrical_blocks() — cria definições de bloco no DXF."""

    @pytest.fixture()
    def doc(self):
        import ezdxf

        return ezdxf.new(dxfversion="R2010")

    def test_retorna_contagem_positiva(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        count = define_electrical_blocks(doc)
        assert count > 0

    def test_blocos_existem_no_documento(self, doc):
        from backend.application.dxf_export import define_electrical_blocks
        from backend.domain.blocks import nomes_disponiveis

        define_electrical_blocks(doc)
        nomes = nomes_disponiveis()
        for nome in nomes:
            assert nome in doc.blocks, f"Bloco '{nome}' não definido no DXF"

    def test_idempotente_segunda_chamada_nao_recria(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        count1 = define_electrical_blocks(doc)
        count2 = define_electrical_blocks(doc)
        # Segunda chamada deve retornar 0 (blocos já existem)
        assert count1 > 0
        assert count2 == 0

    def test_appid_registrado(self, doc):
        from backend.application.dxf_export import define_electrical_blocks, APPID_SISRUA

        define_electrical_blocks(doc)
        assert APPID_SISRUA in doc.appids

    def test_poste_concreto_bf_tem_entidades(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        define_electrical_blocks(doc)
        blk = doc.blocks["POSTE_CONCRETO_BF"]
        entidades = [e for e in blk if e.dxftype() not in ("BLOCK", "ENDBLK")]
        assert len(entidades) > 0

    def test_trafo_aereo_tf_tem_entidades(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        define_electrical_blocks(doc)
        blk = doc.blocks["TRAFO_AEREO_TF"]
        entidades = [e for e in blk if e.dxftype() not in ("BLOCK", "ENDBLK")]
        assert len(entidades) > 0

    def test_aterramento_tem_linhas(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        define_electrical_blocks(doc)
        blk = doc.blocks["ATERRAMENTO"]
        linhas = [e for e in blk if e.dxftype() == "LINE"]
        assert len(linhas) >= 3  # haste + 3 linhas horizontais

    def test_para_raios_tem_polilinhas(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        define_electrical_blocks(doc)
        blk = doc.blocks["PARA_RAIOS_MT"]
        plines = [e for e in blk if e.dxftype() == "LWPOLYLINE"]
        assert len(plines) >= 1

    def test_medidor_caixa_tem_polilinhas(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        define_electrical_blocks(doc)
        blk = doc.blocks["MEDIDOR_CAIXA"]
        plines = [e for e in blk if e.dxftype() == "LWPOLYLINE"]
        assert len(plines) >= 1

    def test_chave_faca_tem_polilinhas_e_linhas(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        define_electrical_blocks(doc)
        blk = doc.blocks["CHAVE_FACA_MT"]
        entidades = [e for e in blk if e.dxftype() not in ("BLOCK", "ENDBLK")]
        assert len(entidades) >= 2  # losango + hastes

    def test_caixa_passagem_tem_diagonais(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        define_electrical_blocks(doc)
        blk = doc.blocks["CAIXA_PASSAGEM"]
        linhas = [e for e in blk if e.dxftype() == "LINE"]
        assert len(linhas) >= 2  # duas diagonais

    def test_religadora_tem_arco(self, doc):
        from backend.application.dxf_export import define_electrical_blocks

        define_electrical_blocks(doc)
        blk = doc.blocks["CHAVE_RELIGADORA"]
        arcos = [e for e in blk if e.dxftype() == "ARC"]
        assert len(arcos) >= 1


# ---------------------------------------------------------------------------
# API: GET /api/v1/blocks
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """TestClient autenticado com token de teste."""
    import os

    os.environ["SISRUA_AUTH_TOKEN"] = "test-token-blocks"
    import importlib
    import backend.infrastructure.api as api_mod
    importlib.reload(api_mod)

    from fastapi.testclient import TestClient

    return TestClient(api_mod.app, headers={"X-SisRua-Token": "test-token-blocks"})


class TestBlocksRoute:
    """Endpoints REST de blocos CAD."""

    def test_list_blocks_retorna_200(self, client):
        resp = client.get("/api/v1/blocks")
        assert resp.status_code == 200

    def test_list_blocks_retorna_lista_com_total(self, client):
        resp = client.get("/api/v1/blocks")
        data = resp.json()
        assert "blocos" in data
        assert "total" in data
        assert data["total"] > 0
        assert len(data["blocos"]) == data["total"]

    def test_list_blocks_filtro_por_tipo_poste(self, client):
        resp = client.get("/api/v1/blocks?tipo=poste")
        assert resp.status_code == 200
        data = resp.json()
        assert all(b["tipo"] == "poste" for b in data["blocos"])

    def test_list_blocks_filtro_por_tensao_MT(self, client):
        resp = client.get("/api/v1/blocks?tensao=MT")
        assert resp.status_code == 200
        data = resp.json()
        assert all(b["tensao"] == "MT" for b in data["blocos"])

    def test_list_blocks_filtro_tipo_invalido_retorna_422(self, client):
        resp = client.get("/api/v1/blocks?tipo=inexistente")
        assert resp.status_code == 422

    def test_list_blocks_filtro_tensao_invalida_retorna_422(self, client):
        resp = client.get("/api/v1/blocks?tensao=XX")
        assert resp.status_code == 422

    def test_get_block_names_retorna_lista(self, client):
        resp = client.get("/api/v1/blocks/names")
        assert resp.status_code == 200
        nomes = resp.json()
        assert isinstance(nomes, list)
        assert "POSTE_CONCRETO_BF" in nomes

    def test_get_block_por_nome_existente(self, client):
        resp = client.get("/api/v1/blocks/POSTE_CONCRETO_BF")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nome"] == "POSTE_CONCRETO_BF"
        assert data["tipo"] == "poste"

    def test_get_block_por_nome_case_insensitive_via_upper(self, client):
        # Endpoint faz `.upper()` no nome — aceita minúsculas
        resp = client.get("/api/v1/blocks/poste_concreto_bf")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nome"] == "POSTE_CONCRETO_BF"

    def test_get_block_nome_inexistente_retorna_404(self, client):
        resp = client.get("/api/v1/blocks/BLOCO_INEXISTENTE")
        assert resp.status_code == 404

    def test_list_blocks_sem_autenticacao_retorna_401_ou_403(self, client):
        import os
        from fastapi.testclient import TestClient
        import backend.infrastructure.api as api_mod

        c = TestClient(api_mod.app)  # sem headers de auth
        resp = c.get("/api/v1/blocks")
        assert resp.status_code in (401, 403)

    def test_cada_bloco_tem_campos_obrigatorios(self, client):
        resp = client.get("/api/v1/blocks")
        blocos = resp.json()["blocos"]
        campos = {"nome", "descricao", "tipo", "tensao", "layer", "escala"}
        for b in blocos:
            assert campos.issubset(b.keys()), f"Campos ausentes em {b.get('nome')}"
