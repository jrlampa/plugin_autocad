# Plano de Testes — sisRUA (audit-ready)

## 1) Objetivo

Garantir evidências de que o sisRUA:

- atende requisitos funcionais (OSM/GeoJSON → CAD)
- atende requisitos não-funcionais relevantes (autorização local, robustez, privacidade)
- possui rastreabilidade (requisito → teste → evidência)

## 2) Escopo

- **Inclui**
  - Backend (FastAPI): auth/health/jobs/geojson
  - Frontend (React): UX básica, carregamento, fluxos de drop/preview
  - Plugin AutoCAD: instalação, comando, desenho, camadas, atribuição

- **Exclui (por limitações de automação)**
  - automação completa dentro do AutoCAD (UI WebView2 + desenho) — coberta via testes manuais com evidência

## 3) Estratégia

- **Automatizado (rápido)**
  - Backend: `pytest` (unit + integração leve sem rede)
  - Frontend: `vitest` + Testing Library (com mocks de Leaflet)

- **Manual (funcional + UI/UX)**
  - Roteiros com campos de evidência (screenshot/log)

## 4) Ambientes

- Windows 10/11, AutoCAD 2024/2025/2026
- Node LTS
- Python 3.11+

Registrar execução em: `manual/execution-record-template.md`.

## 5) Critérios de entrada

- Build do plugin (Release)
- `sisrua_backend.exe` presente no bundle (produção)
- `landing/` e docs legais atualizados (quando aplicável)

## 6) Critérios de aceite (saída)

- 100% dos testes automatizados passando
- Testes manuais críticos executados com evidência
- `traceability.csv` preenchida (IDs consistentes)

