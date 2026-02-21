# sisRUA — RAG / Memória de Trabalho

> Arquivo de memória viva do projeto. Atualizado a cada sessão de desenvolvimento.
> Usado como fonte de contexto (RAG) por todos os agentes e pelo AI assistente embutido.

---

## 🧭 Visão Geral

**sisRUA** é um plugin AutoCAD enterprise de nível de produção para processamento urbano GIS.  
Pipeline técnico: Campo → GIS → CAD, offline-first, custo zero.

- **Repositório**: `jrlampa/plugin_autocad`
- **Branch principal de desenvolvimento**: `dev`
- **Versão atual**: `0.1.0`
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

*Última atualização: 2026-02-21 | Versão do projeto: 0.1.0 | Versionamento zerado e sincronizado em todo o projeto*

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

---

## ⚡ Sessão 2026-02-21 — Fix: Retry em Modo de Teste + Estabilidade CI

### Bug Corrigido — `core/retry.py` (atrasos de retry em CI)
- **Problema**: O decorador `@Retry(max_retries=3, initial_delay=2.0)` aplicado a `_download_grid` no `ElevationService` causava espera de ~14 segundos (2s + 4s + 8s) em CI (sem rede). Os testes `test_create_prepare_job_geojson_completes` e `test_create_prepare_job_geojson_blocks_completes` possuem deadline de polling de 10 segundos, tornando o job impossível de completar antes do prazo → `AssertionError: 'processing' == 'completed'`.
- **Correção**:
  - `core/retry.py`: Quando `SISRUA_TESTING=true`, o `sleep_time` é zerado (sem espera entre tentativas).
  - `tests/conftest.py`: Adicionado `os.environ.setdefault("SISRUA_TESTING", "true")` para garantir que todos os testes rodem em modo de teste.
- **Impacto**: Todos os 101 testes passam agora em ~3.7 segundos (anteriormente 2 falhavam por timeout). Comportamento em produção inalterado (SISRUA_TESTING não definido → backoff exponencial normal).

### Infraestrutura de Testes
- Cobertura total: **101 testes passando** (sem alterações).
- `SISRUA_TESTING=true` é agora definido automaticamente em toda sessão de testes via `conftest.py`.

---

## 📐 Sessão 2026-02-21 — Conformidade ABNT + DXF Aprimorado

### Novo Módulo — `gis_core/abnt.py`
- **Criado**: módulo de conformidade ABNT para exportação CAD urbana.
- **Normas aplicadas**:
  - ABNT NBR 14166:1998 — Rede de referência cadastral municipal
  - ABNT NBR 13133:2021 — Execução de levantamento topográfico
  - ABNT NBR 15777:2009 — Representação de informação geográfica digital
- **Principais exports**:
  - `AbntDrawingMetadata` (dataclass frozen) — metadados de desenho técnico (CRS, escala, tolerância, órgão, datum, projeção, zona UTM)
  - `validate_utm_coordinates(easting, northing, epsg)` — valida limites do território brasileiro (NBR 14166 §4.1)
  - `nearest_abnt_escala(value)` — retorna escala ABNT NBR 13133 mais próxima da lista padronizada
  - `build_default_metadata(epsg)` — constrói metadados a partir do EPSG (deriva zona_utm e crs_label)
  - `ABNT_ESCALAS_CADASTRAIS` — lista de escalas tabeladas: 500, 1000, 2000, 5000, 10000, 25000, 50000, 100000
- **Tolerâncias**: mapeadas por escala (0,2 mm × denominador conforme §8.5 da NBR 13133:2021).

### Evolução — `services/dxf_export.py`
- **Assinatura atualizada**: `export_features_to_dxf(features, output_path, crs_label, metadata, epsg)`.
  - Parâmetro `metadata: Optional[AbntDrawingMetadata]` — metadados ABNT explícitos.
  - Parâmetro `epsg: int = 31983` — usado em `build_default_metadata` quando `metadata` não fornecido.
- **Injeção ABNT**: `_inject_abnt_metadata(doc, metadata)` grava `$FINGERPRINTGUID` com string de rastreabilidade sisRUA (datum, zona, escala) — rastreabilidade BIM-LITE.
- **Log aprimorado**: `dxf_exported` agora loga `crs` e `escala` além de `path` e `features`.
- **Retrocompatibilidade**: chamadas sem `metadata` e sem `epsg` continuam funcionando (padrão 31983).

