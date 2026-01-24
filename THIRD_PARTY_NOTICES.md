# THIRD PARTY NOTICES — sisRUA

Última atualização: 2026-01-24

Este arquivo lista dependências de terceiros conhecidas usadas pelo sisRUA (plugin + frontend + backend).
Para submissão na Autodesk App Store, recomenda-se **confirmar licenças/avisos** gerando um relatório automatizado
no ambiente de build.

## Como gerar uma lista completa (recomendado)

- **Python (backend)**:
  - Crie um venv e instale `sisRUA.bundle/Contents/backend/requirements.txt`
  - Rode uma ferramenta de auditoria de licenças (ex.: `pip-licenses`) e cole aqui o resultado, incluindo textos quando exigido.

- **JavaScript (frontend)**:
  - Rode um gerador de licenças para `package-lock.json` (ex.: `license-checker`/`pnpm licenses`) e copie o relatório.

## Componentes principais (não-exaustivo)

- **Microsoft Edge WebView2 Runtime**
  - Usado para renderizar a UI via WebView2 no Windows.
  - Documentação: `https://learn.microsoft.com/microsoft-edge/webview2/`

- **FastAPI**
  - Backend HTTP local.
  - Site: `https://fastapi.tiangolo.com/`

- **Uvicorn**
  - Servidor ASGI.
  - Site: `https://www.uvicorn.org/`

- **OSMnx / GeoPandas / PyProj / Shapely / Pandas / NumPy / NetworkX**
  - Processamento geoespacial e transformação de coordenadas.
  - Sites:
    - `https://osmnx.readthedocs.io/`
    - `https://geopandas.org/`
    - `https://pyproj4.github.io/pyproj/`
    - `https://shapely.readthedocs.io/`

## Nota
As licenças podem variar por versão. Atualize este arquivo a cada release.

