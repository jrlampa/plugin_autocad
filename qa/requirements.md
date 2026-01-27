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
- **FR-008 — Limpar Dados Locais**: o plugin deve fornecer um comando ou funcionalidade na UI para que o usuário possa apagar todos os dados locais persistidos pelo sisRUA (cache, logs, tokens).
- **FR-009 — Associatividade e Notificação de Alterações**: o plugin deve manter associatividade entre as entidades CAD geradas e os dados de origem (OSM/GeoJSON), notificando o usuário sobre possíveis alterações nos dados de origem e oferecendo a opção de atualização.
- **FR-010 — Guia de Usuário e Documentação de Suporte**: o projeto deve fornecer um guia de usuário abrangente e documentação de suporte para facilitar o uso e a resolução de problemas do plugin.
- **FR-011 — Inserção de Blocos a partir de OSM**: o plugin deve inserir blocos CAD a partir de dados OSM (ex: postes, medidores) com base em tags e mapeamento configurável.
- **FR-012 — Inserção de Blocos a partir de GeoJSON**: o plugin deve inserir blocos CAD a partir de dados GeoJSON com geometria de ponto e metadados de bloco.
- **FR-013 — Padronização Gráfica de Blocos**: os blocos inseridos devem seguir as padronizações definidas (camadas, escala, rotação, etc.), conforme configurado em `blocks_mapping.json`.
- **FR-014 — Persistência de Projeto**: o plugin deve permitir salvar o desenho atual como um projeto no banco de dados SQLite, associado a um `project_id` fornecido ou gerado.
- **FR-015 — Recuperação e Redesenho de Projeto**: o plugin deve permitir listar projetos salvos e redesenhar um projeto selecionado a partir do banco de dados SQLite.

## Não-funcionais (NFR)

- **NFR-001 — Autorização local**: endpoints sensíveis do backend devem exigir token (header `X-SisRua-Token`).
- **NFR-002 — Robustez de payload**: o sistema deve lidar com entradas inválidas sem travar (erro claro, sem crash).
- **NFR-003 — Logs**: backend deve gerar logs locais para suporte (rotacionados).
- **NFR-004 — Privacidade**: sem telemetria por padrão; rede externa apenas quando o usuário solicitar OSM.
- **NFR-005 — Trusted Locations (UX)**: instalação deve reduzir alertas de segurança (“Trusted Folder”) configurando `TRUSTEDPATHS` quando possível.
- **NFR-006 — Integridade dos Dados Persistidos**: os dados de projeto salvos no SQLite (polylines e blocos) devem ser recuperados com todas as suas propriedades íntegras e corresponder ao estado original.