### Testes — 11 novos testes ABNT (total: **112 passando**)
Adicionados ao final de `tests/test_dxf.py`:
  - `test_abnt_module_imports` — importações do módulo sem erros
  - `test_abnt_metadata_defaults` — campos padrão corretos (SIRGAS 2000, 'm', EPSG:31983)
  - `test_abnt_escala_str` — notação '1:1.000' e '1:25.000'
  - `test_abnt_tolerancia_por_escala` — tolerâncias para escalas 500, 1000, 10000
  - `test_abnt_validate_utm_coordinates_valid` — REF_1 e REF_2 aprovados
  - `test_abnt_validate_utm_coordinates_invalid` — coordenadas fora do Brasil rejeitadas
  - `test_abnt_nearest_escala` — escala mais próxima para valores intermediários
  - `test_abnt_build_default_metadata_epsg` — derivação de zona e label a partir de EPSG
  - `test_abnt_comment_lines_content` — campos obrigatórios NBR 14166 presentes
  - `test_dxf_with_abnt_metadata` — DXF gerado com metadata explícito tem FINGERPRINTGUID
  - `test_dxf_without_explicit_metadata_uses_default` — DXF sem metadata usa build_default_metadata

### .gitignore — Artefatos excluídos
- `all_files.txt` (1.5 MB — gerado por análise interna, não deve ser versionado)
- `desktop.ini` (artefato Windows)
- `build_out.txt`, `test_out_full.txt` (saídas de build/teste)
- `pytest_v110_output.txt`, `vitest_results.txt`, `vitest_results_v2.txt`, `vitest_v110_output.txt`
- `src/backend/backend/gis_core/topology_report.json` (artefato gerado em runtime)

### Infraestrutura de Testes
- Cobertura total: **112 testes passando** (~3.6 segundos).
- Novos testes são todos headless (sem rede, sem filesystem externo), executáveis em CI.

---

## 🐛 Sessão 2026-02-21 — Bug Fixes, Clean Code e DXF API Endpoint

### Bug Corrigido — `services/elevation.py` (null guard para DEM ausente)
- **Problema**: `get_elevation_profile` e `get_contours` lançavam `AttributeError` (tentativa de `rasterio.open(None)`) quando nenhum DEM estava disponível offline (`tif_path is None`).
- **Correção em `get_elevation_profile`**: Adicionada guarda após `get_elevation_grid()` — retorna `[None] * len(coordinates)` com log `elevation_profile_no_dem`.
- **Correção em `get_contours`**: Adicionada guarda antes dos imports pesados (`rasterio`, `numpy`, `skimage`) — retorna `[]` com log `contours_no_dem`. Mover o null check antes dos imports também resolve `ModuleNotFoundError: No module named 'skimage'` em ambientes sem scikit-image (CI/CD).
- **Impacto**: Pipeline continua funcionando sem DEM local ou conectividade com OpenTopography — features são geradas sem elevação em vez de crashar.

### Clean Code — `gis_core/osm.py` (classes inline → módulo)
- **Problema**: `MockRow` e `MockNode` eram classes Python definidas **dentro de loops** em `_parse_overpass_to_features`. Isso cria closures desnecessárias, dificulta testes unitários e é um code smell clássico.
- **Correção**: Extraídas para classes de módulo `_OsmWayRow` e `_OsmNodeRow`:
  - `__slots__` para eficiência de memória.
  - Documentação clara de responsabilidade.
  - Importação de `Point` (shapely) movida para `_OsmNodeRow.__init__` (lazy import).
  - Import de `Point` removido da função `_parse_overpass_to_features` (agora usa apenas `LineString`).
- **Impacto**: Testabilidade isolada das estruturas OSM; sem mudança funcional.

### Novo Endpoint — `GET /api/v1/export/dxf/{project_id}` (`enterprise.py`)
- **Feature**: Endpoint REST que exporta um projeto salvo no SQLite como arquivo DXF R2010.
- **Parâmetro de query**: `escala` (int, padrão: 1000) — define a escala ABNT cartográfica.
- **Retorno**: `FileResponse` com `media_type="application/dxf"`.
- **Conformidade**: Usa `export_project_to_dxf()` que injeta metadados ABNT NBR 14166/13133.
- **Erros**: 404 para projeto inexistente; 500 com mensagem para falhas internas.
- **Requer autenticação**: `X-SisRua-Token` (ISO 27001).

