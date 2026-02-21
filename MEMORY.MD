# sisRUA — RAG / Memória de Trabalho

> Arquivo de memória viva do projeto. Atualizado a cada sessão de desenvolvimento.
> Usado como fonte de contexto (RAG) por todos os agentes e pelo AI assistente embutido.

---

## 🧭 Visão Geral

**sisRUA** é um plugin AutoCAD enterprise de nível de produção para processamento urbano GIS.  
Pipeline técnico: Campo → GIS → CAD, offline-first, custo zero.

- **Repositório**: `jrlampa/plugin_autocad`
- **Branch principal de desenvolvimento**: `dev`
- **Versão atual**: `1.1.0`
- **Stack**: Python (FastAPI backend) + React/Vite (frontend WebView2) + C# (plugin AutoCAD)

---

## 🏗️ Arquitetura

```
plugin_autocad/
├── src/
│   ├── backend/          # Python FastAPI — Smart Backend
│   │   ├── backend/
│   │   │   ├── api.py            # App FastAPI + middleware + startup
│   │   │   ├── routes/           # Roteadores por domínio (SoC)
│   │   │   │   ├── health.py     # /health, /auth
│   │   │   │   ├── jobs.py       # /jobs
│   │   │   │   ├── tools.py      # /tools/elevation
│   │   │   │   ├── ai.py         # /ai/chat
│   │   │   │   ├── prepare.py    # /prepare/osm, /prepare/geojson
│   │   │   │   ├── enterprise.py # /export, /sync, /management
│   │   │   │   └── webhooks.py   # /webhooks, /events
│   │   │   ├── gis_core/         # Núcleo GIS
│   │   │   │   ├── osm.py        # Fetch + parse Overpass API
│   │   │   │   ├── crs.py        # Conversão EPSG:4326 → SIRGAS 2000 UTM
│   │   │   │   ├── geometry.py   # Offset local, snap, bounding box
│   │   │   │   └── topology.py   # Healing de rede, assinatura de integridade
│   │   │   ├── services/         # Serviços de negócio
│   │   │   │   ├── elevation.py  # SRTM via OpenTopography (offline-first)
│   │   │   │   ├── geojson.py    # Preparo de GeoJSON para CAD
│   │   │   │   ├── projects.py   # CRUD projetos SQLite (otimistic locking)
│   │   │   │   ├── jobs.py       # Job queue assíncrono
│   │   │   │   ├── ai.py         # Groq LLM (gratuito) + RAG
│   │   │   │   ├── export_service.py  # GeoJSON + GeoPackage export
│   │   │   │   ├── dxf_export.py # Geração DXF headless (ezdxf, 2.5D)
│   │   │   │   ├── health.py     # Deep health check
│   │   │   │   ├── cache.py      # In-memory cache
│   │   │   │   ├── webhooks.py   # Event broadcasting
│   │   │   │   └── housekeeper.py     # Limpeza de dados (LGPD)
│   │   │   └── core/             # Infraestrutura transversal
│   │   │       ├── logger.py     # structlog + trace ID
│   │   │       ├── audit.py      # Audit log
│   │   │       ├── circuit_breaker.py
│   │   │       ├── retry.py
│   │   │       ├── rate_limit.py
│   │   │       ├── database.py   # SQLite connection
│   │   │       ├── migrations.py
│   │   │       ├── bus.py        # Event bus interno
│   │   │       ├── ipc.py        # Named pipe (Windows) para handshake C#
│   │   │       └── lifecycle.py  # Shutdown event + job registry
│   │   └── tests/                # Pytest unit tests
│   ├── frontend/         # React/Vite — Thin Frontend (pt-BR)
│   │   └── src/
│   │       ├── components/       # UI components
│   │       ├── hooks/            # Custom React hooks
│   │       ├── services/         # SDK + Resilience service
│   │       └── api.js            # API client
│   ├── plugin/           # C# AutoCAD plugin
│   │   ├── SisRuaPlugin.cs       # Entry point
│   │   ├── SisRuaCommands.cs     # Comandos AutoCAD (partial class, ~300 linhas)
│   │   ├── Commands/             # Módulos do partial class SisRuaCommands
│   │   │   ├── SisRuaCommandDtos.cs    # DTOs HTTP privados
│   │   │   ├── SisRuaCommandConfig.cs  # Mapeamento layer/bloco + config JSON
│   │   │   ├── SisRuaCadUtils.cs       # Utilitários CAD de baixo nível
│   │   │   └── SisRuaDrawHelpers.cs    # Lógica de desenho + metadados BIM-LITE
│   │   ├── SisRuaPalette.cs      # WebView2 palette
│   │   ├── GeometryCleaner.cs    # Limpeza de polilinhas duplicadas
│   │   └── Engine/               # Motor de desenho CAD
│   └── sisRUA.Core/      # C# Core DTOs compartilhados
├── docker-compose.yml    # Backend + Redis + Frontend
├── schema/v1/            # JSON Schema (validação de contratos)
├── docs/                 # Documentação técnica
└── MEMORY.MD             # Este arquivo (RAG)
```

