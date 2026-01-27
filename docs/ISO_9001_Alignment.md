# Alinhamento do Projeto sisRUA com ISO 9001:2015

Este documento visa explicitar como os artefatos e processos do projeto sisRUA se alinham e suportam a certificação ISO 9001:2015, focando nas cláusulas relevantes para o desenvolvimento de software.

## 1. Contexto da Organização (Cláusula 4)

Embora esta cláusula seja amplamente organizacional, o projeto contribui ao definir claramente seu escopo (pipeline Campo → GIS → CAD, offline-first) e suas partes interessadas (usuários, Autodesk, etc.).

## 2. Liderança (Cláusula 5)

A visão e os princípios arquiteturais imutáveis definidos no `ROADMAP OFICIAL DE DESENVOLVIMENTO.txt` demonstram um comprometimento da liderança com a qualidade e a direção estratégica do projeto.

## 3. Planejamento (Cláusula 6)

### 3.1. Ações para Abordar Riscos e Oportunidades (Cláusula 6.1)
*   **Contribuição do Projeto**: O `ROADMAP OFICIAL DE DESENVOLVIMENTO.txt` aborda riscos ao priorizar "custo zero inicial" e "não dependência de nuvem até provar valor", minimizando riscos financeiros e de dependência externa. A abordagem "offline-first" também mitiga riscos de conectividade.
*   **Próximos Passos Sugeridos**: Formalizar um registro de riscos do projeto, identificando, analisando e planejando ações para mitigar riscos técnicos e de implementação.

### 3.2. Objetivos da Qualidade e Planejamento para Alcançá-los (Cláusula 6.2)
*   **Contribuição do Projeto**: O `ROADMAP OFICIAL DE DESENVOLVIMENTO.txt` define objetivos claros para cada fase (ex: "Garantir padronização gráfica desde o início" para FASE 1.5).
*   **Próximos Passos Sugeridos**: Vincular esses objetivos do roadmap a métricas de qualidade mensuráveis e revisá-los periodicamente.

### 3.3. Planejamento de Mudanças (Cláusula 6.3)
*   **Contribuição do Projeto**: O uso do controle de versão Git e o histórico de commits fornecem um registro detalhado das mudanças no código-fonte.
*   **Próximos Passos Sugeridos**: Formalizar um processo para solicitação, revisão e aprovação de mudanças (ex: pull requests com revisões), garantindo que as mudanças sejam rastreadas e avaliadas quanto ao impacto.

## 4. Apoio (Cláusula 7)

### 4.1. Recursos (Cláusula 7.1)
*   **Contribuição do Projeto**: A especificação de ambientes de teste (`qa/test-plan.md`) e ferramentas (Python 3.11+, Node LTS, AutoCAD 2024/2025/2026) define os recursos necessários.

