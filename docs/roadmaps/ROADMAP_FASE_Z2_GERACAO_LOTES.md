# ROADMAP SUPLEMENTAR (FUTURO) — FASE Z.2 — GERAÇÃO DE LOTES E PARCELAMENTO SIMPLIFICADO

## Visão da Fase Z.2
Capacitar o sisRUA com funcionalidades de desenho urbano generativo, permitindo a criação e exploração rápida de cenários de parcelamento de solo a partir de um traçado viário, automatizando uma das tarefas mais trabalhosas e iterativas do urbanismo e do design de loteamentos.

## PRINCÍPIOS ARQUITETURAIS
*   **Processamento Paramétrico**: A geração de lotes será baseada em parâmetros definidos pelo usuário (área mínima, testada mínima, etc.).
*   **Iteração Rápida**: A ferramenta deve permitir que o usuário teste diferentes configurações de parcelamento de forma rápida e visual.
*   **Foco no Desenho Conceitual**: O objetivo não é criar um projeto de parcelamento legalmente perfeito, mas sim uma ferramenta de estudo de viabilidade e desenho conceitual de alta velocidade.

## FASE Z.2 — GERAÇÃO DE LOTES E PARCELAMENTO SIMPLIFICADO
**Objetivo**: Implementar uma ferramenta que, a partir de um bloco de ruas fechado (um quarteirão), gere automaticamente uma subdivisão de lotes com base em regras e parâmetros definidos pelo usuário.

### Entregas Detalhadas

#### 1. Identificação de Quarteirões (Polígonos Fechados)
*   **Sub-Objetivo**: Desenvolver a capacidade de identificar áreas fechadas formadas pela rede de ruas.
*   **Entregas**:
    *   **Lógica de Detecção de Polígonos (Python)**: No backend, após a análise topológica (FASE Z.1), usar algoritmos de teoria dos grafos (`networkx`) ou GIS (`shapely.ops.polygonize`) para identificar todos os polígonos fechados que representam quarteirões.
    *   **Geração de `CadFeature` de Área**: Enviar esses quarteirões para o frontend como `CadFeature`s do tipo `Polygon`, com um atributo especial (ex: `"feature_subtype": "block"`).

#### 2. Interface do Usuário para Parcelamento
*   **Sub-Objetivo**: Criar uma UI para que o usuário possa selecionar um quarteirão e definir os parâmetros de parcelamento.
*   **Entregas**:
    *   **Seleção de Quarteirão na UI (Frontend)**: Permitir que o usuário clique em um quarteirão no mapa para selecioná-lo para parcelamento.
    *   **Painel de Parâmetros**: Ao selecionar um quarteirão, exibir um painel com os seguintes parâmetros:
        *   **Área Mínima do Lote** (ex: 250 m²).
        *   **Testada (Frente) Mínima do Lote** (ex: 10 m).
        *   **Profundidade Máxima do Lote** (ex: 40 m).
        *   **Opções de Layout**: "Grid Simples", "Espinha de Peixe", etc.
    *   **Botão "Gerar Lotes"**: Um botão para acionar o processo de geração.

#### 3. Algoritmo de Geração de Lotes (Backend)
*   **Sub-Objetivo**: Desenvolver o núcleo da lógica de parcelamento paramétrico.
*   **Entregas**:
    *   **Novo Endpoint de API (Python)**: Criar um novo endpoint no backend (ex: `/api/v1/subdivide_block`) que recebe a geometria do quarteirão e os parâmetros de parcelamento.
    *   **Algoritmo de Subdivisão**: Implementar o algoritmo que "fatia" o polígono do quarteirão em lotes menores, tentando respeitar os parâmetros definidos. Este é o maior desafio técnico da fase. Pode começar com uma abordagem simples (divisão em grid retangular) e evoluir.
    *   **Retorno de GeoJSON**: O endpoint retornará um GeoJSON contendo as geometrias dos novos lotes gerados.

#### 4. Visualização e Desenho dos Lotes
*   **Sub-Objetivo**: Exibir os lotes gerados no mapa e desenhá-los no AutoCAD.
*   **Entregas**:
    *   **Preview no Frontend**: O frontend receberá o GeoJSON dos lotes e os exibirá no mapa para aprovação do usuário.
    *   **Desenho no CAD (C#)**: Uma vez aprovado, o GeoJSON dos lotes será enviado ao plugin C# (via `IMPORT_GEOJSON`), que desenhará cada lote como uma `Polyline` fechada em uma camada dedicada (ex: "Lotes").
    *   **Anotação de Lotes (Opcional, link com FASE X.1)**: Automaticamente legendar cada lote com seu número e área calculada.

### Critérios de Sucesso
*   ✔️ O sistema identifica automaticamente os quarteirões formados pelas ruas.
*   ✔️ O usuário pode selecionar um quarteirão e definir parâmetros básicos de parcelamento.
*   ✔️ O backend gera uma subdivisão de lotes que respeita (ou tenta se aproximar) dos parâmetros.
*   ✔️ Os lotes gerados são exibidos no mapa de preview e podem ser desenhados no AutoCAD.