### Refatoração — `services/export_service.py`
- **Bug corrigido**: `str(Path().stat().st_mtime)` → `datetime.now(timezone.utc).isoformat()` (timestamp correto no GeoJSON exportado).
- **Helpers extraídos**: `_fetch_cad_rows()` e `_check_project_exists()` — reutilizados por GeoJSON, GeoPackage e DXF export.
- **GeoPackage**: Não tenta mais INSERT em `gpkg_contents`/`gpkg_geometry_columns` se essas tabelas não existirem na cópia do DB (evita `OperationalError` em banco padrão sisRUA).
- **NotFoundError**: Todos os métodos de export lançam `NotFoundError` quando o projeto não existe (antes apenas GeoPackage verificava, mas de forma incorreta).
- **Novo método**: `export_project_to_dxf(project_id, escala=1000)` — lê features do SQLite, reconstrói `CadFeature` e chama `export_features_to_dxf()` com metadados ABNT derivados do CRS armazenado.

### Testes — 6 novos (total: **118 passando**)
Adicionados ao final de `tests/test_services.py`:
  - `test_elevation_profile_returns_nones_when_no_dem` — null guard verificado sem DEM
  - `test_elevation_contours_returns_empty_when_no_dem` — null guard verificado sem DEM
  - `test_export_service_dxf_not_found` — NotFoundError para projeto inexistente
  - `test_export_service_dxf_creates_valid_file` — DXF gerado, válido R2010+, com 1 polilinha
  - `test_osm_way_row_module_level` — _OsmWayRow acessível no módulo, atributos corretos
  - `test_osm_node_row_module_level` — _OsmNodeRow acessível no módulo, coordenadas corretas

### CodeQL — 0 alertas

---

## 📦 Sessão 2026-02-21 — Modularização test_dxf.py + Limpeza de Artefatos

### Modularização — `tests/test_dxf.py` (596 → 450 linhas)
- **Problema**: `test_dxf.py` atingiu 596 linhas, violando a regra de 500 linhas.
- **Solução**: Extraídos 11 testes ABNT para `tests/test_dxf_abnt.py` (196 linhas):
  - `test_abnt_module_imports` — importação do módulo
  - `test_abnt_metadata_defaults` — campos padrão SIRGAS 2000
  - `test_abnt_escala_str` — notação 1:1.000 / 1:25.000
  - `test_abnt_tolerancia_por_escala` — tolerâncias NBR 13133:2021
  - `test_abnt_validate_utm_coordinates_valid` — REF_1 e REF_2 dentro do Brasil
  - `test_abnt_validate_utm_coordinates_invalid` — coordenadas fora do Brasil
  - `test_abnt_nearest_escala` — escala ABNT mais próxima
  - `test_abnt_build_default_metadata_epsg` — derivação de zona do EPSG
  - `test_abnt_comment_lines_content` — campos obrigatórios NBR 14166
  - `test_abnt_dxf_header_fingerprintguid` — DXF com metadata ABNT explícito
  - `test_abnt_dxf_default_metadata_applied` — DXF sem metadata usa default
- `test_dxf.py` mantém 18 testes de geometria DXF (450 linhas).
- Ambos os arquivos estão abaixo de 500 linhas.
- Helpers locais (`_make_road`, constantes REF_E/REF_N/REF2_E/REF2_N) duplicados em `test_dxf_abnt.py` para independência de arquivo (padrão pytest recomendado).

### Limpeza de Artefatos — git rm --cached
- Removidos do índice git (mas mantidos localmente conforme `.gitignore`):
  - `src/backend/pytest_v110_output.txt`
  - `src/frontend/build_out.txt`
  - `src/frontend/test_out_full.txt`
  - `src/frontend/vitest_results.txt`
  - `src/frontend/vitest_results_v2.txt`
  - `src/frontend/vitest_v110_output.txt`
- Esses arquivos já estavam no `.gitignore` mas eram rastreados por terem sido commitados antes das regras de ignore.

### Infraestrutura de Testes
- Cobertura total: **118 testes passando** (inalterado — apenas reorganização de arquivos).
- Novo arquivo: `tests/test_dxf_abnt.py` (11 testes ABNT, 196 linhas).

---

## 🆕 Sessão 2026-02-21 — GET /projects Endpoint + Clean Code + Docker 3.12

### Novo Endpoint — `GET /api/v1/projects/{project_id}` (`routes/projects.py`)
- **Problema**: `ProjectService.get_project()` existia desde a Fase 1.5.1, mas não tinha exposição HTTP. Para completar o CRUD de projetos, o frontend e o SDK precisam ler metadados de um projeto por ID.
- **Implementação**: 
  ```
  GET /api/v1/projects/{project_id}
  Headers: X-SisRua-Token (obrigatório — ISO 27001)
  200 → {project_id, project_name, crs_out, version, creation_date}
  404 → {"detail": "Projeto '{id}' não encontrado."} (em pt-BR)
  ```
- **Delegação**: chama `project_service.get_project(project_id)` do composition root.

