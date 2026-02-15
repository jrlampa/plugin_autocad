# Como cada profissional analisa o projeto sisRUA

Este documento descreve **como cada perfil analisa** o projeto: o que cada um observa, que critérios usa, quais pontos fortes e fracos identifica e que tipo de conclusão tira. Complementa o guia [PERFIS_PROFISSIONAIS.md](PERFIS_PROFISSIONAIS.md) (que foca em *como acompanhar* o projeto).

---

## 1. Dev Sênior

**O que analisa:** Coerência arquitetural, qualidade das APIs, acoplamento entre C#, Python e React, tratamento de erros e decisões técnicas documentadas.

**Critérios típicos:**

- Clareza dos contratos (schema, versionamento, estabilidade).
- Separação de responsabilidades (backend = processamento; plugin = orquestração e CAD; frontend = UI).
- Existência de ADRs para decisões relevantes.
- Testes automatizados nas camadas críticas (backend, integração).

**Análise aplicada ao sisRUA:**

| Aspecto | Observação |
|--------|------------|
| **Arquitetura** | Três camadas bem definidas (plugin C#, FastAPI, React); fluxo OSM/GeoJSON documentado em [ARQUITETURA.md](ARQUITETURA.md). Pontos de integração claros: `postMessage` UI→C#, HTTP C#→API. |
| **API** | FastAPI com `/api/v1/*`, OpenAPI em `/docs`; [API_STABILITY_POLICY.md](API_STABILITY_POLICY.md) define garantias; schemas em `schema/v1/` ajudam consistência. |
| **Plugin** | Multi-target (net48 + net8.0-windows) para compatibilidade AutoCAD 2021+; Engine abstrai desenho (testável com mock). |
| **Riscos** | Dois consumidores da mesma API (React e C#): mudanças de contrato exigem alinhamento; plugin e backend usam SQLite em caminhos que podem divergir (backend em Python, plugin em C#) — convenção de path e migrações precisam estar alinhadas. |

**Conclusão típica:** Projeto com boa base (arquitetura clara, API versionada, ADRs). Manter disciplina de contrato (schema + policy) e alinhar modelo de dados (SQLite) entre backend e plugin.

---

## 2. Fullstack Sênior

**O que analisa:** Fluxo ponta a ponta (UI → API → processamento → desenho), consistência de dados entre camadas, tratamento de loading/erro e evolução alinhada de frontend e backend.

**Critérios típicos:**

- Uma ação na UI resulta em chamada de API e efeito visível no CAD (ou mensagem clara de erro).
- Jobs assíncronos com polling e feedback na UI (progresso, conclusão, falha).
- Contratos (request/response) compartilhados e usados por frontend e plugin.
- Experiência em cenários de falha (backend indisponível, timeout, dados inválidos).

**Análise aplicada ao sisRUA:**

| Aspecto | Observação |
|--------|------------|
| **Fluxo E2E** | UI envia ações (ex.: GENERATE_OSM, IMPORT_GEOJSON); C# recebe em `SisRuaPalette` e chama backend; resposta vira desenho via `SisRuaCommands` + Engine. Fluxo descrito na arquitetura e implementado de forma coerente. |
| **Jobs** | Backend expõe jobs (prepare OSM/GeoJSON); frontend usa `JobOverlay` com status (queued/processing/completed/failed) e barra de progresso; C# faz polling em `RunPrepareJobAsync`. Alinhamento entre API de jobs e UI. |
| **Contratos** | `schema/v1/` (PrepareResponse, JobStatusResponse, etc.) serve como referência; frontend e C# consomem os mesmos endpoints e estruturas. |
| **Resiliência** | App.jsx faz health check do backend; `LoadingScreen` e estado de erro; `ErrorBoundary` e serviços como `ResilienceService` indicam preocupação com falhas. |
| **Riscos** | Duplicação de lógica de chamada (api.js no frontend e HttpClient no C#): evolução do contrato exige atualizar ambos; testes E2E no AutoCAD são manuais (Playwright condicional no CI). |

**Conclusão típica:** Fluxo ponta a ponta bem desenhado e com feedback de jobs. Manter sincronia entre frontend e plugin ao evoluir contratos e investir em automação E2E onde possível.

---

## 3. Frontend Sênior / Especialista em UI-UX

**O que analisa:** Jornadas do usuário, consistência visual, acessibilidade, estados de loading/erro/vazio, clareza das mensagens e aderência aos requisitos (FR/NFR).

**Critérios típicos:**

- Cada requisito funcional (FR) mapeável para um fluxo na UI.
- Feedback imediato e compreensível (progresso, sucesso, erro).
- Paleta utilizável em diferentes tamanhos (WebView2).
- Tratamento de estados extremos (sem backend, dados vazios, arquivo inválido).

**Análise aplicada ao sisRUA:**

| Aspecto | Observação |
|--------|------------|
| **Requisitos** | [qa/requirements.md](../qa/requirements.md) traz FRs (ex.: FR-002 UI, FR-003/004 OSM/GeoJSON, FR-007 progresso de job); componentes como `JobOverlay`, `MapView`, `Sidebar`, `useFileProcessing` cobrem esses fluxos. |
| **Feedback de job** | `JobOverlay` mostra status (Aguardando/Processando/Concluído), mensagem e barra de progresso; estados de erro (failed) com ícone e estilo distinto. Atende FR-007. |
| **Estados** | `LoadingScreen` no carregamento; health check do backend; `Toast` e estado de erro global; drag-and-drop com preview (useFileProcessing). Há preocupação com feedback. |
| **Design** | Uso de Tailwind; componentes com classes semânticas (estados de sucesso/erro/loading); lazy load de MapView e AiAssistant para TTI. |
| **Riscos** | Documentação explícita de acessibilidade (teclado, screen readers) não aparece nos arquivos analisados; testes manuais de UAT e evidências em [qa/manual/](../qa/manual/) são essenciais para validar UX no AutoCAD. |

**Conclusão típica:** UI alinhada aos FRs principais e com boa preocupação com loading e erro. Reforçar acessibilidade e documentar padrões de UX para a paleta; manter roteiros manuais e evidências atualizados.

---

## 4. DevOps / QA

**O que analisa:** Pipelines de CI/CD, cobertura de testes, segurança (SAST/SCA), rastreabilidade requisito→teste→evidência e critérios de release.

**Critérios típicos:**

- CI em todo push/PR; QA (testes + segurança) em branch principal ou em demanda.
- Artefatos de teste (JUnit, coverage) e de segurança (Bandit, pip-audit) gerados e opcionalmente enviados a SonarCloud.
- Plano de testes e requisitos com IDs para rastreabilidade.
- Release definido (build do plugin, bundle com backend, instalador).

**Análise aplicada ao sisRUA:**

| Aspecto | Observação |
|--------|------------|
| **CI** | [.github/workflows/ci.yml](../.github/workflows/ci.yml): backend (pytest, coverage) e frontend (lint, vitest, build); Python 3.10, Node 20; artefatos de coverage. |
| **QA** | [.github/workflows/ci_qa.yml](../.github/workflows/ci_qa.yml): Bandit (SAST), pip-audit (SCA), pytest com JUnit e coverage, vitest com JUnit e coverage; Playwright E2E condicional; SonarCloud com fontes backend/frontend/plugin. Pipeline completo para qualidade e segurança. |
| **Plano de testes** | [qa/test-plan.md](../qa/test-plan.md) define escopo (backend, frontend, plugin), estratégia (automatizado vs manual), ambientes e critérios de entrada/saída; [qa/requirements.md](../qa/requirements.md) com FR/NFR auditáveis. |
| **Evidências** | [qa/manual/](../qa/manual/) com template de registro de execução; menção a traceability e evidências no test-plan. |
| **Release** | [installer/](../installer/) (Inno Setup); build do plugin em Release; bundle com backend EXE como critério de entrada. |
| **Riscos** | Plugin C# não roda no CI (Linux); testes do plugin dependem de ambiente Windows + AutoCAD ou de testes unitários/mock; cobertura real do fluxo completo depende de testes manuais e evidências. |

**Conclusão típica:** Pipeline de QA bem estruturado (SAST, SCA, testes, SonarCloud). Limitação principal é a ausência de execução do plugin no CI; manter testes manuais e evidências bem documentados e rastreáveis.

---

## 5. Especialista em Database e SQL

**O que analisa:** Modelo de dados, migrações, índices, integridade referencial, uso de SQLite/GeoPackage e consistência entre backend (Python) e plugin (C#).

**Critérios típicos:**

- Esquema versionado e migrações não destrutivas (ADD/CREATE).
- Índices alinhados às queries (filtros por project_id, feature_type, etc.).
- Um único arquivo de DB ou política clara de uso (quem escreve onde).
- Compatibilidade com GeoPackage quando aplicável.

**Análise aplicada ao sisRUA:**

| Aspecto | Observação |
|--------|------------|
| **Backend** | [database.py](../src/backend/backend/core/database.py): SQLite em `%LOCALAPPDATA%/sisRUA/projects.db`, WAL; tabelas GeoPackage (`gpkg_spatial_ref_sys`, `gpkg_contents`, `gpkg_geometry_columns`) para compatibilidade. |
| **Migrações** | [migrations.py](../src/backend/backend/core/migrations.py): CURRENT_VERSION = 3; migrações com CREATE INDEX e ALTER TABLE ADD COLUMN; tabela `schema_version`; tratamento de “already exists” para idempotência. Boa prática para evolução do esquema. |
| **Índices** | Índices em `CadFeatures(project_id)`, `(feature_type)`, `(project_id, feature_type)`; alinhados a consultas por projeto e tipo. |
| **Plugin (C#)** | [ProjectRepository.cs](../src/plugin/ProjectRepository.cs): mesmo path de DB (LocalApplicationData/sisRUA/projects.db); cria tabelas `Projects` e `CadFeatures` (e gpkg_*) com CREATE TABLE IF NOT EXISTS; colunas compatíveis com o uso (project_id, project_name, creation_date, crs_out, total_mileage_km; feature_type, layer, coords_xy_json, etc.). |
| **Riscos** | Duas implementações de “criação de tabelas” (backend em Python, plugin em C#): evolução do esquema (novas colunas, índices) precisa ser replicada ou centralizada; migrações formais estão no backend — o plugin pode rodar primeiro e criar esquema base; versioning (optimistic locking) existe no backend (coluna `version` em Projects); garantir que o plugin respeite isso ao atualizar. |

**Conclusão típica:** Modelo e migrações no backend estão bem organizados; uso de SQLite e GeoPackage é coerente. Principal ponto de atenção: evolução do esquema e migrações precisam ser únicas ou sincronizadas entre Python e C#, e o plugin deve respeitar a política de versioning e índices.

---

## Resumo: o que cada perfil prioriza na análise

| Perfil | Foco da análise | Principal ponto de atenção |
|--------|------------------|----------------------------|
| Dev Sênior | APIs, contratos, arquitetura, ADRs | Alinhar contrato e uso de SQLite entre C# e Python |
| Fullstack Sênior | Fluxo E2E, jobs, resiliência | Sincronizar frontend e plugin em mudanças de API; E2E |
| Frontend UI/UX | Jornadas, feedback, acessibilidade | Acessibilidade e documentação de UX na paleta |
| DevOps/QA | CI, testes, SAST/SCA, evidências | Plugin não roda no CI; evidências manuais e rastreabilidade |
| DB/SQL | Esquema, migrações, índices, consistência | Uma única fonte de verdade para esquema e migrações (backend + plugin) |

Cada perfil usa esse tipo de análise para avaliar maturidade, riscos e próximos passos do projeto, em conjunto com o guia [PERFIS_PROFISSIONAIS.md](PERFIS_PROFISSIONAIS.md).
