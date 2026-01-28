# ROADMAP SUPLEMENTAR (FUTURO) — FASE A.1 — VETORIZAÇÃO DE IMAGENS COM IA (RASTER-TO-VECTOR)

## Visão da Fase A.1
Superar uma das maiores barreiras em projetos de engenharia e GIS: a digitalização de dados legados. Esta fase visa capacitar o sisRUA a "ler" mapas em formato de imagem (scans, PDFs, imagens de satélite) e extrair de forma inteligente as feições vetoriais (ruas, edificações), automatizando um processo que hoje é extremamente manual, demorado e sujeito a erros.

## PRINCÍPIOS ARQUITETURAIS
*   **Integração com Serviços de IA**: A lógica de reconhecimento de imagem residirá em um serviço externo (seja uma API de nuvem como Google Vision AI / Azure Cognitive Services, ou um modelo de ML hospedado). O backend Python será o orquestrador.
*   **Fluxo de Trabalho Assistido**: A IA não substituirá o projetista, mas o assistirá. O resultado da vetorização será um "rascunho" que o usuário poderá revisar e aprovar antes de prosseguir.
*   **Foco Inicial em Ruas**: O primeiro caso de uso será a extração de eixos de ruas, por ser a feição mais proeminente e de maior valor inicial.

## FASE A.1 — VETORIZAÇÃO DE IMAGENS COM IA (RASTER-TO-VECTOR)
**Objetivo**: Implementar um fluxo de trabalho onde o usuário pode importar uma imagem raster (ex: PNG, JPG, TIFF) e usar um modelo de IA para detectar e extrair feições lineares (ruas) como dados vetoriais, que podem então ser processados pelo pipeline do sisRUA.

### Entregas Detalhadas

#### 1. Pesquisa e Integração com Serviço de Visão Computacional
*   **Sub-Objetivo**: Identificar e selecionar uma tecnologia de IA para a tarefa de segmentação de imagem e extração de feições.
*   **Entregas**:
    *   **Levantamento de Tecnologias**:
        *   **APIs de Nuvem**: Avaliar APIs prontas como Google Vision AI, Azure AI Vision, ou AWS Rekognition para tarefas de OCR e detecção de objetos/linhas.
        *   **Modelos Open Source**: Pesquisar por modelos de Machine Learning pré-treinados para segmentação de imagens de mapas ou satélites (ex: modelos baseados em U-Net).
    *   **Prova de Conceito (PoC)**: Realizar uma PoC para validar a eficácia da tecnologia escolhida em extrair eixos de ruas a partir de imagens de exemplo.

#### 2. Interface do Usuário para Importação e Georreferenciamento
*   **Sub-Objetivo**: Permitir que o usuário carregue uma imagem e a posicione geograficamente.
*   **Entregas**:
    *   **Upload de Imagem (Frontend)**: Uma nova opção na UI para o usuário fazer upload de um arquivo de imagem.
    *   **Ferramenta de Georreferenciamento Simplificado**:
        *   A imagem carregada será exibida como uma camada semi-transparente sobre o mapa base (Leaflet).
        *   O usuário poderá arrastar, rotacionar e escalar a imagem até que ela se alinhe com o mapa base.
        *   Alternativamente, o usuário poderá clicar em dois ou mais pontos de controle na imagem e seus correspondentes no mapa para realizar o georreferenciamento.

#### 3. Backend para Processamento de Imagem
*   **Sub-Objetivo**: Orquestrar o envio da imagem para o serviço de IA e o processamento do resultado.
*   **Entregas**:
    *   **Novo Endpoint de API (Python)**: Um endpoint como `/api/v1/vectorize_image`, que recebe a imagem e seus dados de georreferenciamento.
    *   **Lógica de Processamento**:
        1.  O backend envia a imagem para o serviço de IA escolhido.
        2.  Recebe a resposta (que pode ser uma máscara de pixels, uma lista de coordenadas de linhas, etc.).
        3.  **Pós-processamento**: Converte a resposta da IA em um formato GeoJSON de `LineString`s. Esta etapa pode envolver algoritmos de "afinamento" de linhas (skeletonization) e suavização.
        4.  O GeoJSON resultante é retornado para o frontend para preview.

#### 4. Revisão e Aprovação pelo Usuário
*   **Sub-Objetivo**: Dar ao usuário a chance de revisar e aprovar o resultado da vetorização.
*   **Entregas**:
    *   **Preview no Frontend**: O GeoJSON vetorizado é exibido sobre o mapa e a imagem original.
    *   **Ferramentas de Edição Simples (Opcional)**: Ferramentas básicas para o usuário deletar linhas incorretas ou conectar segmentos quebrados.
    *   **Botão "Aprovar e Importar"**: Ao clicar, o GeoJSON aprovado é enviado para o pipeline normal de importação do sisRUA.

### Critérios de Sucesso
*   ✔️ O usuário consegue fazer upload de uma imagem (ex: JPG, PNG) na interface.
*   ✔️ O usuário consegue alinhar (georreferenciar) a imagem com o mapa base.
*   ✔️ A IA consegue identificar e extrair os eixos das ruas da imagem como dados vetoriais.
*   ✔️ O resultado é exibido como um preview para o usuário, que pode então importá-lo para o AutoCAD.