---

## 📐 Princípios Arquiteturais (IMUTÁVEIS)

| Princípio | Implementação |
|-----------|---------------|
| Offline-first | Cache local de tiles SRTM; fallback DEM library |
| CRS tratado no início | EPSG:4326 → SIRGAS 2000 UTM (pyproj) |
| Frontend EPSG:4326 | Leaflet com lat/lon WGS84 |
| Backend/CAD: UTM | `sirgas2000_utm_epsg()` detecta zona automaticamente |
| Formato padrão | GeoJSON enriquecido com propriedades `sisrua:*` |
| 2.5D (não 3D) | `elevation` como atributo escalar em `CadFeature`, não coordenada Z |
| Custo zero | Overpass API, OpenTopography, Groq free tier |
| SoC | JS→visualização / C#→orquestração CAD / Python→GIS |
| Segurança | Token IPC, session tokens, rate limiting, audit log |

---

## 🔑 Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `SISRUA_AUTH_TOKEN` | Não (gerado) | Token de autenticação IPC |
| `OPENTOPOGRAPHY_API_KEY` | Não | Para download SRTM (gratuito com chave) |
| `GROQ_API_KEY` | Não | Para AI assistant (Groq free tier) |
| `SENTRY_DSN` | Não | Error monitoring |
| `REDIS_URL` | Não | Cache distribuído (Docker) |
| `SISRUA_DEM_LIBRARY` | Não | Pasta com arquivos .tif locais |
| `SISRUA_TESTING` | Não | Desativa IPC em testes (`"true"`) |

---

## 🗺️ Coordenadas de Teste Padrão

| Descrição | CRS | Valor |
|-----------|-----|-------|
| Coordenada de campo (REF_1) | SIRGAS 2000 UTM 23K | E=788547, N=7634925 |
| Lat/Lon de REF_1 (inversa via pyproj) | EPSG:4326 | ≈ -21.365°, -42.218° |
| Coordenada de projeto (REF_2) | EPSG:4326 | -22.15018°, -42.92185° |
| UTM equivalente de REF_2 | SIRGAS 2000 UTM 23S | E≈714316, N≈7549084 |
| EPSG para ambas as coordenadas (Zona 23) | SIRGAS 2000 | EPSG:31983 (Zona 23S) |
| Raios de teste de REF_1 | — | 100 m |
| Raios de teste de REF_2 | — | 500 m, 1000 m |

> **Nota**: REF_1 (23K 788547 7634925) e REF_2 (-22.15018°, -42.92185°) são
> **dois locais geográficos distintos**, ambos na Zona UTM 23 (EPSG:31983).
> Conversão verificada via `pyproj`: `latlon_to_utm(-22.15018, -42.92185)` → E≈714316, N≈7549084.

---

## 🚦 Status das Fases (Roadmap)

| Fase | Status | Descrição |
|------|--------|-----------|
| 0 — Fundação | ✅ Completo | CRS, modelos de dados, estrutura de pastas |
| 1 — MVP Ruas | ✅ Completo | OSM fetch, projeção UTM, polilinhas CAD |
| 1.5 — Blocos | ✅ Completo | Catálogo de blocos DWG |
| 1.5.1 — SQLite | ✅ Completo | Persistência de projetos |
| 1.5.2 — Limpeza Geom. | ✅ Completo | Dedup, merge, Douglas-Peucker |
| 1.5.7 — Edificações OSM | ✅ Completo | Layer SISRUA_OSM_EDIFICIOS |
| 1.5.8 — Pontos → Blocos | ✅ Completo | Marcadores UI → INSERT CAD |
| 1.6 — UX Instalação | ✅ Completo | Backend silencioso, splash screen |
| 2 — Elevação | ✅ Completo | SRTM + perfil de elevação |
| 3 — OSM Avançado | ✅ Completo | Filtros highway, cache local |
| 4 — App Campo | 🔄 Parcial | PWA conceitual |
| 5 — Drag & Drop | ✅ Completo | GeoJSON drop → CAD |
| 5.5 — Cadastro Técnico | ✅ Completo | XData via Extension Dicts |
| 6 — Nuvem | 🔄 Interfaces | Interfaces desacopladas prontas |

