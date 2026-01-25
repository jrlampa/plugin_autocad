# Registro de Execução de Testes (template — audit-ready)

> Objetivo: deixar **reprodutível** o “o que foi testado”, “em que ambiente”, “com quais binários”, e “quais evidências comprovam”.
> Armazenamento recomendado (não versionar): `qa/out/manual/<RUN_ID>/`

## Identificação

- **Produto**: sisRUA
- **RUN_ID**: (ex.: `20260125_1530_BRT_Jonatas-PC`)
- **Versão do produto**: (ex.: `0.1.0` — `VERSION.txt` ou versão do instalador)
- **Commit (fonte)**: (ex.: `git rev-parse --short=12 HEAD`, ou `N/A` se testou apenas release)
- **Branch/tag (fonte)**: (opcional)
- **Data/hora início**: (local)
- **Data/hora fim**: (local)
- **Responsável**: (nome)
- **Revisor**: (opcional)

## Proveniência (o que foi testado)

- **Origem do build**: release oficial / build local / build de CI
- **Nome do artefato**: (ex.: `sisRUA-Installer-0.1.0.exe`)
- **Pasta do RUN**: `qa/out/manual/<RUN_ID>/`
- **Evidências nesta execução**:
  - **Screenshots**: `qa/out/manual/<RUN_ID>/evidence/`
  - **Logs**: `qa/out/manual/<RUN_ID>/logs/`
  - **DWGs/exports**: `qa/out/manual/<RUN_ID>/artifacts/`

## Ambiente

- **SO**: Windows (versão/build) + idioma/região
- **AutoCAD/Civil 3D**: versão (2024/2025/2026) + build
- **.NET Desktop Runtime**: versão (se aplicável)
- **WebView2 Runtime**: versão
- **Máquina**: CPU/RAM/GPU (resumo)
- **Rede**: online/offline; proxy; firewall

## Artefatos sob teste (identificação por hash)

> Preencha **caminho completo** (quando possível) + **SHA-256**. Isso elimina ambiguidade em auditoria.

| Item | Caminho/Nome | Versão (se aplicável) | SHA-256 | Observações |
|---|---|---|---|---|
| Instalador (EXE) |  |  |  |  |
| Bundle (`sisRUA.bundle`) |  |  | (se aplicável, ver comando abaixo) |  |
| Backend (`sisrua_backend.exe`) |  |  |  |  |
| `layers.json` |  |  |  |  |
| `mapeamento.json` |  |  |  |  |
| `prancha.dwg` |  |  |  |  |

### Como coletar SHA-256 (PowerShell)

Arquivo único:

```powershell
Get-FileHash -Algorithm SHA256 "C:\caminho\para\arquivo.ext" | Format-List
```

Pasta (hash de todos os arquivos; útil para um bundle):

```powershell
Get-ChildItem -Recurse -File "C:\ProgramData\Autodesk\ApplicationPlugins\sisRUA.bundle" |
  Get-FileHash -Algorithm SHA256 |
  Sort-Object Path |
  Format-Table -Auto
```

> Dica: salve também a saída em `qa/out/manual/<RUN_ID>/artifacts-under-test.sha256.txt`.

## Execução (checklist)

> Marque os casos executados e registre **o nome dos arquivos de evidência** gerados.

- [ ] **TC-MAN-000** — Preparação do RUN (pasta + template + hashes)
- [ ] **TC-MAN-001** — Instalação e autoload do bundle
- [ ] **TC-MAN-002** — Abertura da paleta (UI)
- [ ] **TC-MAN-003** — Gerar OSM e desenhar vias
- [ ] **TC-MAN-004** — Importar GeoJSON e desenhar
- [ ] **TC-MAN-005** — Atribuição OSM no DWG
- [ ] **TC-MAN-006** — Logs do backend (produção)
- [ ] **TC-MAN-007** — Privacidade / rede
- [ ] **TC-MAN-008** — Trusted Locations (redução de popup)

## Checklist mínimo de evidências (por execução)

- [ ] **Print do comando disponível** (`SISRUA` no prompt) — `TC-MAN-001_*`
- [ ] **Print da paleta/UI renderizada** — `TC-MAN-002_*`
- [ ] **Print do ModelSpace com resultado** (OSM e/ou GeoJSON) — `TC-MAN-003_*`, `TC-MAN-004_*`
- [ ] **Print do gerenciador de layers** (layers criados/cores) — `TC-MAN-003_*`, `TC-MAN-004_*`
- [ ] **Print do texto de atribuição OSM** — `TC-MAN-005_*`
- [ ] **Cópia de logs** (ex.: `%LOCALAPPDATA%\sisRUA\logs\backend.log`) — `TC-MAN-006_*`
- [ ] **DWG de saída (amostra)** salvo — `artifacts/*.dwg` (opcional mas recomendado)

## Evidências anexadas (lista)

> Padrão recomendado de nome: `<TC-ID>_<o-que-e>_<YYYYMMDD-HHMM>.png` / `.txt` / `.log` / `.dwg`

- (ex.: `qa/out/manual/<RUN_ID>/evidence/TC-MAN-003_modelspace_20260125-1542.png`)
- (ex.: `qa/out/manual/<RUN_ID>/logs/backend.log`)
- (ex.: `qa/out/manual/<RUN_ID>/artifacts/result_osm.dwg`)

## Incidentes / desvios

- **ID**: (bug/issue)
- **Descrição**:
- **Passos p/ reproduzir**:
- **Evidência**:

## Resultado

- **Status**: PASS / FAIL / PARTIAL
- **Observações**:

