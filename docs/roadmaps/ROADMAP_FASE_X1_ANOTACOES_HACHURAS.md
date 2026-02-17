# ROADMAP SUPLEMENTAR (FUTURO) — FASE X.1 — GERAÇÃO AUTOMÁTICA DE ANOTAÇÕES E HACHURAS

## Visão da Fase X.1
Elevar o nível de detalhamento dos desenhos gerados, reduzindo drasticamente o trabalho manual de pós-processamento no AutoCAD. O plugin não apenas desenhará a geometria, mas também a anotará e preencherá de forma inteligente.

## PRINCÍPIOS ARQUITETURAIS
*   **Configurabilidade**: O usuário deve ter controle sobre o que é anotado, os estilos de texto e os padrões de hachura.
*   **Desempenho**: As operações de anotação não devem degradar significativamente o desempenho da importação.
*   **Inteligência de Contexto**: As anotações devem ser posicionadas de forma a evitar sobreposição e garantir a legibilidade.

## FASE X.1 — GERAÇÃO AUTOMÁTICA DE ANOTAÇÕES E HACHURAS
**Objetivo**: Implementar a capacidade de gerar automaticamente anotações de texto (nomes de ruas, IDs de blocos) e hachuras (para calçadas, áreas verdes) associadas às feições desenhadas.

### Entregas Detalhadas

#### 1. Geração de Anotações de Texto para Polilinhas (Ruas)
*   **Sub-Objetivo**: Legendar as ruas com seus nomes.
*   **Entregas**:
    *   **Lógica de Anotação (C#)**: Em `SisRuaCommands.cs`, após desenhar uma polyline, extrair a propriedade `name` da `CadFeature`.
    *   **Criação de `MText`**: Criar um objeto `MText` com o nome da rua.
    *   **Posicionamento Inteligente**: Desenvolver um algoritmo para posicionar o `MText` de forma legível (ex: centralizado ao longo da polyline, curvado se a rua for longa, ou em uma camada dedicada para anotações).
    *   **Estilo de Texto**: Permitir que o usuário configure o estilo de texto (`TextStyle`) e a altura do texto a ser usado, aproveitando as configurações da FASE 1.5.6 (Estilos Configuráveis).

#### 2. Geração de Anotações para Blocos
*   **Sub-Objetivo**: Legendar os blocos inseridos com informações relevantes.
*   **Entregas**:
    *   **Lógica de Anotação (C#)**: Após inserir um bloco, extrair propriedades relevantes da `CadFeature` (ex: `name`, um ID único, ou atributos do `properties`).
    *   **Criação de `MLeader` ou `MText`**: Criar um líder (`MLeader`) apontando para o bloco ou um `MText` próximo a ele.
    *   **Configuração**: Permitir que o usuário escolha quais atributos legendar e o estilo a ser usado.

#### 3. Geração de Hachuras
*   **Sub-Objetivo**: Preencher áreas, como calçadas ou canteiros centrais, com hachuras.
*   **Entregas**:
    *   **Lógica de Detecção de Área (C#)**: Identificar polilinhas fechadas que representam áreas a serem hachuradas. Isso pode ser feito se a lógica de offset (FASE 1.5.6) gerar polilinhas fechadas para as calçadas.
    *   **Criação de `Hatch`**: Criar um objeto `Hatch` para preencher a área.
    *   **Configuração de Padrão e Escala**: Permitir que o usuário configure, nos estilos de desenho (FASE 1.5.6), o padrão de hachura (`PatternName`) e a escala para cada tipo de área (ex: `CALCADA`, `GRAMA`).

### Critérios de Sucesso
*   ✔️ Nomes de ruas são automaticamente desenhados como `MText` no CAD.
*   ✔️ Blocos inseridos são legendados com seus IDs ou nomes.
*   ✔️ Áreas de calçada são preenchidas com um padrão de hachura configurável.
*   ✔️ O usuário pode habilitar/desabilitar e configurar o comportamento das anotações e hachuras.
