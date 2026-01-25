# Requisitos (FR/NFR) — sisRUA

Este documento define requisitos **auditáveis** (com IDs) para rastreabilidade.

## Convenções

- **FR-xxx**: requisito funcional
- **NFR-xxx**: requisito não-funcional (segurança, desempenho, confiabilidade, privacidade)
- **EVI-xxx**: evidência esperada (ex.: screenshot, log, relatório)
- **TC-xxx**: caso de teste (automatizado ou manual)

## Funcionais (FR)

- **FR-001 — Autoload**: ao instalar, o sisRUA deve ser carregado automaticamente pelo AutoCAD via `.bundle` (sem `NETLOAD`).
- **FR-002 — Abrir UI**: ao executar o comando `SISRUA`, a paleta deve abrir e renderizar a UI (WebView2).
- **FR-003 — OSM → CAD**: a UI deve permitir solicitar geração via OSM (lat/lon + raio) e o plugin deve desenhar no ModelSpace.
- **FR-004 — GeoJSON → CAD**: o usuário deve poder importar GeoJSON (drag & drop / UI) e desenhar no ModelSpace.
- **FR-005 — CRS**: o backend deve projetar dados de entrada (EPSG:4326) para **SIRGAS 2000 / UTM** automaticamente.
- **FR-006 — Atribuição OSM**: ao usar dados OSM, deve existir atribuição visível (UI) e anotação no DWG.
- **FR-007 — Feedback de progresso (jobs)**: enquanto o backend processa um job, a UI deve exibir progresso/estado e apresentar mensagens de erro claras quando aplicável.

## Não-funcionais (NFR)

- **NFR-001 — Autorização local**: endpoints sensíveis do backend devem exigir token (header `X-SisRua-Token`).
- **NFR-002 — Robustez de payload**: o sistema deve lidar com entradas inválidas sem travar (erro claro, sem crash).
- **NFR-003 — Logs**: backend deve gerar logs locais para suporte (rotacionados).
- **NFR-004 — Privacidade**: sem telemetria por padrão; rede externa apenas quando o usuário solicitar OSM.
- **NFR-005 — Trusted Locations (UX)**: instalação deve reduzir alertas de segurança (“Trusted Folder”) configurando `TRUSTEDPATHS` quando possível.

