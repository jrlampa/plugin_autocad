# ROADMAP SUPLEMENTAR (FUTURO) — FASE P.2 — SUPORTE A XREFS E VIEWPORTS

## Visão da Fase P.2
Alinhar o sisRUA com as melhores práticas de organização de projetos em AutoCAD, tratando os dados importados como uma base de referência externa. Isso promove desenhos mais limpos, leves e modulares, onde os dados do sisRUA servem como um "pano de fundo" para o projeto do usuário, em vez de se misturarem diretamente com ele.

## PRINCÍPIOS ARQUITETURAIS
*   **Não-destrutivo**: O fluxo de trabalho com XRef garante que o desenho principal do usuário permaneça intacto, com os dados do sisRUA contidos em um arquivo separado.
*   **Opcional**: O usuário deve poder escolher entre o modo de desenho atual (direto no Model Space) e o novo modo XRef.
*   **Automação do Fluxo CAD**: O plugin deve automatizar todo o processo: criar o DWG, anexá-lo como XRef e, opcionalmente, configurar uma viewport para visualização imediata.

## FASE P.2 — SUPORTE A XREFS (REFERÊNCIAS EXTERNAS) E VIEWPORTS
**Objetivo**: Implementar uma opção para que o resultado da importação de dados seja salvo em um novo arquivo `.dwg` e automaticamente anexado como uma XRef ao desenho ativo do usuário, com a criação opcional de um layout e viewport configurados.

### Entregas Detalhadas

#### 1. Lógica de Criação de Desenho Externo (C#)
*   **Sub-Objetivo**: Desenvolver a capacidade de criar um novo arquivo `.dwg` em segundo plano e desenhar as feições nele.
*   **Entregas**:
    *   **Criação de Banco de Dados**: Utilizar a API do AutoCAD para criar um `Database` em memória ou diretamente em um arquivo `.dwg` temporário.
    *   **Lógica de Desenho Adaptada**: A lógica de `SisRuaCommands.cs` (desenhar polilinhas, inserir blocos, criar layers) será adaptada para operar sobre este `Database` externo, em vez do `Database` do documento ativo.
    *   **Salvar o DWG**: Após o desenho, salvar o `Database` em um arquivo `.dwg` em um local escolhido pelo usuário ou em uma subpasta do projeto.

#### 2. Funcionalidade de Anexação de XRef (C#)
*   **Sub-Objetivo**: Anexar o `.dwg` recém-criado como uma XRef no desenho atual do usuário.
*   **Entregas**:
    *   **Comando `AttachXref`**: Utilizar a função `db.AttachXref()` da API do AutoCAD.
    *   **Configuração de XRef**: Definir o tipo de anexo como `Attachment` ou `Overlay` (configurável pelo usuário). O XRef deve ser inserido na coordenada `0,0,0` e com escala `1:1`.
    *   **Gerenciamento de Camadas da XRef**: Garantir que o AutoCAD gerencie corretamente as camadas vindas da XRef (ex: com o prefixo do nome do arquivo).

#### 3. Criação Automática de Layout e Viewport (C#)
*   **Sub-Objetivo**: Facilitar a visualização dos dados da XRef em uma prancha (espaço de papel).
*   **Entregas**:
    *   **Novo Comando `SISRUA_CRIAR_LAYOUT_XREF`**: Um comando que cria um novo Layout.
    *   **Criação de Viewport**: Dentro do novo layout, criar um objeto `Viewport`.
    *   **Zoom Extents**: Configurar a `Viewport` para aplicar um "Zoom Extents" nos dados da XRef, garantindo que todo o conteúdo importado seja visível.
    *   **Escala da Viewport**: Permitir que o usuário defina uma escala padrão para a viewport (ex: 1:1000).

#### 4. Interface do Usuário
*   **Sub-Objetivo**: Expor as novas opções de fluxo de trabalho para o usuário.
*   **Entregas**:
    *   **Opção de Modo de Importação (Frontend)**: No painel onde o usuário inicia a importação, adicionar uma opção para escolher o modo:
        *   "Desenhar no Desenho Atual" (comportamento padrão).
        *   "Anexar como XRef".
    *   **Configurações de XRef**: Se o modo XRef for escolhido, exibir opções para:
        *   Nome do arquivo `.dwg` a ser criado.
        *   Tipo de anexo (`Attachment` vs. `Overlay`).
        *   Opção para criar layout e viewport automaticamente.

### Critérios de Sucesso
*   ✔️ O usuário pode escolher importar os dados como uma XRef.
*   ✔️ O plugin cria um novo arquivo `.dwg` com os dados importados, sem desenhar no arquivo ativo.
*   ✔️ O novo `.dwg` é anexado com sucesso como uma XRef ao desenho do usuário.
*   ✔️ Opcionalmente, um novo layout com uma viewport mostrando a XRef é criado.
*   ✔️ O fluxo de trabalho tradicional (desenho direto) continua funcionando normalmente.