---

## ⚠️ Decisões Técnicas Importantes

### Funções de CRS (crs.py)
- `utm_zone(longitude)` → zona UTM inteira
- `sirgas2000_utm_epsg(lat, lon)` → EPSG da projeção SIRGAS 2000 UTM
- `latlon_to_utm(lat, lon, epsg_out=None)` → `(easting, northing, epsg)` via pyproj
- `utm_to_latlon(easting, northing, epsg_in)` → `(lat, lon)` via pyproj
- `transform_coords(coords, epsg_in, epsg_out)` → lista transformada

Estas funções encapsulam pyproj e são o ponto único de conversão CRS no backend.
- A elevação é armazenada como atributo `elevation` (float) em `CadFeature`, não como coordenada Z.
- As polilinhas CAD são desenhadas em 2D com `elevation` como propriedade de atributo.
- Perfis de elevação são gerados separadamente via `/api/v1/tools/elevation/profile`.

### Modularização de SisRuaCommands.cs
- `SisRuaCommands.cs` (1445 linhas) foi dividido em `partial class` para respeitar a regra de 500 linhas:
  - `Commands/SisRuaCommandDtos.cs` — DTOs HTTP privados (96 linhas)
  - `Commands/SisRuaCommandConfig.cs` — Mapeamento layer/bloco + carregamento de JSON (202 linhas)
  - `Commands/SisRuaCadUtils.cs` — Utilitários CAD: bloco, layer, escala, HTTP (409 linhas)
  - `Commands/SisRuaDrawHelpers.cs` — Desenho em streaming + metadados BIM-LITE (478 linhas)
  - `SisRuaCommands.cs` reduzido a ~307 linhas (campos + comandos SISRUA_* + API pública)
- Bug corrigido: `processingResult.Tolerance` não existia no tipo anônimo retornado por `DrawCadFeatureDtos`; adicionado `Tolerance = 0.0` ao tipo anônimo e null-guard para resultado nulo.

### Sem Mock Data
- O endpoint `/api/v1/sync/cloud` anteriormente usava `time.sleep(1.5)` com dados estáticos fictícios. 
  Foi corrigido para retornar status real baseado em dados do banco de dados local.
- Nenhum endpoint deve retornar dados inventados. Fallback aceitável: erro 503 com mensagem clara.

### Modularização de api.py
- `api.py` foi dividido em `backend/routes/` com routers por domínio (SoC).
- Regra: arquivos > 500 linhas devem ser modularizados.

### Segurança
- Todos os endpoints sensíveis requerem `X-SisRua-Token`.
- Tokens de sessão de curta duração (30 min) via `/api/v1/auth/session`.
- Rate limiting: 5 jobs/min por IP.
- Origin validation middleware (ISO 27001).
- Input sanitization via `sanitize_jsonable()`.

### Validação de Coordenadas nos Modelos (models.py)
- `PrepareOsmRequest`: latitude (`-90 ≤ lat ≤ 90`), longitude (`-180 ≤ lon ≤ 180`), radius (`0 < r ≤ 50000 m`).
- `PrepareJobRequest`: mesmos limites para os campos opcionais OSM.
- `ElevationQueryRequest`: latitude e longitude com os mesmos limites globais.
- `ElevationProfileRequest`: mínimo de 2 pontos; cada ponto validado individualmente via `field_validator`.
- Validação é feita no modelo (Pydantic), retornando HTTP 422 antes de qualquer processamento de negócio.

### Bug Corrigido — `core/utils.py` (`get_layer_config`)
- A linha `logger.error("json_load_failed", ..., path=path)` referenciava a variável `path`, que não
  estava definida nesse escopo (a variável correta era `layers_path`).
- Corrigido para `path=str(layers_path)`.
- Impacto: quando `layers.json` existia mas era inválido (JSON malformado), ocorria `NameError` em vez
  de fallback para a configuração hardcoded — potencial 500 em produção.



---

## 🧪 Infraestrutura de Testes

