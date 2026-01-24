# Arquitetura

## Visão geral

O sisRUA é um plugin do AutoCAD (C#) que abre uma UI (React) dentro de uma paleta (WebView2) e usa um backend local (FastAPI) para:

- baixar OSM
- processar GeoJSON
- projetar para UTM/SIRGAS
- retornar um “payload CAD” (linhas em XY) para o C# desenhar direto no ModelSpace

## Componentes

- **AutoCAD / C#**
  - Abre a paleta com WebView2
  - Recebe mensagens da UI (`action`, `data`)
  - Chama endpoints do backend e desenha `Polyline` no ModelSpace

- **Frontend / React**
  - UI em `http://localhost:8000/` (servida pelo FastAPI via `frontend/dist`)
  - Envia mensagens via `window.chrome.webview.postMessage({ action, data })`

- **Backend / FastAPI**
  - APIs em `/api/v1/*`
  - Serve o frontend em `/`

## Fluxo principal (OSM)

1) UI envia `{ action: "GENERATE_OSM", data: { latitude, longitude, radius } }`
2) C# chama `POST /api/v1/prepare/osm`
3) Backend baixa OSM e projeta para UTM/SIRGAS
4) Backend retorna:
   - `crs_out`
   - `features: [{ layer, name, highway, coords_xy: [[x,y], ...] }]`
5) C# cria layers e desenha `Polyline` por feature

## Fluxo principal (GeoJSON)

1) UI envia `{ action: "IMPORT_GEOJSON", data: "<geojson>" }`
2) C# chama `POST /api/v1/prepare/geojson`
3) Backend projeta e retorna `features` com `coords_xy`
4) C# desenha `Polyline` no ModelSpace

## Backend “standalone” (sem Python)

Para produção, o backend pode ser empacotado em um executável:

- `Contents/backend/sisrua_backend.exe`

O C# dá preferência a esse EXE e só usa Python como fallback (dev).