### 4.2. Competência (Cláusula 7.2)
*   **Contribuição do Projeto**: O projeto utiliza tecnologias específicas (C#, Python, JavaScript, AutoCAD API) que exigem competências específicas. A documentação (`ROADMAP`, `qa/`) serve como base de conhecimento.

### 4.3. Conscientização (Cláusula 7.3)
*   **Contribuição do Projeto**: O `qa/README.md` explicita a importância da rastreabilidade e dos artefatos para auditorias.

### 4.4. Comunicação (Cláusula 7.4)
*   **Contribuição do Projeto**: A comunicação do status do projeto é feita através do roadmap e dos resultados dos testes automatizados (CI).

### 4.5. Informação Documentada (Cláusula 7.5)
*   **Criação e Atualização (7.5.2)**: Todos os documentos (código, `ROADMAP`, `requirements.md`, `test-plan.md`, `VERSION.txt`, etc.) são criados e atualizados sob controle de versão (Git).
*   **Controle da Informação Documentada (7.5.3)**:
    *   **Contribuição do Projeto**: O Git garante controle de versão, acesso, recuperação, uso e retenção dos documentos.
    *   **Próximos Passos Sugeridos**: Implementar políticas de backup e recuperação de dados para toda a informação documentada do projeto.

## 5. Operação (Cláusula 8)

### 5.1. Planejamento e Controle Operacional (Cláusula 8.1)
*   **Contribuição do Projeto**: O `ROADMAP OFICIAL DE DESENVOLVIMENTO.txt` e o `qa/test-plan.md` fornecem um plano claro para a operação do desenvolvimento.

### 5.2. Requisitos para Produtos e Serviços (Cláusula 8.2)
*   **Comunicação com o Cliente (8.2.1)**:
    *   **Contribuição do Projeto**: A UI do plugin (`SisRuaPalette.cs`) lida com avisos de privacidade (`MessageBox.Show`) e feedback de progresso (job status).
*   **Determinação dos Requisitos (8.2.2)**:
    *   **Contribuição do Projeto**: O `qa/requirements.md` detalha os requisitos funcionais e não-funcionais (FR/NFR).
*   **Análise Crítica dos Requisitos (8.2.3)**:
    *   **Próximos Passos Sugeridos**: Formalizar o processo de revisão dos requisitos com as partes interessadas para garantir que são adequados, completos e consistentes.

### 5.3. Projeto e Desenvolvimento de Produtos e Serviços (Cláusula 8.3)
Esta é uma cláusula central para o desenvolvimento de software.

*   **Planejamento de Projeto e Desenvolvimento (8.3.2)**:
    *   **Contribuição do Projeto**: O `ROADMAP OFICIAL DE DESENVOLVIMENTO.txt` é a principal evidência deste planejamento, detalhando fases, objetivos, entregas e critérios de sucesso. O `qa/test-plan.md` complementa com a estratégia de testes.
*   **Entradas de Projeto e Desenvolvimento (8.3.3)**:
    *   **Contribuição do Projeto**: `qa/requirements.md` define claramente os FRs e NFRs. Os princípios arquiteturais (`ROADMAP`) também servem como entradas.
*   **Controles de Projeto e Desenvolvimento (8.3.4)**:
    *   **Análises Críticas**: O processo de Pull Request (se usado) e as reuniões de equipe (se documentadas) serviriam como análises.
    *   **Verificação**: Os testes automatizados (backend/frontend em `ci_qa.yml`) e os testes manuais (`qa/manual/`) são as principais evidências de verificação do projeto.
    *   **Validação**: Testes de aceitação (manuais) e feedback de usuários (se documentado) contribuem para a validação.
    *   **Contribuição do Projeto**: A `traceability.csv` (matriz de rastreabilidade) é fundamental para demonstrar o link entre requisitos, testes e validação.
*   **Saídas de Projeto e Desenvolvimento (8.3.5)**:
    *   **Contribuição do Projeto**: O código-fonte, os binários compilados (`.dll`, `.exe`), o bundle de instalação, a UI, as camadas e blocos CAD gerados são todas saídas controladas do projeto. Os documentos de teste e o `TEST_PLAN_V0.1.1_AUTOCAD_COMPAT.md` também são saídas do processo de desenvolvimento.
*   **Controle de Alterações de Projeto e Desenvolvimento (8.3.6)**:
    *   **Contribuição do Projeto**: O histórico de commits do Git é a principal ferramenta para o controle de alterações do código.

### 5.4. Controle de Processos, Produtos e Serviços Fornecidos Externamente (Cláusula 8.4)
*   **Contribuição do Projeto**: A instalação de dependências Python em ambiente virtual (`EnsureVenvAndDependencies` em `SisRuaPlugin.cs`) e o uso de pacotes NuGet são exemplos de controle de serviços/produtos externos.

### 5.5. Produção e Provisão de Serviço (Cláusula 8.5)
*   **Controle de Produção e Provisão de Serviço (8.5.1)**:
    *   **Contribuição do Projeto**: Os scripts de build (`build_release.cmd`, `organizar_projeto.cmd`) e o `.csproj` definem o processo controlado de compilação e empacotamento.
    *   **Próximos Passos Sugeridos**: Formalizar um documento de "Guia de Build/Release" que detalhe todos os passos para a geração de uma release final.
*   **Identificação e Rastreabilidade (8.5.2)**:
    *   **Contribuição do Projeto**: `VERSION.txt`, nomes dos binários (ex: `sisRUA_NET48_ACAD2021.dll`), e o controle de versão do Git garantem identificação e rastreabilidade dos artefatos. A **FASE 1.5.1 (Persistência SQLite)** adiciona rastreabilidade aos projetos salvos via `project_id`.
*   **Propriedade de Clientes ou Provedores Externos (8.5.3)**:
    *   **Contribuição do Projeto**: A gestão de tokens de autenticação (`BackendAuthToken`) e os mecanismos de privacidade (`SisRuaPalette.cs`) visam proteger os dados do usuário. A **FASE 1.5.1 (Persistência SQLite)** garante que os dados de projeto são armazenados localmente sob controle do usuário.
*   **Preservação (8.5.4)**:
    *   **Contribuição do Projeto**: O versionamento Git e o empacotamento em bundles contribuem para a preservação dos produtos.
*   **Atividades Pós-Entrega (8.5.5)**:
    *   **Contribuição do Projeto**: O sistema de logs implementado no plugin auxilia na análise de problemas pós-entrega.
*   **Controle de Mudanças (8.5.6)**:
    *   **Contribuição do Projeto**: Similar ao 6.3, o Git e o processo de PR (se implementado) gerenciam as mudanças no produto após a entrega.

### 5.6. Liberação de Produtos e Serviços (Cláusula 8.6)
*   **Próximos Passos Sugeridos**: Formalizar critérios de liberação (ex: todos os testes críticos PASS, sem bugs P0/P1 abertos) e um registro de liberação.

### 5.7. Controle de Saídas Não Conformes (Cláusula 8.7)
*   **Contribuição do Projeto**: O sistema de logs no plugin (`SisRuaPlugin.cs`, `SisRuaCommands.cs`) e as mensagens de erro na UI (`SisRuaPalette.cs`) ajudam a identificar e reportar saídas não conformes. O registro de incidentes no `execution-record-template.md` também é uma forma de controle.
*   **Próximos Passos Sugeridos**: Formalizar um processo para tratamento de bugs e não conformidades, incluindo análise da causa raiz e ações corretivas/preventivas.

## 6. Avaliação de Desempenho (Cláusula 9)

### 6.1. Monitoramento, Medição, Análise e Avaliação (Cláusula 9.1)
*   **Contribuição do Projeto**: Os testes automatizados (CI) fornecem monitoramento contínuo da qualidade do código. Os logs do plugin permitem a medição do desempenho e erros em tempo de execução.

### 6.2. Auditoria Interna (Cláusula 9.2)
*   **Contribuição do Projeto**: Os artefatos e a organização da pasta `qa/` são projetados para facilitar auditorias internas e externas.

### 6.3. Análise Crítica pela Direção (Cláusula 9.3)
*   **Contribuição do Projeto**: O `ROADMAP OFICIAL DE DESENVOLVIMENTO.txt` serve como um documento de entrada para essas análises.

## 7. Melhoria (Cláusula 10)

### 7.1. Não Conformidade e Ação Corretiva (Cláusula 10.2)
*   **Contribuição do Projeto**: O registro de incidentes nos templates de teste manual e a rastreabilidade ajudam na identificação de não conformidades e no planejamento de ações corretivas.

### 7.2. Melhoria Contínua (Cláusula 10.3)
*   **Contribuição do Projeto**: O próprio `ROADMAP` com suas fases de evolução reflete um ciclo de melhoria contínua do produto.

## Resumo e Próximos Passos

O projeto sisRUA já possui uma base documental e processual notável para o desenvolvimento de software que está fortemente alinhada com as exigências da ISO 9001. Para uma certificação formal, a organização precisaria:
1.  **Integrar** estes artefatos e processos específicos do projeto em um Sistema de Gestão da Qualidade (SGQ) abrangente.
2.  **Documentar** os processos organizacionais que complementam os processos técnicos (ex: gestão de clientes, compras, RH).
3.  **Implementar** e manter um sistema de auditorias internas e análises críticas pela direção.

Este documento (`ISO_9001_Alignment.md`) servirá como um guia para demonstrar a conformidade do projeto com a ISO 9001 durante uma auditoria.
