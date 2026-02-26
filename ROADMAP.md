# sisRUA — Roadmap Oficial · Foco Alpha Release

> **Versão atual:** `0.2.0-alpha` (branch `dev` → `main`)
> **Meta imediata:** Alpha release funcional para primeiros usuários técnicos (projetistas de rede elétrica MT/BT).

---

## 🏁 Alpha Release Checklist (`v0.3.0-alpha`)

| # | Item | Status | Responsável |
|---|------|--------|-------------|
| 1 | `<AiAssistant>` sem Suspense → sem tela branca (ErrorBoundary cobre) | ✅ Pronto | Dev |
| 2 | `LoadingScreen` mostra versão correta (`v0.2.0-alpha`) | ✅ Feito | Dev |
| 3 | Dockerfile CMD usa `${PORT:-8000}` (Cloud Run compatível) | ✅ Feito | DevOps |
| 4 | `cloudrun.tf` sem `revision_name` hardcoded | ✅ Feito | DevOps |
| 5 | CORS configurável via `SISRUA_CORS_ORIGINS` (Cloud Run) | ✅ Feito | Dev |
| 6 | CI/CD deploy automático para Cloud Run em push `main` | ✅ Feito | DevOps |
| 7 | 983 backend tests · 100% cobertura | ✅ Feito | QA |
| 8 | 395 frontend tests · 99.35% cobertura | ✅ Feito | QA |
| 9 | Backend embarcado: `standalone.py` + PyInstaller | ✅ Pronto | Dev |
| 10 | IPC Named Pipe (Windows) handshake C# ↔ Python | ✅ Pronto | Dev |
| 11 | Build do frontend React (`npm run build`) sem erros | ✅ Pronto | Dev |
| 12 | Healthcheck `/api/v1/health` respondendo | ✅ Pronto | Dev |
| 13 | `ErrorBoundary` capturando erros críticos no frontend | ✅ Pronto | Dev |
| 14 | Processo de build do plugin C# (`.bundle` gerado) | ⚠️ Manual | Dev |
| 15 | Teste E2E real com coordenadas de campo (REF_2) | ⚠️ Pendente | QA |

### Bloqueadores Alpha (devem ser zero antes do release)

