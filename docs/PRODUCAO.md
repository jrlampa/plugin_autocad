# Prontidão para produção (tech-lead) — sisRUA

Este documento resume o nível de prontidão do sisRUA para “produção” (usuário final / Autodesk App Store) e um plano curto de hardening.

## Nota atual (estimativa)

- **7,5/10 (~75%)** — base sólida e fluxo principal funcionando, mas ainda há pontos de segurança/robustez e “polimento” que impactam suporte e confiança do usuário final.

## O que já está bem encaminhado

- **Autoload via bundle** (`ApplicationPlugins`) com build de release e instalador.
- **Backend local** (FastAPI) e **frontend embutido** (React build em `Contents/frontend/dist`).
- **Porta dinâmica + health/auth-check** no plugin.
- **Atribuição OSM (ODbL)** no desenho (camada `SISRUA_ATTRIB`).
- **Trusted Location**: instalador tenta adicionar `sisRUA.bundle\...` ao `TRUSTEDPATHS` (reduz popup “Trusted Folder”).

## Gaps (alto impacto)

- **Assinatura de código ausente**:
  - Sem assinatura, a UX piora (warnings e desconfiança), principalmente para App Store.
  - Recomendação: assinar **DLLs do plugin**, **sisrua_backend.exe** e **instalador**.

- **Token persistido em texto plano**:
  - Hoje o plugin persiste `backend_token.txt` em `%LOCALAPPDATA%\sisRUA\`.
  - Recomendação: proteger com **DPAPI** (`ProtectedData`) e rotação controlada.

- **Validação/limites de payload (GeoJSON / OSM)**:
  - Recomendação: limitar tamanho (bytes), número de features e número de pontos por feature para evitar travamentos/DoS local.

- **Logs do plugin em Release + rotação**:
  - Hoje a saída principal vai para o Editor/Debug.
  - Recomendação: log estruturado em `%LOCALAPPDATA%\sisRUA\logs\` (com rotação).

- **Consistência de versão**:
  - Garantir sincronismo automático entre `VERSION.txt`, `PackageContents.xml`, instalador e frontend.

## Plano de produção (roadmap curto)

### Semana 1 (crítico)

- Sincronizar versão automaticamente (ex.: `VERSION.txt` → `PackageContents.xml` + instalador).
- Proteger token persistido (DPAPI).
- Limitar tamanho de payload/arquivo GeoJSON e impor limites de geometria.
- Log estruturado do plugin em `%LOCALAPPDATA%\sisRUA\logs\` com rotação simples.

### Semana 2 (alta)

- Retry/backoff para falhas temporárias ao consultar OSM.
- Melhorar mensagens de erro (com ação sugerida) na UI e no AutoCAD.
- Smoke tests mais completos (com OSM opcional) e CI reforçado.

### Semana 3 (média)

- Persistência simples de jobs (opcional) e métricas básicas no health.
- Documentação/App Store assets (screenshots, descrição, troubleshooting expandido).

## Benchmark (posicionamento)

- **ArcGIS for AutoCAD / Map 3D**: poderosos, mas pesados/caros; sisRUA ganha em simplicidade e foco no fluxo Campo→CAD.
- **Plex.Earth**: foco em imagem/serviços externos; sisRUA ganha em vetores estruturados (vias/layers) e CRS automático.
- **Importadores genéricos**: rápidos mas despadronizados; sisRUA ganha em layers padronizados, CRS e pipeline controlado.

## Observações práticas (suporte)

- “Trusted Folder”: se o AutoCAD ainda não criou o perfil no registro, o instalador não consegue escrever `TRUSTEDPATHS`; o usuário pode adicionar manualmente em:
  - `Options > Files > Trusted Locations`
- GitHub: `sisrua_backend.exe` tende a ser grande; considerar **Git LFS** para reduzir atrito no repositório.

