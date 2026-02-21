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

### DXF / CAD
- A geração de features CAD é feita em Python (backend) e enviada como JSON para o plugin C#.
- O plugin C# (AutoCAD) consome o JSON e insere entidades no desenho.
- Testes de DXF são executados headless via `accoreconsole.exe` ou via `ezdxf` em Python.

---

## 🧪 Infraestrutura de Testes

| Tipo | Ferramenta | Localização |
|------|------------|-------------|
| Unit (Python) | pytest | `src/backend/tests/` |
| E2E (Frontend) | Playwright | `src/frontend/e2e/` |
| Unit (Frontend) | Vitest | `src/frontend/src/**/*.test.jsx` |
| DXF headless | ezdxf + pytest | `src/backend/tests/test_dxf.py` |
| C# | xUnit | `src/plugin/tests/` |

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

*Última atualização: 2026-02-21 | Versão do projeto: 1.1.0 | Modularização: SisRuaCommands → partial class*
