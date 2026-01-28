# ROADMAP DA FASE 1.5.8 — DESENHO DE BLOCOS A PARTIR DE PONTOS INSERIDOS NA UI — sisRUA

## Visão da Fase 1.5.8
Completar o ciclo de trabalho para o usuário inserir elementos pontuais (como postes, árvores) diretamente no mapa da interface do plugin e, com uma ação explícita, tê-los desenhados como blocos configurados no AutoCAD, aproveitando a infraestrutura de blocos e processamento de GeoJSON já existente.

## PRINCÍPIOS ARQUITETURAIS
*   **Reutilização de Componentes**: Utilizar ao máximo os componentes de UI (marcadores arrastáveis) e o pipeline de backend (processamento de GeoJSON) já existentes.
*   **Feedback Visual Claro**: A interface deve dar feedback claro sobre quais pontos estão marcados e prontos para serem enviados.
*   **Simplicidade de Fluxo**: O processo deve ser intuitivo para o usuário.

## FASE 1.5.8 — DESENHO DE BLOCOS A PARTIR DE PONTOS INSERIDOS NA UI
**Objetivo**: Implementar a funcionalidade para converter marcadores inseridos manualmente pelo usuário no mapa da interface em blocos do AutoCAD, utilizando o fluxo GeoJSON -> Backend -> C# existente.

### Entregas Detalhadas

#### 1. Coleta de Dados dos Marcadores (Frontend `App.jsx`)
*   **Sub-Objetivo**: Adicionar a capacidade de coletar todos os marcadores que o usuário adicionou manualmente no mapa e prepará-los para envio.
*   **Entregas**:
    *   **Acesso aos Marcadores**: O `useMapLogic` já gerencia o estado dos `markers`. Uma função será adicionada para retornar todos os marcadores ativos.
    *   **Formato GeoJSON**: Converter cada marcador (com sua posição `lat/lng` e `tipo` - ex: "POSTE", "ARVORE") em um `GeoJSON Point Feature`, onde o `tipo` será mapeado para o `block_name` nas `properties` do GeoJSON.
    *   **Exemplo de GeoJSON para um marcador "Poste"**:
        ```json
        {
          "type": "Feature",
          "properties": {
            "block_name": "POSTE",
            "name": "Poste A",
            "layer": "SISRUA_MANUAL_PONTOS"
            // outros atributos (meta.desc, meta.altura) também podem ser incluídos
          },
          "geometry": {
            "type": "Point",
            "coordinates": [-41.3235, -21.7634]
          }
        }
        ```

#### 2. Botão de Ação na UI (Frontend `App.jsx`)
*   **Sub-Objetivo**: Criar um controle na interface para o usuário disparar o envio dos pontos para o AutoCAD.
*   **Entregas**:
    *   **Botão "Desenhar Pontos no CAD"**: Adicionar um botão no painel direito (próximo aos botões "GERAR OSM") que fica habilitado quando há marcadores no mapa.
    *   **Evento de Clique**: Ao clicar, o botão acionará a função de coleta de dados dos marcadores e o envio para o plugin C#.

#### 3. Envio para o Plugin C# (`SisRuaPalette.cs`)
*   **Sub-Objetivo**: Enviar o GeoJSON contendo os pontos para o plugin C#.
*   **Entregas**:
    *   **Nova Ação `SEND_UI_POINTS_TO_CAD`**: O frontend enviará uma mensagem para o C# com o GeoJSON gerado e uma nova ação.
    *   **Handler em `SisRuaPalette.cs`**: O `HandleMessage` em `SisRuaPalette.cs` será atualizado para reconhecer essa nova ação.
    *   **Reutilização de `ImportarDadosCampo`**: O plugin C# passará o GeoJSON recebido para `SisRuaCommands.ImportarDadosCampo`, que já sabe como lidar com GeoJSON, incluindo `Point` features com `block_name`.

#### 4. Limpeza da UI (Opcional)
*   **Sub-Objetivo**: Após o envio bem-sucedido, oferecer a opção de remover os marcadores do mapa.
*   **Entregas**:
    *   **Clear Markers**: Um prompt ou uma opção na UI para limpar os marcadores do mapa do frontend após o desenho no CAD.

#### 5. Atualização da Estratégia de Testes
*   **Sub-Objetivo**: Validar a nova funcionalidade de ponta a ponta.
*   **Entregas**:
    *   **Novos FRs/NFRs**: Adicionar um requisito em `qa/requirements.md` para a inserção de pontos via UI.
    *   **Casos de Teste Manuais**: Adicionar um novo caso de teste em `qa/manual/test-cases-manual.csv` para verificar se:
        *   Usuário pode arrastar e soltar ícones de bloco no mapa.
        *   Botão "Desenhar Pontos no CAD" fica habilitado.
        *   Ao clicar no botão, os blocos são corretamente inseridos no AutoCAD.

### Critérios de Sucesso
*   ✔️ O usuário pode inserir múltiplos pontos de bloco (Poste, Árvore) no mapa do frontend.
*   ✔️ Um botão na UI permite enviar esses pontos para o AutoCAD.
*   ✔️ Os pontos são convertidos em `GeoJSON Point Features` e processados pelo backend.
*   ✔️ Os blocos correspondentes são desenhados corretamente no AutoCAD nas coordenadas especificadas.
*   ✔️ A funcionalidade se integra perfeitamente com a lógica existente de importação de blocos via GeoJSON.