| Tipo | Ferramenta | Localização |
|------|------------|-------------|
| Unit (Python) | pytest | `src/backend/tests/` |
| E2E (Frontend) | Playwright | `src/frontend/e2e/` |
| Unit (Frontend) | Vitest | `src/frontend/src/**/*.test.jsx` |
| DXF headless | ezdxf + pytest | `src/backend/tests/test_dxf.py` |
| C# | xUnit | `src/plugin/tests/` |

> **Cobertura atual**: 96 testes pytest passando (Python backend).

---

## 🐳 Docker

```bash
# Subir todo o stack
docker-compose up -d

# Backend apenas
docker-compose up backend

# Rebuild forçado
docker-compose build --no-cache
```

---

## 📦 Dependências Chave (Backend)

| Lib | Uso | Custo |
|-----|-----|-------|
| FastAPI + uvicorn | API REST | Gratuito |
| pyproj | Conversão CRS | Gratuito |
| shapely | Geometria | Gratuito |
| rasterio | Leitura GeoTIFF SRTM | Gratuito |
| requests | Overpass + OpenTopography | Gratuito |
| groq | AI (LLM) | Free tier |
| structlog | Logging estruturado | Gratuito |
| sentry-sdk | Error monitoring | Free tier |
| ezdxf | Geração/validação de DXF | Gratuito |

---

## 🔄 Fluxo Típico de Uso

```
1. Usuário abre AutoCAD → plugin carrega WebView2 (React)
2. Usuário insere coordenada ou Drag & Drop de GeoJSON
3. Frontend envia POST /api/v1/jobs/prepare (kind=osm ou geojson)
4. Backend processa: Overpass → CRS → Topology healing → CadFeatures
5. Plugin C# recebe JSON → insere polilinhas/blocos no desenho
6. Elevação aplicada via /api/v1/tools/elevation/query (SRTM offline-first)
7. Projeto salvo em SQLite local via SISRUA_SAVE_PROJECT
```

---

## 📝 Convenções de Camadas CAD

| Layer AutoCAD | Conteúdo |
|---------------|----------|
| `SISRUA_OSM_HIGHWAY` | Vias principais |
| `SISRUA_OSM_RESIDENTIAL` | Vias residenciais |
| `SISRUA_OSM_EDIFICIOS` | Edificações |
| `SISRUA_OSM_NODES` | Pontos de infraestrutura |
| `SISRUA_GEOJSON` | Importações manuais GeoJSON |
| `SISRUA_ELEVATION` | Curvas de nível |

---

## 🛡️ Conformidade

- **ISO 27001**: Session tokens, origin validation, audit log, rate limiting
- **LGPD/GDPR**: Housekeeper service (limpeza automática de dados temporários)
- **ISO 9001**: Rastreabilidade de jobs via trace ID
- **BIM-LITE**: CadFeature com propriedades enriquecidas (atributos não-gráficos)

---

*Última atualização: 2026-02-21 | Versão do projeto: 1.1.0 | Modularização: SisRuaCommands → partial class | Validação de coordenadas + bug fix get_layer_config + bug fix ElevationService cache em geojson.py (101 testes)*

---

## 🔐 Sessão 2026-02-21 — Correções de Segurança e Qualidade

### Autenticação nas Rotas de Auditoria (`audit_routes.py`)
- **Problema**: Todos os endpoints `/api/audit/*` e `/api/valuation/summary` eram públicos (sem autenticação), violando ISO 27001.
- **Correção**: Adicionada dependência `require_token` em **todos** os 8 endpoints do router de auditoria:
  - `POST /api/audit` — criação de log
  - `GET /api/audit` — listagem
  - `GET /api/audit/{id}` — leitura específica
  - `GET /api/audit/{id}/verify` — verificação de assinatura
  - `POST /api/audit/verify-all` — verificação em lote
  - `GET /api/audit/stats` — estatísticas
  - `GET /api/audit/export/compliance` — exportação CSV
  - `GET /api/valuation/summary` — métricas de valuação

### Sanitização de Entrada (`audit_routes.py`)
- `POST /api/audit`: campos `event_type`, `entity_type`, `entity_id`, `user_id` agora passam por `_safe_str()` (trunca em 256 chars — proteção DoS).
- Campo `data` (dict livre) passa por `sanitize_jsonable()` (remove NaN/Inf, garante JSON estrito).
- Limite `verify-all`: `limit` validado e clampeado entre 1 e 10000.
- Imports reorganizados no topo do arquivo (clean code).

