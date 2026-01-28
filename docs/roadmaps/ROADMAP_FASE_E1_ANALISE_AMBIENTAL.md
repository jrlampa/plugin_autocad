# ROADMAP SUPLEMENTAR (FUTURO) — FASE E.1 — ANÁLISE DE ZONAS AMBIENTAIS (API BRASIL)

## Visão da Fase E.1
Agregar uma camada de inteligência de conformidade ambiental ao sisRUA, permitindo que o usuário identifique, no início do ciclo de projeto, potenciais conflitos com áreas de proteção ambiental (APPs, Unidades de Conservação, etc.), economizando tempo e evitando retrabalho e problemas legais.

## PRINCÍPIOS ARQUITETURAIS
*   **Conectividade Opcional**: A funcionalidade dependerá de uma conexão com a internet para consultar a API externa, mas a falha na consulta não deve impedir o funcionamento principal do plugin.
*   **Foco em Alertas, Não em Análise Profunda**: O objetivo inicial é alertar o usuário sobre a *presença* de uma zona ambiental, não fornecer um laudo ambiental completo.
*   **Integração via Backend**: A lógica de consulta à API externa deve residir no backend Python, mantendo o plugin C# focado na interação com o CAD.

## FASE E.1 — ANÁLISE DE ZONAS AMBIENTAIS (API BRASIL)
**Objetivo**: Implementar uma consulta a uma API de dados geoespaciais do Brasil para verificar se o ponto central do projeto está inserido em uma zona de proteção ambiental e exibir um alerta para o usuário.

### Entregas Detalhadas

#### 1. Pesquisa e Seleção da API
*   **Sub-Objetivo**: Identificar APIs ou serviços de mapa (WMS/WFS) gratuitos e confiáveis que forneçam dados sobre zonas ambientais no Brasil.
*   **Entregas**:
    *   **Levantamento de Fontes**: Pesquisar por serviços de dados oferecidos por órgãos como MMA, ICMBio, IBAMA, Secretarias Estaduais de Meio Ambiente e o Cadastro Ambiental Rural (CAR).
    *   **Critérios de Seleção**: A API/serviço escolhido deve ser de acesso público, ter uma documentação clara e permitir consultas por coordenadas geográficas (ponto ou bounding box).
    *   **Exemplo**: API do "GeoSampa" para São Paulo, ou um serviço WFS do MMA para dados nacionais.

#### 2. Implementação da Consulta no Backend
*   **Sub-Objetivo**: Desenvolver a lógica no backend Python para realizar a consulta à API externa.
*   **Entregas**:
    *   **Novo Endpoint de API (Opcional)**: Um novo endpoint, como `/api/v1/check_environmental_zone`, que recebe as coordenadas do projeto.
    *   **Lógica de Consulta (Python)**:
        *   Quando um projeto é gerado (via OSM, por exemplo), o backend fará uma chamada HTTP para a API ambiental externa, enviando as coordenadas do ponto central.
        *   A lógica irá interpretar a resposta da API (que pode ser um JSON, XML ou outro formato) para determinar se o ponto está dentro de uma zona de interesse.
    *   **Retorno para o Frontend**: O backend enviará uma notificação para o frontend com o resultado da análise (ex: `{"zone_found": true, "zone_type": "Área de Preservação Permanente", "source": "MMA"}`).

#### 3. Exibição do Alerta na Interface do Usuário
*   **Sub-Objetivo**: Informar o usuário de forma clara e não intrusiva sobre o resultado da análise.
*   **Entregas**:
    *   **Componente de Alerta na UI (Frontend)**:
        *   Após a geração de um projeto, se o backend retornar um alerta ambiental, a UI exibirá uma notificação visual.
        *   O alerta pode ser um banner, um ícone ao lado do nome da localização, ou um pop-up.
        *   A mensagem deve informar o tipo de zona encontrada e a fonte dos dados, com um aviso de que a informação é para referência e requer verificação formal.
    *   **Exemplo de Mensagem**: "⚠️ Alerta: A área do projeto pode estar sobre uma Zona de Amortecimento, segundo dados do ICMBio. Recomenda-se verificação junto aos órgãos competentes."

### Critérios de Sucesso
*   ✔️ O backend consegue consultar com sucesso uma API ambiental brasileira.
*   ✔️ Quando um projeto é gerado em uma área de proteção, o usuário recebe um alerta visual na interface do sisRUA.
*   ✔️ O alerta informa o tipo de zona e a fonte dos dados.
*   ✔️ Se a consulta à API falhar ou a área não tiver restrições, nenhuma notificação é exibida e o fluxo do usuário continua normalmente.
