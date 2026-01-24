# Uso no AutoCAD

## Abrir a interface

1) Abra o AutoCAD
2) Digite o comando: `SISRUA`
3) A paleta do sisRUA abre com a UI (WebView2)

## Gerar ruas via OSM

1) Escolha um ponto/coords no mapa
2) Ajuste o raio (m)
3) Clique em **Gerar Projeto (OSM)**

Resultado:

- O plugin chama `POST /api/v1/prepare/osm`
- O AutoCAD desenha **polylines** no ModelSpace em metros, em layers como `SISRUA_OSM_VIAS`

## Importar GeoJSON

Opções:

- **Arrastar arquivo** `.geojson/.json` na paleta do sisRUA
- Ou carregar na UI e clicar em **IMPORTAR PARA O AUTOCAD**

Resultado:

- O plugin chama `POST /api/v1/prepare/geojson`
- O AutoCAD desenha **polylines** no ModelSpace, usando `properties.layer` (quando existir)

## Observações

- CRS de entrada: **EPSG:4326** (lat/lon)
- CRS de saída (automático): **SIRGAS 2000 / UTM** (ex.: `EPSG:31984`)