### Clean Code — `TROJAN HORSE` Comments Removidos
- **Arquivo**: `services/geojson.py` linha 105 e `gis_core/osm.py` linha 231.
- **Problema**: Comentários com nomenclatura interna coloquial (`TROJAN HORSE`) são inapropriados em código de produção enterprise.
- **Correção**: Substituídos por comentários técnicos precisos descrevendo o mapeamento de ativos urbanos OSM → blocos CAD e a persistência no banco local para enriquecimento BIM-LITE.

### Docker — `python:3.10-slim` → `python:3.12-slim` (`src/backend/Dockerfile`)
- **Problema**: A imagem base usava Python 3.10, enquanto o ambiente CI (e todas as sessões de desenvolvimento) usa Python 3.12.3. Inconsistência que pode causar bugs sutis de compatibilidade.
- **Correção**: `FROM python:3.10-slim` → `FROM python:3.12-slim`.
- **Benefícios**: Patches de segurança de 2024-2025, melhorias de performance (GIL melhorado, parser mais rápido), compatibilidade com type hints modernos usados no projeto.

### Testes — 3 novos (total: **121 passando**)
Adicionados ao final de `tests/test_api_auth_and_jobs.py`:
  - `test_get_project_not_found` — GET retorna 404 com mensagem pt-BR para projeto inexistente
  - `test_get_project_requires_auth` — GET sem token retorna 401 (ISO 27001)
  - `test_get_project_success` — GET retorna estrutura completa do projeto

### CodeQL — 0 alertas

---

## ⚙️ Sessão 2026-02-21 — Implementação TopologyHealer.heal_network() (Union-Find)

### Problema
`TopologyHealer.heal_network()` em `gis_core/topology.py` era um stub completo:
```python
# (Conceptual implementation for brevity - fully logic-hardened)
return features
```
O método era chamado em cada requisição OSM (`gis_core/osm.py:352`) mas não fazia nada.
Isso significa que gaps de topologia (nós desconectados, micro-gaps de digtização OSM) não eram
corrigidos, comprometendo a qualidade das malhas viárias geradas para CAD/BIM.

### Solução Implementada — Union-Find Node Snapping
Arquivo: `src/backend/backend/gis_core/topology.py`

**Algoritmo**: Union-Find (Disjoint Set Union) com path compression.
- **Complexidade**: O(n²) para verificação de pares de endpoints + O(α(n)) amortizado para Union-Find.
- **Corretude**: Trata corretamente junções T/X onde 3+ estradas compartilham um nó.

**Fluxo**:
1. Coleta todos os endpoints (primeiro e último vértice) de polylines
2. Para cada par de endpoints, usa `math.sqrt(dx²+dy²) < snap_tolerance` para decidir se devem ser unidos
3. Agrupa via Union-Find (path compression para O(α(n)) amortizado)
4. Snap cada grupo ao centróide geométrico
5. Atualiza `stats["healed_nodes"] = len(group) - 1` para cada grupo

**Auxiliares extraídos**:
- `_make_uf(n)` — inicializa parent array
- `_uf_find(parent, x)` — path-compressed Find
- `_uf_union(parent, a, b)` — union por raiz

**Parâmetros**:
- `snap_tolerance = 0.05` m (5 cm, padrão) — adequado para dados OSM projetados em UTM
- `integrity_seed = "sisRUA_v1.1"` — semente para HMAC de integridade

**Comentário removido**: "Conceptual implementation for brevity - fully logic-hardened" → substituído por docstrings precisos.

### Testes — 12 novos (total: **133 passando**)
Novo arquivo: `tests/test_topology.py`:
  - `test_topology_healer_single_feature_passthrough` — 1 polilinha, nada para snap
  - `test_topology_healer_far_endpoints_not_snapped` — endpoints >tol, sem snap
  - `test_topology_healer_snaps_close_endpoints` — gap 4cm < 10cm tol → snap ao centróide
  - `test_topology_healer_does_not_snap_above_tolerance` — gap 20cm > 10cm tol → sem snap
  - `test_topology_healer_snaps_t_junction` — junção T (3 polilínias) → centróide correto
  - `test_topology_healer_preserves_point_features` — Point features passam inalteradas
  - `test_topology_healer_empty_features` — lista vazia sem exceção
  - `test_topology_healer_integrity_signature_deterministic` — assinatura estável
  - `test_topology_healer_robust_signature_deterministic` — assinatura robusta estável
  - `test_topology_healer_signature_changes_with_geometry` — geometrias diferentes → assinaturas diferentes
  - `test_topology_healer_stats_reset_between_instances` — stats isoladas por instância
  - `test_topology_healer_get_report` — report tem summary e metrics

### CodeQL — 0 alertas
