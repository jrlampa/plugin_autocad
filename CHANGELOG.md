# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-02-25

### Added
- **BIM-LITE XData completo** (`_build_bim_xdata`): cada entidade CAD agora armazena em XDATA todos os campos semânticos do esquema BIM-LITE — `sisrua:class` (street/block/point/polyline), `sisrua:highway`, `sisrua:name`, `sisrua:width_m`, `sisrua:elevation`, `sisrua:slope`, `sisrua:layer`. Implementa o requisito "Half-way BIM: uma rua sabe que é uma rua".
- **Layer topográfica `SISRUA_TOPO`** (`add_contours_to_dxf`): função headless que adiciona curvas de nível SRTM ao DXF com cor ciano (ACI 4) e XDATA BIM-LITE (`sisrua:class=contour`, `sisrua:elevation`, `sisrua:interval`).
- **`ExportService.export_project_with_topo`**: exporta projeto + curvas de nível SRTM num único arquivo DXF. Abre o DXF base, injeta a layer SISRUA_TOPO e salva. Quando `contour_lines` é vazio/None, retorna o DXF standard sem modificação.
- **`test_bim_lite_xdata.py`** (40 testes): cobertura completa do esquema BIM-LITE — unit tests de `_build_bim_xdata` (13), integração com ezdxf (11), `add_contours_to_dxf` (11), `export_project_with_topo` com DB real (5).

### Fixed
- **`_build_bim_xdata`**: lógica de classificação de entidade refatorada de ternário aninhado para if/elif/else explícitos (legibilidade).
- **`ROADMAP.md`**: marcado como concluído os itens v0.4.0 (DXF headless, SISRUA_TOPO) e v0.5.0 (XData BIM-LITE); métricas atualizadas (935 testes backend).

## [0.3.1] - 2026-02-25

### Added
- **Testes E2E de integração** (`tests/test_e2e_ref_coordinates.py`, 34 testes): pipeline completo com coordenadas de referência REF_1 e REF_2 (100 m, 500 m, 1 km). Valida projeção CRS real, coordenadas locais, princípio 2.5D, exportação DXF headless e config auto-token.
- **`TestCrsProjection`** (6 testes): `sirgas2000_utm_epsg`, `latlon_to_utm`, roundtrip UTM↔WGS84, `transform_coords`.
- **`TestOsmPipelineRef2`** (12 testes): `prepare_osm_compute` mocked HTTP, real geometry/topology/DXF. Valida `sys_sisrua_origin` (UTM absoluto), coords locais em metros, layers SISRUA_*.
- **`TestDxfHeadlessExport`** (7 testes): DXF R2010, layers, entidades, `$INSUNITS=6` (metros), princípio 2.5D.
- **`TestSettingsConfig`** (5 testes): `extra_cors_origins`, auto-geração de token + injeção `os.environ` (linha 20 de `config.py`).

### Fixed
- **`.gitignore`**: adicionados padrões `**/build_log.txt`, `**/test_err.txt`, `**/secret_scan_report.txt`.
- **Limpeza do repositório**: 22 arquivos de artefatos (CI logs, test outputs, screenshots, DB de teste) removidos do tracking git via `git rm --cached`.

## [0.3.0] - 2026-02-25

### Added
- **Modularização C# `BackendManager`**: dividido em 3 arquivos `partial class` (BackendManager.cs 309L, BackendProcess.cs 177L, BackendPersistence.cs 100L) — todos abaixo do limite de 500 linhas.
- **`src/frontend/.dockerignore`**: excluí `node_modules`, `dist`, `.env*`, `coverage`, etc. do contexto de build Docker.
- **Headers de segurança nginx**: `X-Frame-Options SAMEORIGIN`, `X-Content-Type-Options nosniff`, `X-XSS-Protection`, `Referrer-Policy`, `Content-Security-Policy` para o frontend containerizado.
- **Timeouts de proxy nginx**: `proxy_read_timeout 120s` e `proxy_connect_timeout 10s` para requests longos de processamento OSM/IBGE/INEA.

### Fixed
- **`docker-compose.yml`**: build context do backend corrigido de `.` (raiz) para `./src/backend` (contexto correto do Dockerfile); volume de dev corrigido de `./src/backend:/app/backend` para `./src/backend:/app`.
- **`docker-compose.yml`**: `SISRUA_AUTH_TOKEN` padrão alterado de `test-token` hardcoded para string vazia (backend auto-gera UUID na inicialização).
- **`docker-compose.yml`**: Redis atualizado de `redis:alpine` para `redis:7-alpine`; adicionados volumes nomeados para persistência de logs, cache e dados Redis.
- **`BackendPersistence.cs`**: `TcpListener` em `ChooseFreePort()` encapsulado em `try/finally` para garantir `Stop()` mesmo em exceção.
- **`BackendProcess.cs`**: variável renomeada de `candidate` para `pythonExePath` para clareza.

