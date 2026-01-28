# ROADMAP DA FASE 1.5.7 — IMPORTAÇÃO DE EDIFICAÇÕES DO OSM — sisRUA

## Visão da Fase 1.5.7
Enriquecer drasticamente o contexto dos projetos gerados, permitindo que o usuário, com um único clique, importe não apenas a malha viária, mas também os contornos (footprints) das edificações existentes na área de interesse, tudo a partir do OpenStreetMap.

## PRINCÍPIOS ARQUITETURAIS
*   **Reutilização de Pipeline**: A nova funcionalidade deve se integrar ao fluxo de trabalho existente (`OSM -> Backend -> C#`), minimizando a necessidade de refatoração.
*   **Controle do Usuário**: A importação de edificações deve ser uma opção que o usuário pode habilitar ou desabilitar para controlar a quantidade de dados e o tempo de processamento.
*   **Processamento no Backend**: A tarefa de buscar e processar os dados das edificações é uma responsabilidade do backend Python, que já lida com a lógica GIS.

## FASE 1.5.7 — IMPORTAÇÃO DE EDIFICAÇÕES DO OSM
**Objetivo**: Adicionar a capacidade de importar e desenhar os contornos das edificações adjacentes à malha viária a partir do OpenStreetMap.

### Entregas Detalhadas

#### 1. Modificação do Backend (Python `api.py`)
*   **Sub-Objetivo**: Estender a função `_prepare_osm_compute` para buscar e processar polígonos de edificações.
*   **Entregas**:
    *   **Busca de Feições**: Utilizar a função `osmnx.features.features_from_point` para baixar feições com a tag `{"building": True}` na mesma área e coordenadas da busca de ruas.
    *   **Processamento de Polígonos**: Iterar sobre o GeoDataFrame de edificações retornado.
    *   **Conversão para `CadFeature`**: Para cada polígono de edificação, criar uma `CadFeature` do tipo `Polyline` (fechada), atribuindo-a a uma camada específica (ex: `SISRUA_OSM_EDIFICIOS`).
    *   **Otimização**: A busca de edificações só deve ocorrer se um novo parâmetro (ex: `include_buildings=true`) for passado na requisição da API.

#### 2. Atualização da Interface do Usuário (Frontend `App.jsx`)
*   **Sub-Objetivo**: Dar ao usuário a opção de incluir ou não as edificações na importação.
*   **Entregas**:
    *   **Novo Controle na UI**: Adicionar um `checkbox` ou `toggle switch` no painel principal com o texto "Incluir Edificações".
    *   **Estado da UI**: Gerenciar o estado (ligado/desligado) desta opção no componente React.
    *   **Modificação da Requisição**: Ao acionar a geração de projeto OSM, o frontend passará o novo parâmetro `include_buildings` para o backend (seja na mensagem para o C# ou diretamente na chamada de API, dependendo da arquitetura final).

#### 3. Ajustes no Plugin C#
*   **Sub-Objetivo**: Garantir que as novas `CadFeature`s de edificação sejam desenhadas corretamente.
*   **Entregas**:
    *   **Gerenciamento de Camada**: A lógica em `SisRuaCommands.cs` já é genérica o suficiente para desenhar qualquer `Polyline` em qualquer camada. A única garantia necessária é que a nova camada `SISRUA_OSM_EDIFICIOS` seja criada com uma cor padrão distinta (ex: um tom de cinza ou amarelo), seguindo a mesma lógica já existente para a criação de camadas.

#### 4. Atualização da Estratégia de Testes
*   **Sub-Objetivo**: Validar a nova funcionalidade de ponta a ponta.
*   **Entregas**:
    *   **Novos FRs/NFRs**: Adicionar um requisito em `qa/requirements.md` para a importação de edificações do OSM.
    *   **Testes Automatizados (Backend)**: Modificar os testes de `test_api_auth_and_jobs.py` para:
        *   Testar a importação de OSM com a opção `include_buildings` habilitada.
        *   Verificar se a resposta contém `CadFeature`s na camada `SISRUA_OSM_EDIFICIOS`.
    *   **Casos de Teste Manuais**: Adicionar um novo caso de teste em `qa/manual/test-cases-manual.csv` para verificar se, ao marcar a opção "Incluir Edificações", os contornos dos prédios são corretamente desenhados no AutoCAD.

### Critérios de Sucesso
*   ✔️ A UI do plugin apresenta uma opção para incluir edificações na importação de OSM.
*   ✔️ Quando a opção está marcada, o backend busca e processa os dados de edificações.
*   ✔️ O desenho final no AutoCAD inclui os contornos das edificações em uma camada separada e com cor distinta.
*   ✔️ Quando a opção está desmarcada, o comportamento do plugin é o mesmo de antes, sem buscar dados extras.