### Docker Compose — Healthchecks de Produção (`docker-compose.yml`)
- `backend`: healthcheck via `curl /api/v1/health` (30s interval, 3 retries, 15s start).
- `redis`: healthcheck via `redis-cli ping` (10s interval).
- `frontend`: `depends_on: backend: condition: service_healthy` (aguarda backend pronto).
- Todos os serviços com `restart: unless-stopped`.

### Testes — Cobertura de Segurança (`test_security_iso27001.py`)
- 7 novos testes adicionados (total: 91 passando):
  - `test_audit_post_requires_auth` — sem token → 401
  - `test_audit_get_requires_auth` — sem token → 401
  - `test_audit_stats_requires_auth` — sem token → 401
  - `test_audit_export_requires_auth` — sem token → 401
  - `test_valuation_requires_auth` — sem token → 401
  - `test_audit_post_with_valid_token` — token válido → 201
  - `test_audit_sanitizes_oversized_fields` — truncamento verificado

---

## 🔐 Sessão 2026-02-21 — Bug Fix e Segurança (Webhook)

### Bug Corrigido — `services/elevation.py` (`get_contours`)
- **Problema**: Instrução `return results` duplicada (linhas 225–226). A segunda instrução era código morto (unreachable), encobrindo possíveis futuros refactors.
- **Correção**: Linha duplicada removida.
- **Impacto**: Sem impacto funcional imediato, mas melhora legibilidade e evita confusão em refactors futuros.

### Segurança — `models.py` (`WebhookRegistrationRequest`)
- **Problema**: O campo `url` aceitava qualquer string, incluindo esquemas `ftp://`, `file://`, ausência de hostname — vetor de SSRF (Server-Side Request Forgery).
- **Correção**: Adicionado `@field_validator("url")` que:
  - Exige prefixo `http://` ou `https://` (case-insensitive).
  - Exige `netloc` (hostname) via `urllib.parse.urlparse`.
  - Retorna HTTP 422 com mensagem clara para URLs inválidas.
- Adicionado `@field_validator("events")`:
  - Trunca cada item a 128 caracteres (DoS prevention).
  - Retira espaços em branco.
  - Retorna `None` se a lista ficar vazia após sanitização.

### Testes — Cobertura de Webhook (`test_core.py`)
- 8 novos testes adicionados (total: **96 passando**):
  - `test_webhook_valid_https_url` — URL HTTPS aceita
  - `test_webhook_valid_http_url` — URL HTTP aceita
  - `test_webhook_invalid_scheme_rejected` — `ftp://` rejeitado (422)
  - `test_webhook_file_scheme_rejected` — `file://` rejeitado (422)
  - `test_webhook_no_scheme_rejected` — URL sem esquema rejeitada (422)
  - `test_webhook_events_sanitized` — truncamento a 128 chars verificado
  - `test_webhook_events_empty_list_becomes_none` — lista vazia → `None`
  - `test_webhook_events_none_allowed` — `None` é aceito normalmente

---

## 🐛 Sessão 2026-02-21 — Bug Fix ElevationService + Qualidade de Código

### Bug Corrigido — `services/geojson.py` (`prepare_geojson_compute`)
- **Problema**: `ElevationService()` era instanciado **sem** o argumento obrigatório `cache`, causando `TypeError` silencioso (capturado pelo bloco `except Exception`) durante injeção de elevação no pipeline GeoJSON. O resultado era que features GeoJSON nunca recebiam dados de elevação, sem qualquer aviso ao operador.
- **Correção**:
  - `ElevationService()` substituído por `ElevationService(cache=_cache_svc)`, onde `_cache_svc` é o `cache_service` singleton importado de `backend.services.cache`.
  - `print(f"Error injecting elevation data for GeoJSON: {e}")` substituído por `logger.warning("elevation_injection_failed_geojson", error=str(e))` (logging estruturado — clean code).
  - `get_logger(__name__)` adicionado ao módulo `geojson.py`.
- **Impacto**: Features GeoJSON passam a receber elevação corretamente quando o DEM está disponível (online ou cache local). Falhas de elevação agora são registradas no log estruturado.

### Testes — Cobertura da Correção (`test_services.py`)
- 2 novos testes adicionados (total: **101 passando**):
  - `test_elevation_service_requires_cache` — Verifica via `inspect.signature` que `cache` é parâmetro obrigatório.
  - `test_geojson_elevation_injection_uses_cache` — Spy em `ElevationService.__init__` garante que o cache não é `None` quando injetado pelo pipeline GeoJSON.
