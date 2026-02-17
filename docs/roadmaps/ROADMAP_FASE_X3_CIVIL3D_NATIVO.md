# ROADMAP SUPLEMENTAR (FUTURO) — FASE X.3 — SUPORTE A AUTOCAD CIVIL 3D NATIVO

## Visão da Fase X.3
Evoluir o sisRUA de um plugin genérico do AutoCAD para uma ferramenta de automação de engenharia civil de alto nível, aproveitando o poder do modelo de objetos do Civil 3D para criar projetos mais inteligentes, dinâmicos e úteis para engenheiros civis.

## PRINCÍPIOS ARQUITETURAIS
*   **Integração Profunda**: O plugin deve interagir com a API do Civil 3D, não apenas com a API base do AutoCAD.
*   **Detecção de Ambiente**: O plugin deve detectar se está rodando no Civil 3D e, nesse caso, habilitar as funcionalidades específicas.
*   **Não Quebrar Compatibilidade**: A funcionalidade base deve continuar funcionando no AutoCAD "vanilla".

## FASE X.3 — SUPORTE A AUTOCAD CIVIL 3D NATIVO
**Objetivo**: Implementar a capacidade de gerar objetos nativos do Civil 3D, como `Alignments` e `Parcels`, a partir dos dados de ruas e áreas importados, em vez de apenas polilinhas genéricas.

### Entregas Detalhadas

#### 1. Adaptação do Projeto e Referências
*   **Sub-Objetivo**: Preparar o ambiente de desenvolvimento para a API do Civil 3D.
*   **Entregas**:
    *   **Adicionar Referências C#**: Adicionar referências às DLLs da API do Civil 3D (ex: `AeccDbMgd.dll`) ao `sisRUA.csproj`, com carregamento condicional para não quebrar o build para AutoCAD base.
    *   **Abstração de "Desenhador"**: Refatorar `SisRuaCommands.cs` para usar uma interface de "desenhador" (ex: `IDrawingService`). Haveria duas implementações: `AutoCADDrawingService` (padrão) e `Civil3DDrawingService`. O plugin selecionaria a implementação correta em tempo de execução.

#### 2. Geração de `Alignments` (Alinhamentos) a partir de Ruas
*   **Sub-Objetivo**: Converter os eixos das ruas em objetos `Alignment` do Civil 3D.
*   **Entregas**:
    *   **Lógica de Criação de Alignment (C#)**: No `Civil3DDrawingService`, em vez de desenhar uma polyline para o eixo da rua, criar um objeto `Alignment`.
    *   **Estilos de Alignment**: Permitir que o usuário configure, na UI, o `AlignmentStyle` e `AlignmentLabelSetStyle` a serem usados, oferecendo uma experiência nativa do Civil 3D.
    *   **Dados de Propriedade**: O nome da rua e outras informações seriam atribuídos às propriedades do `Alignment`.

#### 3. Geração de `Parcels` (Lotes) a partir de Áreas
*   **Sub-Objetivo**: Converter geometrias de polígonos fechados (ex: quarteirões, áreas verdes) em objetos `Parcel` do Civil 3D.
*   **Entregas**:
    *   **Lógica de Criação de Parcel (C#)**: Desenvolver a lógica para criar `Parcels` a partir de polilinhas fechadas.
    *   **Estilos de Parcel**: Permitir a configuração do `ParcelStyle` e `ParcelLabelStyle`.
    *   **Criação de `Sites`**: Os `Parcels` no Civil 3D precisam pertencer a um `Site`. A lógica deve criar ou permitir que o usuário selecione um `Site` para os novos lotes.

#### 4. Interface do Usuário para Configurações do Civil 3D
*   **Sub-Objetivo**: Expor as novas opções de configuração na UI do sisRUA.
*   **Entregas**:
    *   **Detecção de Ambiente no Frontend**: O plugin C# informará ao frontend se o ambiente Civil 3D está ativo.
    *   **UI Condicional**: A UI exibirá uma nova seção de "Configurações do Civil 3D" apenas quando o plugin estiver rodando no Civil 3D.
    *   **Controles na UI**: Dropdowns para que o usuário selecione os estilos de `Alignment` e `Parcel` disponíveis no desenho atual.

### Critérios de Sucesso
*   ✔️ Quando rodando no Civil 3D, o plugin cria `Alignments` em vez de polilinhas para os eixos das ruas.
*   ✔️ As ruas desenhadas possuem as propriedades e a inteligência de um `Alignment` nativo.
*   ✔️ O usuário pode controlar os estilos dos objetos Civil 3D gerados.
*   ✔️ O plugin continua funcionando normalmente no AutoCAD base, sem erros.
