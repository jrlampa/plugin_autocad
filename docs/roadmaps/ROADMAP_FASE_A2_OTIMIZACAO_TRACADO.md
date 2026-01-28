# ROADMAP SUPLEMENTAR (FUTURO) — FASE A.2 — ANÁLISE PREDITIVA E OTIMIZAÇÃO DE TRAÇADO DE VIAS

## Visão da Fase A.2
Levar o sisRUA ao próximo nível de "Inteligência Artificial de Design", transformando-o de uma ferramenta que apenas digitaliza o que existe para uma ferramenta que ativamente **sugere e otimiza novas soluções**. O plugin se tornará um parceiro de design para o engenheiro ou urbanista, explorando possibilidades e otimizando para múltiplos critérios.

## PRINCÍPIOS ARQUITETURAIS
*   **Design Assistido, não Automatizado**: A IA sugere opções; o projetista toma a decisão final. O sistema é uma ferramenta de apoio, não um substituto.
*   **Baseado em Múltiplos Critérios**: A otimização deve levar em conta uma combinação de fatores: topografia, custo de construção estimado, impacto ambiental e restrições de design.
*   **Feedback Visual e Interativo**: O usuário deve poder ver as diferentes opções de traçado, comparar suas métricas e ajustar os pesos de cada critério de otimização.

## FASE A.2 — ANÁLISE PREDITIVA E OTIMIZAÇÃO DE TRAÇADO DE VIAS
**Objetivo**: Implementar uma funcionalidade onde o usuário define um ponto inicial e final para uma nova via, e um modelo de IA sugere múltiplos traçados otimizados com base em critérios como topografia, custo e restrições.

### Entregas Detalhadas

#### 1. Coleta e Preparação de Dados para Otimização
*   **Sub-Objetivo**: Reunir todas as camadas de dados necessárias para o algoritmo de otimização.
*   **Entregas**:
    *   **Dados de Terreno (MDE)**: Utilizar os dados de elevação da FASE 2 (Relevo) para calcular declividades ao longo de possíveis traçados.
    *   **Dados de Custo**: Criar um modelo de custo simplificado, onde cada pixel do mapa tem um "custo de passagem". Por exemplo:
        *   Áreas com alta declividade têm custo alto.
        *   Áreas de proteção ambiental (FASE E.1) têm custo "infinito" ou muito alto.
        *   Edificações existentes (FASE 1.5.7) têm custo muito alto.
    *   **"Cost-Surface Raster"**: Gerar um raster intermediário onde o valor de cada pixel é o custo para construir naquele local.

#### 2. Implementação do Algoritmo de Otimização (Pathfinding)
*   **Sub-Objetivo**: Desenvolver o núcleo do motor de sugestão de traçados.
*   **Entregas**:
    *   **Pesquisa de Algoritmos**: Avaliar algoritmos de "pathfinding" (encontrar caminhos) que funcionam em "cost surfaces", como o Algoritmo de Dijkstra ou A* (A-star).
    *   **Implementação no Backend (Python)**:
        *   Criar um novo endpoint de API, ex: `/api/v1/optimize_path`, que recebe pontos de início/fim e os pesos dos critérios de otimização.
        *   O backend executa o algoritmo de pathfinding sobre o "cost-surface raster" para encontrar, por exemplo, os 3 caminhos de menor custo total.
    *   **Múltiplos Cenários**: O algoritmo pode ser executado múltiplas vezes com diferentes pesos (ex: um caminho otimizado para menor custo, outro para menor declividade) para gerar alternativas.

#### 3. Interface do Usuário para Otimização
*   **Sub-Objetivo**: Criar uma interface intuitiva para o usuário definir o problema e analisar os resultados.
*   **Entregas**:
    *   **Modo "Otimizar Traçado" na UI**: Um novo modo de interação no frontend.
    *   **Definição de Início/Fim**: O usuário clica em dois pontos no mapa para definir o início e o fim da via desejada.
    *   **Painel de Otimização**: Exibir um painel onde o usuário pode ajustar sliders para os pesos dos critérios:
        *   Peso do Custo de Construção (declividade, etc.)
        *   Peso do Impacto Ambiental
    *   **Visualização dos Resultados**:
        *   Os traçados sugeridos são exibidos como linhas de preview no mapa.
        *   Ao passar o mouse sobre um traçado, exibir suas métricas: comprimento, custo estimado, declividade máxima.

#### 4. Integração com o Fluxo de Desenho
*   **Sub-Objetivo**: Permitir que o usuário transforme um traçado sugerido em um elemento de projeto.
*   **Entregas**:
    *   **Botão "Selecionar Traçado"**: Após revisar as opções, o usuário pode selecionar um dos traçados.
    *   **Conversão para GeoJSON**: O traçado selecionado é convertido para um `GeoJSON LineString`.
    *   **Importação para o CAD**: O GeoJSON é então enviado para o pipeline de importação existente do sisRUA para ser desenhado no AutoCAD.

### Critérios de Sucesso
*   ✔️ O usuário pode definir um ponto de início e fim no mapa para uma nova via.
*   ✔️ O sistema gera e exibe um ou mais traçados otimizados entre os pontos.
*   ✔️ O usuário pode visualizar e comparar as métricas básicas de cada traçado sugerido.
*   ✔️ O usuário pode selecionar um dos traçados para ser desenhado no AutoCAD.