## [0.2.0] - 2026-02-25

### Added

- **Arquitetura DDD** completa: módulos reorganizados em `domain/`, `application/`, `infrastructure/`, `shared/` com camada de compatibilidade retroativa via `sys.modules`.
- **Rotas IBGE e INEA**: `/api/v1/prepare/ibge` (malha municipal) e `/api/v1/prepare/inea` (feições ambientais WFS).
- **`PersistenceBuffer`** assíncrono em `backend/shared/buffer.py` — flush por batch ou intervalo de tempo.
- **Middleware de segurança ampliado**: `Content-Security-Policy`, `Referrer-Policy`, `X-Request-ID` (echo/geração automática), `X-Frame-Options: SAMEORIGIN`.
- **Sistema de migrations** (`backend/shared/migrations.py`) com rastreamento de versão, idempotência e rollback seguro.
- **Conversão KML/KMZ** no frontend (`api.convertKml`) com validação rigorosa de FeatureCollection.
- **Assistente IA** (`AiAssistant`) integrado ao frontend com suporte a contexto RAG.
- **`_DynamicToken`** em `api.py` — resolve `SISRUA_AUTH_TOKEN` de `os.environ` em tempo real para isolamento entre testes.
- **Fixture `_restore_auth_token`** (autouse) em `conftest.py` para isolamento de env vars entre testes.
- `SHUTDOWN_EVENT.clear()` no startup do lifespan e em `create_prepare_job` para evitar cancelamento prematuro de jobs em sequências de teste.

### Fixed

- `_sanitize_tags` em `osm_parser.py` preserva listas multi-valor (ex: `highway: [residential, secondary]`).
- `AiService.__init__` lê `GROQ_API_KEY` de `os.environ` diretamente (suporta `monkeypatch`).
- `_get_master_token()` em `auth.py` lê de `os.environ` dinamicamente.
- Botão de envio do `AiAssistant` rótulo corrigido para "Enviar" (compatível com testes).
- Validação de `FeatureCollection` reforçada: exige `features.length > 0`.

### Changed

- CI/CD: Python 3.10 → **3.12**; `SISRUA_TESTING=true` e `SISRUA_AUTH_TOKEN` adicionados ao ambiente CI.
- `requirements-ci.txt`: adicionados `fastkml`, `pydantic-settings`, `httpx`, `anyio`.
- Cobertura de testes backend: 92.44% → **95.60%** (776 testes).
- Cobertura de testes frontend: 99.35% statements (362 testes).
- `backend/shared/migrations.py`: 18% → **100%** de cobertura.
- `backend/models.py`: 64% → **98%** de cobertura.
- `backend/shared/logger.py`: 74% → **96%** de cobertura.

## [0.1.0] - 2026-02-21

### Added

- Estrutura inicial do projeto sisRUA: plugin AutoCAD (C#), backend Python (FastAPI) e frontend React/Vite.
- Pipeline GIS completo: Campo → OSM/GeoJSON → SIRGAS 2000 UTM → CAD (AutoCAD/Civil 3D).
- Projeção automática de zona UTM via pyproj (EPSG:4326 → SIRGAS 2000 UTM zona 23).
- Geração de DXF headless (2.5D) via ezdxf com elevação armazenada em XDATA.
- Integração com Overpass API (OpenStreetMap) para busca de vias e infraestrutura urbana.
- Elevação SRTM offline-first via OpenTopography + cache local de tiles GeoTIFF.
- Importação de GeoJSON via drag-and-drop com conversão automática de CRS.
- Catálogo de blocos CAD (DWG) para ativos urbanos (postes, hidrantes, bueiros, etc.).
- Persistência de projetos em SQLite local com optimistic locking.
- Limpeza e simplificação de geometria (deduplicação, Douglas-Peucker).
- API REST FastAPI com autenticação por token (X-SisRua-Token), rate limiting e audit log criptográfico.
- Interface WebView2 (React/Vite, pt-BR) integrada à palette do AutoCAD.
- Assistente IA via Groq free tier com RAG contextual.
- Docker Compose com healthchecks de produção (backend, Redis, frontend).
- Conformidade ISO 27001: session tokens, origin validation, rate limiting, audit log HMAC-SHA256.
- Conformidade LGPD: housekeeper service com limpeza automática de dados temporários.
- SDKs gerados: Python (`sisrua-sdk`) e TypeScript (OpenAPI).
- 101 testes pytest passando (unit + integração + DXF headless).
