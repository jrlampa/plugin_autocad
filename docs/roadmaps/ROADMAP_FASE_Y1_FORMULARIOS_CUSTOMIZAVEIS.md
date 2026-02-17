# ROADMAP SUPLEMENTAR (FUTURO) — FASE Y.1 — FORMULÁRIOS DE COLETA CUSTOMIZÁVEIS

## Visão da Fase Y.1
Transformar o "App Offline de Campo" (previsto na FASE 4) de uma ferramenta de coleta de dados com propósito fixo em uma plataforma de levantamento de campo flexível e adaptável, permitindo que as equipes de campo coletem exatamente os dados de que precisam para qualquer tipo de projeto de infraestrutura.

## PRINCÍPIOS ARQUITETURAIS
*   **Configuração via JSON**: A estrutura dos formulários será definida em um arquivo JSON, facilitando a criação e o compartilhamento de templates.
*   **Flexibilidade de Tipos de Dados**: O sistema deve suportar tipos de dados comuns, como texto, números, listas de seleção, caixas de seleção (booleano) e fotos.
*   **Validação de Dados**: Incorporar regras de validação simples (ex: campo obrigatório) para melhorar a qualidade dos dados coletados.

## FASE Y.1 — FORMULÁRIOS DE COLETA CUSTOMIZÁVEIS
**Objetivo**: Permitir que os usuários definam seus próprios formulários para a coleta de dados no "App Offline de Campo", especificando os tipos de feições a serem coletadas e os atributos de cada uma.

### Entregas Detalhadas

#### 1. Definição do Esquema de Formulários
*   **Sub-Objetivo**: Projetar um esquema JSON que descreva a estrutura de um formulário de coleta.
*   **Entregas**:
    *   **Arquivo `forms.json`**: Um arquivo de configuração que define os formulários.
    *   **Estrutura do Esquema**:
        *   Uma lista de "tipos de feição" (ex: "Poste de BT", "Boca de Lobo", "Hidrante").
        *   Para cada tipo de feição, uma lista de "campos" (atributos).
        *   Cada campo terá um nome, um tipo (`text`, `number`, `select`, `boolean`, `photo`), uma legenda e, opcionalmente, regras de validação.

#### 2. Renderização Dinâmica dos Formulários no App de Campo
*   **Sub-Objetivo**: Fazer com que o App de Campo leia o `forms.json` e construa a interface de coleta de dados dinamicamente.
*   **Entregas**:
    *   **Lógica de Leitura de Configuração**: O App de Campo (PWA/Electron) lerá o `forms.json` na inicialização.
    *   **Componentes de UI Reutilizáveis**: Criar componentes de UI (React/Vue/Svelte) para cada tipo de campo (input de texto, dropdown, toggle, etc.).
    *   **Renderizador de Formulário**: Desenvolver a lógica que itera sobre a configuração do formulário e renderiza os componentes de UI apropriados quando o usuário seleciona um tipo de feição para coletar.

#### 3. Armazenamento dos Dados Coletados
*   **Sub-Objetivo**: Garantir que os dados coletados de acordo com o formulário dinâmico sejam salvos corretamente.
*   **Entregas**:
    *   **Exportação para GeoJSON Enriquecido**: Ao coletar uma feição, o app salvará a geometria (ponto GPS) e, na seção `properties` do GeoJSON, armazenará os dados dos campos do formulário em um formato chave-valor.
    *   **Exemplo de `properties`**:
        ```json
        "properties": {
          "featureType": "Boca de Lobo",
          "status_limpeza": "obstruído",
          "diametro_cm": 80,
          "necessita_reparo": true,
          "foto_path": "photos/boca_lobo_123.jpg"
        }
        ```

#### 4. Interface de Gerenciamento de Formulários (Opcional, Fase Avançada)
*   **Sub-Objetivo**: Criar uma UI para que os usuários possam criar e editar os formulários sem editar o JSON manualmente.
*   **Entregas**:
    *   **Editor de Formulários Visual**: Uma nova seção na UI do plugin principal (sisRUA no AutoCAD) ou uma página web separada para construir visualmente os formulários (arrastar e soltar campos, etc.).
    *   **Exportação/Importação de Templates**: Permitir que os usuários salvem e carreguem templates de formulários (`.json`), facilitando o compartilhamento entre equipes.

### Critérios de Sucesso
*   ✔️ O App de Campo exibe opções de coleta de dados com base no que está definido em `forms.json`.
*   ✔️ O usuário pode preencher os campos customizados para cada feição coletada.
*   ✔️ O arquivo GeoJSON exportado contém os atributos personalizados na seção `properties`.
*   ✔️ A solução é flexível o suficiente para suportar diferentes tipos de levantamentos (elétrico, saneamento, ambiental, etc.).
