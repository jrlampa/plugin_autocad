# ROADMAP SUPLEMENTAR (FUTURO) — FASE Y.2 — INTEGRAÇÃO COM GPS EXTERNO DE ALTA PRECISÃO

## Visão da Fase Y.2
Elevar o "App Offline de Campo" (FASE 4) a uma ferramenta de coleta de dados de nível profissional, capaz de gerar dados geoespaciais com a precisão exigida por projetos de engenharia e topografia, eliminando a dependência do GPS de baixa acurácia dos dispositivos móveis.

## PRINCÍPIOS ARQUITETURAIS
*   **Padrões Abertos**: A integração deve priorizar protocolos padrão, como a comunicação serial sobre Bluetooth (SPP - Serial Port Profile) e o formato de dados NMEA.
*   **Experiência de Usuário Simples**: A conexão com o dispositivo GPS deve ser simples e o feedback sobre a qualidade do sinal (ex: RTK Fixed, Float, DGPS) deve ser claro para o usuário em campo.
*   **Modularidade**: A lógica de conexão com o GPS deve ser um módulo separado, permitindo a futura adição de outros tipos de dispositivos.

## FASE Y.2 — INTEGRAÇÃO COM GPS EXTERNO DE ALTA PRECISÃO
**Objetivo**: Implementar a capacidade do "App Offline de Campo" de se conectar a receptores GPS/GNSS externos via Bluetooth, ler os dados de alta precisão e usá-los para a geolocalização das feições coletadas.

### Entregas Detalhadas

#### 1. API de Conexão Bluetooth
*   **Sub-Objetivo**: Desenvolver a camada de software para descobrir, parear e se comunicar com dispositivos Bluetooth.
*   **Entregas**:
    *   **Integração com Web Bluetooth API**: Utilizar a API Web Bluetooth, disponível em navegadores modernos e em ambientes Electron, para gerenciar a conexão com os receptores GNSS.
    *   **UI de Gerenciamento de Dispositivos**:
        *   Uma tela no app para procurar dispositivos Bluetooth próximos.
        *   Botões para conectar/desconectar de um dispositivo selecionado.
        *   Exibição do status da conexão.

#### 2. Parser de Dados NMEA
*   **Sub-Objetivo**: Interpretar os dados brutos de geolocalização enviados pelo receptor GPS.
*   **Entregas**:
    *   **Lógica de Parsing NMEA (JavaScript)**: Desenvolver ou integrar uma biblioteca JavaScript para decodificar as sentenças NMEA (como `$GPGGA`, `$GPRMC`) que são transmitidas pelo receptor via Bluetooth.
    *   **Extração de Dados**: A lógica deve extrair informações cruciais, como:
        *   Latitude e Longitude de alta precisão.
        *   Altitude.
        *   Qualidade do sinal (Fix Type: GPS, DGPS, RTK Fixed, RTK Float).
        *   Número de satélites.
        *   Precisão horizontal e vertical estimada (HDOP, VDOP).

#### 3. Integração com a UI de Coleta de Dados
*   **Sub-Objetivo**: Substituir o GPS do dispositivo pelo GPS externo e fornecer feedback ao usuário.
*   **Entregas**:
    *   **Exibição de Status do GPS**:
        *   Um ícone na interface principal do app que indica o status da conexão com o GPS externo (desconectado, conectando, conectado).
        *   Ao tocar no ícone, exibir informações detalhadas: tipo de "fix", número de satélites e precisão estimada.
    *   **Uso das Coordenadas**: Quando um GPS externo estiver conectado e com um "fix" válido, a função de "marcar ponto" no mapa usará as coordenadas de alta precisão recebidas, em vez das coordenadas do GPS interno do celular/tablet.
    *   **Armazenamento de Metadados de Qualidade**: Salvar, nas `properties` do GeoJSON de cada feição coletada, os metadados de qualidade da coleta (ex: `fix_type`, `accuracy_m`), permitindo auditoria posterior.

### Critérios de Sucesso
*   ✔️ O App de Campo consegue se conectar a um receptor GPS Bluetooth que suporte o perfil SPP.
*   ✔️ A UI do app exibe o status da conexão e a qualidade do sinal GPS em tempo real.
*   ✔️ Ao coletar um ponto, as coordenadas usadas são as do GPS externo, resultando em dados de alta precisão no GeoJSON final.
*   ✔️ O app reverte para o GPS interno de forma graciosa se a conexão com o dispositivo externo for perdida.