- [ ] **E2E manual**: Abrir AutoCAD 2025, instalar bundle, rodar `SISRUA_PREPARAR` com REF_2 (`-22.15018, -42.92185`) em 500m e 1km → polilinhas desenhadas corretamente.
- [ ] **Tela branca**: Validar no WebView2 real (AutoCAD) que `LoadingScreen` aparece e desaparece corretamente.
- [ ] **Configurar secrets no GitHub**: `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `SISRUA_AUTH_TOKEN`, `GROQ_API_KEY` (para ativar deploy automático).

---

## 📦 Modo de Entrega Alpha

O alpha será entregue em **dois sabores**:

### 🖥️ sisRUA Full (Plugin AutoCAD — Standalone)
```
sisRUA.bundle/
├── Contents/
│   ├── backend/
│   │   └── sisrua_backend.exe   ← Python embarcado via PyInstaller
│   ├── frontend/
│   │   └── dist/                ← React buildado, servido pelo backend
│   ├── Blocks/                  ← Blocos DWG (postes, medidores, etc.)
│   └── SisRuaPlugin.dll         ← Plugin C# (AutoCAD 2020-2026)
└── PackageContents.xml
```
- Não requer Python instalado
- Não requer conexão com internet
- Backend inicia silenciosamente, comunica via Named Pipe com o plugin

### ☁️ sisRUA LT (Cloud Run — API remota)
```
Plugin C# leve → HTTPS → Cloud Run (sisrua-backend)
```
- Plugin sem backend embarcado
- Token de autenticação gerenciado via `SISRUA_AUTH_TOKEN` no Cloud Run
- Deploy automatizado por CI/CD ao merge em `main`

---

## 🗺️ Fases Pós-Alpha

### v0.4.0 — Beta Fechado (primeiros 5 projetistas)
- [x] Onboarding guiado dentro do AutoCAD (wizard de primeira instalação) — `OnboardingWizard.jsx` 4 etapas
- [x] Exportação DXF headless via `ezdxf` (sem AutoCAD aberto) — `export_features_to_dxf()`
- [x] Curvas de nível SRTM na layer `SISRUA_TOPO` — `add_contours_to_dxf()` + `export_project_with_topo()`
- [ ] Suporte a importação de DXF/DWG existente (retrocompatibilidade)

### v0.5.0 — Beta Aberto (10+ projetistas)
- [ ] App de campo PWA offline (`sisDRONE` integrado)
- [ ] Drag & drop GeoJSON de campo → CAD
- [x] XData BIM-LITE completo: "uma rua sabe que é uma rua" — `_build_bim_xdata()` com class/highway/name/width/elevation/slope/layer
- [x] Blocos CAD completos: postes, medidores, caixas de passagem, transformadores — `blocks.py` + `define_electrical_blocks()`

### v1.0.0 — Release Público
- [ ] Integração `sisCQT`: cálculo de queda de tensão MT/BT (normativa Light)
- [ ] Geração automática de lista de material e custos
- [ ] Relatório de projeto em PDF
- [ ] Suporte multi-usuário (projetos compartilhados via Cloud Run)
- [ ] `sisDRONE`: twin digital de campo integrado

---

## 🏗️ Princípios Arquiteturais (IMUTÁVEIS)

| Princípio | Implementação atual |
|-----------|---------------------|
| **Offline-first** | Cache SRTM local; Overpass sem API key |
| **CRS no início do fluxo** | EPSG:4326 → SIRGAS 2000 UTM (pyproj) automático |
| **Frontend: EPSG:4326** | Leaflet com lat/lon WGS84 |
| **Backend/CAD: UTM** | `sirgas2000_utm_epsg()` detecta zona automaticamente |
| **2.5D (não 3D)** | `elevation` como atributo escalar, não coordenada Z |
| **Custo zero** | Overpass, OpenTopography, Groq free tier, Cloud Run free tier |
| **Docker first** | Backend + Redis + Frontend em `docker-compose.yml` |
| **DDD** | Domain / Application / Infrastructure / Shared layers |
| **SoC** | JS→visualização · C#→orquestração CAD · Python→GIS |
| **Half-way BIM** | XData em entidades CAD (rua, poste, medidor) |
| **Segurança** | Token IPC, rate limiting, audit log, sanitização de dados |
| **Interfaces pt-BR** | Todos os textos de UI em português brasileiro |

---

## 🔑 Setup Mínimo para Alpha (Cloud Run)

```bash
# 1. Configurar secrets no GitHub (Settings → Secrets):
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/.../locations/global/workloadIdentityPools/...
GCP_SERVICE_ACCOUNT=sisrua-production-sa@PROJECT.iam.gserviceaccount.com

# 2. Configurar variáveis no GitHub (Settings → Variables):
GCP_PROJECT_ID=meu-projeto-gcp
GCP_REGION=southamerica-east1
SISRUA_CORS_ORIGINS=https://sisrua.app

# 3. Criar secrets no Google Secret Manager:
echo -n "$(openssl rand -hex 32)" | gcloud secrets create sisrua-auth-token --data-file=-
echo -n "gsk_..." | gcloud secrets create groq-api-key --data-file=-

# 4. Push para main → deploy automático via CI/CD
git push origin main
```

---

## 📊 Métricas de Qualidade Atuais

| Métrica | Valor |
|---------|-------|
| Backend tests | 935 / 935 ✅ |
| Backend coverage | 100% ✅ |
| Frontend tests | 362 / 362 ✅ |
| Frontend coverage | 99.35% ✅ |
| Total tests | 1297 ✅ |
| Linhas máx. por arquivo | 500 (regra) ✅ |
| Vulnerabilidades CodeQL | 0 ✅ |

---

> **Atualizado em:** 2026-02-25 · **Sessão:** BIM-LITE XData + SISRUA_TOPO Contours
