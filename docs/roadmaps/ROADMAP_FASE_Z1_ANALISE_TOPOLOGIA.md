# ROADMAP SUPLEMENTAR (FUTURO) — FASE Z.1 — ANÁLISE DE TOPOLOGIA E CONECTIVIDADE DE REDE

## Visão da Fase Z.1
Adicionar uma camada de "inteligência espacial" ao backend, permitindo que o sisRUA não apenas desenhe linhas, mas entenda como elas se conectam. Isso abre portas para a automação de tarefas de limpeza de desenhos e análises de rede, gerando um resultado no CAD que é mais limpo, preciso e analiticamente útil.

## PRINCÍPIOS ARQUITETURAIS
*   **Processamento no Backend**: A análise topológica é uma tarefa de processamento de dados GIS e deve residir no backend Python, que já possui as ferramentas necessárias (ex: GeoPandas, Shapely).
*   **Dados Enriquecidos**: O resultado da análise deve ser adicionado como metadados às `CadFeature`s enviadas ao plugin C#, em vez de apenas alterar a geometria. Isso dá ao plugin mais contexto para tomar decisões de desenho.
*   **Configurável**: O usuário deve poder habilitar ou desabilitar as análises topológicas, pois elas podem adicionar tempo de processamento.

## FASE Z.1 — ANÁLISE DE TOPOLOGIA E CONECTIVIDADE DE REDE
**Objetivo**: Implementar algoritmos no backend Python para analisar a topologia da rede de ruas (interseções, conectividade) e usar essa informação para automatizar a limpeza do desenho e enriquecer os dados enviados ao CAD.

### Entregas Detalhadas

#### 1. Detecção Automática de Interseções
*   **Sub-Objetivo**: Identificar todos os pontos onde duas ou mais ruas se cruzam.
*   **Entregas**:
    *   **Lógica de Detecção (Python)**: No backend (`api.py`), após carregar os dados do OSM ou GeoJSON, usar bibliotecas como GeoPandas/Shapely para calcular os pontos de interseção de todas as geometrias de `LineString`.
    *   **Geração de `CadFeature` de Ponto**: Para cada interseção encontrada, gerar uma nova `CadFeature` do tipo `Point` com um atributo especial (ex: `"feature_subtype": "intersection"`).
    *   **Benefício**: Isso permitiria, em fases futuras, a inserção automática de blocos específicos para cruzamentos (ex: sinalização, caixas de passagem).

#### 2. Limpeza de Geometria em Interseções (Snapping e Trimming)
*   **Sub-Objetivo**: Corrigir pequenas imprecisões em cruzamentos, onde as linhas quase se tocam, mas não exatamente.
*   **Entregas**:
    *   **Algoritmo de Snapping (Python)**: Implementar uma lógica que, dentro de uma certa tolerância, "puxe" os vértices finais de linhas próximas para o ponto de interseção exato.
    *   **Algoritmo de Trimming (Opcional)**: Desenvolver uma lógica para aparar (trim) as linhas nos cruzamentos, evitando que uma linha "atravesse" a outra desnecessariamente. Isso já é parcialmente resolvido pela FASE 1.5.2 (Limpeza de Geometria), mas pode ser aprimorado com uma análise topológica formal.

#### 3. Identificação de Conectividade e "Nós" da Rede
*   **Sub-Objetivo**: Construir um grafo lógico da rede de ruas para entender a conectividade.
*   **Entregas**:
    *   **Construção do Grafo (Python)**: Usar bibliotecas como `networkx` em conjunto com os dados do GeoPandas para criar um grafo onde as interseções são os "nós" (nodes) e os segmentos de rua são as "arestas" (edges).
    *   **Enriquecimento dos Dados**: Adicionar, às propriedades das `CadFeature`s, informações de conectividade, como `start_node_id` e `end_node_id`.
    *   **Benefício**: Essa estrutura de dados é a base para qualquer análise de rede futura, como:
        *   Análise de fluxo.
        *   Detecção de rotas.
        *   Identificação de "becos sem saída" (dead ends), que podem ter regras de desenho diferentes.

### Critérios de Sucesso
*   ✔️ O backend identifica corretamente os pontos de interseção na rede de ruas.
*   ✔️ O desenho gerado no CAD exibe cruzamentos de ruas mais limpos e precisos.
*   ✔️ O JSON de `CadFeature`s enviado para o C# contém metadados adicionais sobre a topologia (ex: se um ponto é uma interseção).
*   ✔️ A análise topológica pode ser habilitada ou desabilitada pelo usuário.
