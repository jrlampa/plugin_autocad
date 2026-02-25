# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
