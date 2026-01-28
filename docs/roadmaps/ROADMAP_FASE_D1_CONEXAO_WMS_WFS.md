# ROADMAP SUPLEMENTAR (FUTURO) — FASE D.1 — CONEXÃO COM FONTES DE DADOS ONLINE (WMS/WFS)

## Visão da Fase D.1
Expandir o sisRUA de uma ferramenta que consome arquivos estáticos para uma plataforma que se conecta diretamente a serviços de dados geoespaciais ao vivo, permitindo o acesso a um universo muito maior de dados atualizados e oficiais (governamentais, corporativos) sem a necessidade de download e gerenciamento de arquivos.

## PRINCÍPIOS ARQUITETURAIS
*   **Aderência aos Padrões OGC**: A implementação deve seguir as especificações do Open Geospatial Consortium (OGC) para WMS (Web Map Service) and WFS (Web Feature Service).
*   **Integração via Backend**: A comunicação com os serviços externos é uma responsabilidade do backend Python.
*   **Visualização vs. Importação**: Deve haver uma distinção clara entre:
    *   **WMS**: Visualizar o mapa como uma imagem de fundo (raster).
    *   **WFS**: Importar as feições como dados vetoriais (geometria).

## FASE D.1 — CONEXÃO COM FONTES DE DADOS ONLINE (WMS/WFS)
**Objetivo**: Implementar a capacidade de se conectar, visualizar e importar dados de serviços WMS e WFS.

### Entregas Detalhadas

#### 1. Gerenciador de Fontes de Dados (Data Sources) na UI
*   **Sub-Objetivo**: Criar uma interface para o usuário gerenciar as URLs dos serviços WMS/WFS.
*   **Entregas**:
    *   **Painel "Fontes de Dados Online" (Frontend)**: Uma nova seção na UI.
    *   **UI para Adicionar/Editar/Remover**: O usuário poderá salvar e dar um apelido para as URLs dos serviços que mais utiliza (ex: "IBGE - Malha Municipal", "MMA - Unidades de Conservação").
    *   **Persistência**: As fontes de dados configuradas serão salvas no `settings.json`.

#### 2. Implementação do Cliente WMS (Visualização de Mapa)
*   **Sub-Objetivo**: Adicionar a capacidade de exibir uma camada WMS como um mapa base no Leaflet.
*   **Entregas**:
    *   **Componente de Camada WMS (Frontend)**: O Leaflet já possui suporte nativo para camadas WMS (`L.tileLayer.wms`). A UI permitirá que o usuário selecione um dos serviços WMS configurados para exibi-lo como uma camada de sobreposição no mapa.
    *   **Interação com `GetCapabilities`**: O frontend fará uma requisição `GetCapabilities` ao serviço WMS para listar as camadas disponíveis e permitir que o usuário escolha qual visualizar.

#### 3. Implementação do Cliente WFS (Importação de Vetores)
*   **Sub-Objetivo**: Desenvolver a lógica para buscar dados vetoriais de um serviço WFS e integrá-los ao fluxo de trabalho do sisRUA.
*   **Entregas**:
    *   **Lógica de Requisição WFS (Backend)**:
        *   Um novo endpoint no backend, como `/api/v1/import/wfs`, que receberá a URL do serviço, o nome da camada desejada e o bounding box da área de interesse.
        *   O backend (Python) usará uma biblioteca como `OWSLib` ou fará requisições HTTP diretas para construir a URL de `GetFeature` do WFS.
        *   A requisição pedirá os dados em formato GeoJSON (`outputFormat=application/json`).
    *   **Integração com o Fluxo Principal**: O GeoJSON retornado pelo serviço WFS será então alimentado no mesmo pipeline de processamento que já existe para arquivos GeoJSON, resultando em `CadFeature`s que podem ser desenhadas no AutoCAD.

### Critérios de Sucesso
*   ✔️ O usuário pode adicionar, salvar e gerenciar URLs de serviços WMS/WFS na interface do plugin.
*   ✔️ O usuário pode selecionar um serviço WMS e visualizá-lo como uma camada de mapa no frontend.
*   ✔️ O usuário pode selecionar um serviço WFS, uma camada e uma área, e as feições vetoriais correspondentes são importadas e desenhadas no AutoCAD.
*   ✔️ O sistema lida de forma graciosa com URLs de serviço inválidas ou indisponíveis.
