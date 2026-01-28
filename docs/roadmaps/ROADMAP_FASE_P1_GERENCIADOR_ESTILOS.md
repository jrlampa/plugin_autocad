# ROADMAP SUPLEMENTAR (FUTURO) — FASE P.1 — GERENCIADOR DE LAYERS E ESTILOS AVANÇADO

## Visão da Fase P.1
Capacitar o usuário, especialmente o CAD Manager, com controle total sobre a aparência e organização dos elementos desenhados pelo sisRUA, garantindo 100% de aderência aos padrões de desenho (templates `.dwt`) da empresa e eliminando a necessidade de qualquer ajuste manual de camadas após a importação.

## PRINCÍPIOS ARQUITETURAIS
*   **Integração com Padrões Existentes**: A ferramenta deve permitir o mapeamento para layers e estilos que já existem no desenho do usuário.
*   **Persistência Centralizada**: As configurações de mapeamento devem ser salvas em um arquivo de configuração central, permitindo o compartilhamento e a padronização entre equipes.
*   **Flexibilidade**: O usuário deve poder tanto criar novas layers com propriedades customizadas quanto mapear para layers existentes.

## FASE P.1 — GERENCIADOR DE LAYERS E ESTILOS AVANÇADO
**Objetivo**: Implementar uma interface de gerenciamento onde o usuário pode configurar detalhadamente as propriedades das camadas (nome, cor, tipo de linha, espessura) para cada tipo de feição, ou mapeá-las para camadas já existentes no seu template.

### Entregas Detalhadas

#### 1. Evolução do Esquema de Configuração
*   **Sub-Objetivo**: Expandir o arquivo de configuração de estilos (da FASE 1.5.6) para incluir mais propriedades e opções de mapeamento.
*   **Entregas**:
    *   **Arquivo `drawing_styles.json` (Avançado)**: A estrutura para cada tipo de feição (ex: `highway=residential`) será expandida para incluir:
        *   `target_layer`: O nome da camada a ser usada/criada (editável pelo usuário).
        *   `map_to_existing`: Um booleano. Se `true`, o plugin não criará a camada, apenas usará a `target_layer` se ela já existir.
        *   `layer_color_aci`: Cor (se for para criar a camada).
        *   `linetype`: Nome do tipo de linha (ex: "Continuous", "DASHED").
        *   `lineweight`: Espessura da linha (ex: `LineWeight.LineWeight030`).
        *   `plot_style_name`: Nome do estilo de plotagem.

#### 2. Interface de Gerenciamento de Estilos (Frontend)
*   **Sub-Objetivo**: Criar uma UI robusta para que o usuário configure o mapeamento de estilos.
*   **Entregas**:
    *   **Painel "Gerenciador de Padrões"**: Uma nova seção na UI do sisRUA.
    *   **Lista de Feições**: Exibir uma lista de todos os tipos de feição que o sisRUA pode desenhar (ex: "Rua Residencial", "Poste", "Edificação").
    *   **Controles de Configuração**: Para cada feição na lista, o usuário poderá configurar:
        *   **Nome da Camada de Destino**: Um campo de texto para `target_layer`.
        *   **Mapear para Camada Existente**: Um `checkbox`.
        *   **Propriedades da Nova Camada**: Seletores de cor, tipo de linha e espessura (estes ficariam desabilitados se "Mapear para Camada Existente" estiver marcado).

#### 3. Implementação da Lógica de Desenho Avançada (C#)
*   **Sub-Objetivo**: Fazer com que o plugin C# utilize as novas configurações avançadas.
*   **Entregas**:
    *   **Leitura das Configurações**: `SisRuaSettings.cs` será atualizado para ler a nova estrutura do `drawing_styles.json`.
    *   **Lógica em `SisRuaCommands.cs`**:
        *   A função `GetLayerStyleForFeature` será completamente refatorada.
        *   Ela primeiro verificará a configuração para um tipo de feição.
        *   Se `map_to_existing` for `true`, ela apenas verificará se a `target_layer` existe e a usará. Se não existir, pode retornar um erro ou usar um padrão.
        *   Se `map_to_existing` for `false`, ela criará a `target_layer` (se não existir) e aplicará todas as propriedades configuradas (cor, tipo de linha, espessura, etc.).

### Critérios de Sucesso
*   ✔️ O usuário pode, através de uma UI, mapear um tipo de rua do OSM para um nome de camada de sua escolha.
*   ✔️ O usuário pode definir a cor, o tipo de linha e a espessura para as camadas que serão criadas pelo plugin.
*   ✔️ O usuário pode instruir o plugin a usar uma camada que já existe no desenho, sem tentar criá-la ou modificá-la.
*   ✔️ As configurações são salvas e persistem entre as sessões do AutoCAD.
