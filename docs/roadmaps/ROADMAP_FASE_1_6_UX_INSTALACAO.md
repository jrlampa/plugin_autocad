# ROADMAP DA FASE 1.6 — APERFEIÇOAMENTO DA EXPERIÊNCIA DE INSTALAÇÃO E PRIMEIRO USO (UX)

## Visão da Fase 1.6
Garantir que a primeira impressão do usuário com o sisRUA seja impecável, profissional e extremamente simples. O processo de instalação e a primeira abertura do plugin devem ser tão fluidos que o usuário se sinta imediatamente confiante na qualidade do software, sem nunca ser exposto a detalhes técnicos da implementação, como a execução de um processo de backend.

## PRINCÍPIOS ARQUITETURAIS
*   **Abstração Total do Backend**: O usuário final não precisa saber que existe um backend Python. A experiência deve ser a de um plugin autocontido.
*   **Feedback Visual Contínuo**: Desde o clique no instalador até a interface do plugin estar 100% funcional, o usuário deve sempre ter um feedback visual do que está acontecendo.
*   **Identidade Visual Consistente**: A marca "sisRUA" deve estar presente de forma profissional em todos os pontos de contato, incluindo o instalador.

## FASE 1.6 — APERFEIÇOAMENTO DA EXPERIÊNCIA DE INSTALAÇÃO E PRIMEIRO USO
**Objetivo**: Refinar o processo de instalação e a inicialização do plugin para que seja completamente transparente e profissional, eliminando a janela de console do backend e melhorando a percepção de qualidade desde o primeiro contato.

### Entregas Detalhadas

#### 1. Execução Silenciosa do Backend
*   **Sub-Objetivo**: Fazer com que o `sisrua_backend.exe` seja iniciado em segundo plano sem que nenhuma janela de console apareça.
*   **Entregas**:
    *   **Modificação de `SisRuaPlugin.cs`**:
        *   Na função que inicia o processo do backend (ex: `StartBackendProcess`), configurar o `ProcessStartInfo` do .NET.
        *   Definir `CreateNoWindow = true` para suprimir a criação da janela do processo.
        *   Definir `WindowStyle = ProcessWindowStyle.Hidden` para garantir que a janela fique oculta.
    *   **Gerenciamento de Erros**: Melhorar a captura de erros na inicialização do backend, para que, se o processo falhar (mesmo oculto), o usuário receba uma mensagem de erro clara e útil na interface, em vez de simplesmente não funcionar.

#### 2. Identidade Visual do Instalador
*   **Sub-Objetivo**: Transformar o instalador Inno Setup de um assistente genérico para uma experiência de marca.
*   **Entregas**:
    *   **Criação de Ativos Gráficos**: Preparar imagens para o instalador:
        *   Um ícone (`.ico`) para o executável do instalador.
        *   Uma imagem para o cabeçalho ou lateral do assistente de instalação.
    *   **Modificação de `installer/sisRUA.iss`**:
        *   Adicionar as diretivas `WizardImageFile`, `WizardSmallImageFile` para incluir os gráficos.
        *   Adicionar a diretiva `SetupIconFile` para definir o ícone do instalador.
        *   Revisar todos os textos exibidos durante a instalação para garantir clareza e profissionalismo.

#### 3. Experiência de Carregamento Aprimorada (Frontend)
*   **Sub-Objetivo**: Evitar que o usuário veja uma tela branca ou parcialmente carregada enquanto o backend inicializa e a primeira conexão é estabelecida.
*   **Entregas**:
    *   **Modificação de `src/frontend/src/App.jsx`**:
        *   Implementar um estado de "inicialização" global.
        *   Enquanto o frontend espera pela primeira resposta bem-sucedida do backend (`/api/v1/health`), exibir uma "splash screen" ou um componente de carregamento centralizado com o logo do sisRUA e uma mensagem como "Inicializando sisRUA...".
        *   A interface principal só será renderizada após a confirmação de que o backend está pronto.

### Critérios de Sucesso
*   ✔️ Ao iniciar o AutoCAD e o plugin, nenhuma janela de console preta (do backend) aparece na tela.
*   ✔️ O executável do instalador possui um ícone customizado do sisRUA.
*   ✔️ As telas do assistente de instalação exibem a marca e o logo do sisRUA.
*   ✔️ Ao abrir a paleta do sisRUA pela primeira vez, o usuário vê uma tela de carregamento profissional em vez de uma página em branco.
*   ✔️ A experiência completa, do download ao uso, é fluida e transmite a imagem de um software de alta qualidade.
