# ROADMAP SUPLEMENTAR (FUTURO) — FASE X.2 — SUPORTE A TABELAS AUTOCAD

## Visão da Fase X.2
Transformar o desenho CAD de uma representação puramente gráfica para um "relatório visual", onde os dados e atributos das feições são apresentados de forma estruturada e vinculada à geometria, alinhando o sisRUA com as práticas de documentação de projetos de engenharia.

## PRINCÍPIOS ARQUITETURAIS
*   **Vínculo Dado-Gráfico**: A tabela gerada deve ser facilmente associável aos elementos desenhados.
*   **Customização**: O usuário deve poder escolher quais atributos (colunas) e quais feições (linhas) são incluídos na tabela.
*   **Padrões CAD**: A tabela deve ser gerada usando objetos `Table` nativos do AutoCAD, respeitando os `TableStyle` existentes no desenho.

## FASE X.2 — SUPORTE A TABELAS AUTOCAD
**Objetivo**: Implementar a capacidade de gerar uma tabela de quantitativos e atributos no AutoCAD, resumindo as informações das feições que foram importadas e desenhadas pelo sisRUA.

### Entregas Detalhadas

#### 1. Coleta de Dados para a Tabela
*   **Sub-Objetivo**: Agregar todos os dados relevantes das feições desenhadas em uma estrutura de dados preparada para ser tabulada.
*   **Entregas**:
    *   **Lógica de Agregação (C#)**: Em `SisRuaCommands.cs`, após o desenho de todas as feições, iterar sobre a lista de `CadFeature`s processadas.
    *   **Estrutura de Dados**: Montar uma lista de objetos onde cada objeto representa uma linha da tabela, contendo as propriedades relevantes (ex: `Nome`, `Tipo de Via`, `Comprimento Calculado (m)`, `Camada CAD`, `ID do Bloco`, etc.).

#### 2. Criação da Tabela no AutoCAD
*   **Sub-Objetivo**: Desenvolver a lógica para criar e popular um objeto `Table` nativo do AutoCAD.
*   **Entregas**:
    *   **Novo Comando `SISRUA_GERAR_TABELA`**: Criar um novo `CommandMethod` que executa a lógica de geração de tabela com base nas últimas feições desenhadas.
    *   **Lógica de Criação de Tabela (C#)**:
        *   Criar um objeto `Table`.
        *   Definir o número de linhas e colunas com base nos dados agregados.
        *   Definir os cabeçalhos das colunas (ex: "ID", "NOME", "COMPRIMENTO").
        *   Popular as células da tabela com os dados das feições.
        *   Aplicar um `TableStyle` (seja o padrão do desenho ou um configurado pelo usuário).
    *   **Interação com o Usuário**: O comando pedirá ao usuário para selecionar o ponto de inserção da tabela no desenho.

#### 3. Configuração da Tabela pelo Usuário
*   **Sub-Objetivo**: Permitir que o usuário personalize o conteúdo e a aparência da tabela.
*   **Entregas**:
    *   **UI de Configuração (Frontend)**: Adicionar uma nova seção na UI para "Tabelas e Relatórios".
    *   **Controles na UI**: Permitir que o usuário:
        *   Selecione quais colunas (atributos) devem ser incluídas na tabela.
        *   Filtre quais tipos de feições devem ser incluídas (ex: "gerar tabela apenas para postes").
        *   Defina um nome para o `TableStyle` a ser usado.
    *   **Persistência das Configurações**: Salvar as preferências do usuário no `settings.json` (FASE 1.5.6).

### Critérios de Sucesso
*   ✔️ Um novo comando `SISRUA_GERAR_TABELA` está disponível.
*   ✔️ O comando gera uma tabela no AutoCAD contendo os atributos das feições desenhadas.
*   ✔️ A tabela inclui quantitativos relevantes (ex: contagem de blocos, comprimento de polilinhas).
*   ✔️ O usuário pode configurar quais colunas e tipos de feições são incluídos na tabela.
