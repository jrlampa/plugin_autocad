# ROADMAP DA FASE 1.5 — BIBLIOTECA DE SÍMBOLOS (BLOCOS CAD) — sisRUA

## Visão da Fase 1.5
Complementar o MVP de desenho de ruas com uma biblioteca padronizada de símbolos (blocos CAD), garantindo consistência gráfica desde o início e fornecendo uma base para o cadastro técnico futuro.

## PRINCÍPIOS ARQUITETURAIS (Aplicáveis à Fase)
*   **Offline-first**: Os blocos CAD devem ser armazenados localmente e acessíveis sem conexão à internet.
*   **Formato aberto e padrão**: Utilização de arquivos `.dwg` ou `.dxf` para os blocos, facilmente manipuláveis pelo AutoCAD.
*   **Separação clara de responsabilidades**:
    *   **C# (Plugin AutoCAD)**: Responsável por gerenciar a inserção e associação lógica dos blocos no CAD.
    *   **Python (Backend)**: Pode enriquecer dados geográficos com informações para seleção de blocos (se aplicável, ex: identificação de tipo de poste).
    *   **JS (Frontend)**: Pode oferecer interface para seleção ou visualização de blocos (se houver interação do usuário).
*   **Nenhuma dependência de nuvem**: Os blocos são recursos locais.

## FASE 1.5 — BIBLIOTECA DE SÍMBOLOS (BLOCOS CAD)
**Objetivo**: Garantir padronização gráfica desde o início, fornecendo um catálogo inicial de blocos CAD para elementos comuns de infraestrutura e implementando um mecanismo de associação lógica entre os dados e os blocos.

### Entregas Detalhadas

#### 1. Definição e Criação do Catálogo Inicial de Blocos Base
*   **Sub-Objetivo**: Ter os arquivos CAD dos blocos prontos para uso.
*   **Entregas**:
    *   **Especificação de Tipos de Blocos**: Definir os tipos iniciais de blocos a serem padronizados (ex: `POSTE`, `MEDIDOR`, `CAIXA`).
    *   **Criação dos Arquivos `.dwg` ou `.dxf`**:
        *   Criar ou importar blocos CAD de alta qualidade e otimizados para cada tipo (ex: `POSTE_GENERICO.dwg`, `MEDIDOR_GENERICO.dwg`, `CAIXA_GENERICA.dwg`).
        *   Garantir que os blocos sejam simples, com layers apropriados e pontos de inserção bem definidos.
        *   Armazenar esses blocos na estrutura `sisRUA.bundle/Blocks/` (ou similar).
    *   **Padrão de Nomenclatura de Blocos**: Estabelecer um padrão claro para nomear os arquivos de blocos que reflita seu tipo e, futuramente, seu modelo (ex: `TIPO_MODELO.dwg`).

#### 2. Implementação do Mecanismo de Associação Lógica (Dados → Blocos)
*   **Sub-Objetivo**: Conectar as informações dos dados geográficos (OSM/GeoJSON) com a inserção dos blocos CAD.
*   **Entregas**:
    *   **Definição do Esquema de Metadados**:
        *   Decidir como os metadados dos blocos serão representados nos dados GeoJSON (ex: propriedades `{"sisrua_type": "POSTE", "sisrua_model": "GENERICO"}`).
    *   **Plugin C# - Leitura e Mapeamento**:
        *   Modificar `SisRuaCommands.cs` (ou classe similar) para ler metadados relevantes de `CadFeature` (retornado pelo backend).
        *   Implementar lógica para mapear esses metadados a arquivos de blocos específicos.
    *   **Plugin C# - Inserção Dinâmica de Blocos**:
        *   Desenvolver ou aprimorar a função de desenho (`DrawPolylines`) para inserir entidades `BlockReference` no CAD com base nos metadados e no catálogo de blocos.
        *   Gerenciar a inserção, escala e rotação dos blocos.
        *   Garantir a manipulação de camadas (layers) para os blocos.

#### 3. Integração e Testes
*   **Sub-Objetivo**: Assegurar que os blocos são corretamente inseridos e associados aos dados.
*   **Entregas**:
    *   **Atualização do Backend Python (se necessário)**: Se o backend for responsável por enriquecer os dados OSM/GeoJSON com metadados de blocos, implementar essa lógica.
    *   **Atualização do Frontend (se necessário)**: Se a UI precisar exibir ou permitir a seleção de blocos, implementar as mudanças no `App.jsx`.
    *   **Testes de Unidade e Integração**: Adicionar testes automatizados para o mapeamento de metadados para blocos e para a inserção correta de blocos.
    *   **Testes Manuais**: Atualizar `qa/manual/test-cases-manual.csv` com novos casos para verificar a inserção e padronização dos blocos no AutoCAD.

### Critérios de Sucesso da Fase 1.5
*   ✔️ Catálogo inicial de blocos (Poste, Medidor, Caixa) criado e armazenado.
*   ✔️ Plugin insere blocos CAD corretos no desenho com base nos metadados dos dados de origem.
*   ✔️ Blocos são inseridos em camadas (layers) padronizadas e com propriedades gráficas corretas.
*   ✔️ Desenhos CAD gerados contêm os símbolos de infraestrutura padronizados.

### ORDEM DE EXECUÇÃO IMEDIATA (MÃO NA MASSA)
1.  **Definir as especificações detalhadas** dos primeiros blocos (nomes, camadas, pontos de inserção).
2.  **Criar os arquivos DWG/DXF** dos blocos base (`POSTE_GENERICO.dwg`, `MEDIDOR_GENERICO.dwg`, `CAIXA_GENERICA.dwg`).
3.  **Atualizar o esquema de dados GeoJSON** para incluir os metadados de blocos (ex: `sisrua_type`, `sisrua_model`).
4.  **Implementar a leitura e mapeamento** desses metadados no plugin C#.
5.  **Desenvolver a lógica de inserção de `BlockReference`** no `SisRuaCommands.cs`.
