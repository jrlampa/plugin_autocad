# Alinhamento do Projeto sisRUA com ISO/IEC 27001:2022

Este documento descreve como o projeto sisRUA e seus artefatos técnicos contribuem para um Sistema de Gestão da Segurança da Informação (SGSI) em conformidade com a ISO/IEC 27001:2022. Focamos nos controles aplicáveis ao desenvolvimento de software e proteção de dados dentro do projeto.

## 1. Cláusulas ISO/IEC 27001 (Visão Geral)

Embora a ISO 27001 seja uma norma organizacional, os seguintes aspectos do projeto sisRUA são diretamente relevantes:

*   **5.3 Política de segurança da informação**: A abordagem de privacidade ("sem telemetria por padrão") e os mecanismos de autorização são evidências de uma política implícita.
*   **5.5 Deveres e responsabilidades para segurança da informação**: O uso de controle de versão (Git) e a rastreabilidade do QA definem responsabilidades.
*   **5.10 Uso aceitável da informação e outros ativos**: Implícito no design do plugin e uso de dados.
*   **5.12 Segurança física de longo prazo**: Não aplicável diretamente ao código, mas à infraestrutura de desenvolvimento.
*   **5.14 Login seguro**: Controles de autenticação/autorização com o backend.
*   **5.15 Controles de acesso**: Implementados na comunicação com o backend.
*   **5.16 Gerenciamento de direitos de acesso**: Relacionado aos tokens de autenticação.
*   **5.18 Informação da segurança da informação em sistemas de informação**: Logging detalhado.
*   **5.23 Desenvolvimento seguro**: Boas práticas de codificação.
*   **5.24 Testes de segurança em desenvolvimento e aceitação**: Testes de segurança.
*   **5.25 Segregação de ambientes de desenvolvimento, testes e produção**: Configuração de build (Debug/Release).
*   **5.26 Gerenciamento de segredos**: Armazenamento e uso de tokens.
*   **5.27 Requisitos para mudança**: Controle de versão Git.
*   **5.28 Auditoria de mudanças em configuração**: Controle de versão Git.

## 2. Controles de Segurança da Informação Implementados no Projeto

### 2.1. A.5.15 Controles de Acesso (5.15) & A.5.16 Gerenciamento de Direitos de Acesso (5.16)

*   **Descrição**: Garantir que o acesso aos sistemas e dados seja restrito a usuários autorizados.
*   **Contribuição do Projeto**:
    *   **Autorização Local (NFR-001)**: O backend Python exige um token de autorização (`X-SisRua-Token`) para endpoints sensíveis. Este token é gerado aleatoriamente e persistido localmente (`PersistBackendToken` em `SisRuaPlugin.cs`).
    *   **Mecanismo de Geração de Token**: O token é gerado usando `Guid.NewGuid().ToString("N")`, um método criptograficamente forte para geração de identificadores únicos.
    *   **Verificação de Autorização**: O `SisRuaPlugin.IsBackendAuthorized()` verifica se o token do cliente corresponde ao token esperado pelo backend.
*   **Próximos Passos Sugeridos**:
    *   Documentar a política de expiração/rotação de tokens (atualmente é por sessão, mas persistido para reconexão).
    *   Considerar o armazenamento seguro do token (ex: APIs de proteção de dados do Windows para evitar que seja lido por outros processos).

### 2.2. A.5.18 Informação da Segurança da Informação em Sistemas de Informação (Logging)

*   **Descrição**: Garantir que as informações de segurança da informação sejam registradas e protegidas.
*   **Contribuição do Projeto**:
    *   **Logging Detalhado**: Implementado um sistema de log baseado em arquivo (`sisRUA_plugin_[timestamp].log` em `%LOCALAPPDATA%\sisRUA\logs`) no `SisRuaPlugin.cs` e `SisRuaCommands.cs`.
    *   **Registro de Eventos**: O log registra eventos importantes como inicialização/término do plugin, status do backend, erros durante o processo de backend, falhas na localização de executáveis, etc.
    *   **Tratamento de Exceções**: Blocos `try-catch` robustos são usados para capturar e registrar exceções, auxiliando na detecção de atividades anormais ou falhas de segurança.
*   **Próximos Passos Sugeridos**:
    *   Avaliar a necessidade de registrar eventos específicos de segurança (ex: falhas de autenticação com o backend, tentativas de acesso a recursos não autorizados, se aplicável) com maior granularidade.
    *   Implementar rotação de logs ou política de retenção para gerenciamento de espaço e conformidade.
    *   Proteger os logs contra adulteração (ex: hash ou assinatura dos arquivos de log, se o requisito de integridade for alto).

### 2.3. A.5.23 Desenvolvimento Seguro (Secure Development)

*   **Descrição**: Integrar a segurança nos processos de desenvolvimento de software.
*   **Contribuição do Projeto**:
    *   **Práticas de Codificação Segura**: Uso de `Guid.NewGuid()` para tokens, `HttpClient` com timeout, tratamento robusto de caminhos de arquivo, uso de `try-catch` extensivo.
    *   **Separação de Responsabilidades**: A arquitetura divide responsabilidades entre frontend (UI), C# (orquestração/AutoCAD) e Python (GIS/conversão), o que pode ajudar a conter vulnerabilidades.
    *   **Privacidade by Design (NFR-004)**: "Sem telemetria por padrão" demonstra um compromisso com a privacidade desde o design. O aviso de privacidade na UI (`SisRuaPalette.cs`) informa o usuário sobre o tratamento de dados.
*   **Próximos Passos Sugeridos**:
    *   Integrar ferramentas de análise estática de código (SAST) no pipeline de CI/CD para identificar vulnerabilidades de segurança comuns (ex: injeção, XSS se aplicável no frontend).
    *   Realizar revisões de código focadas em segurança.
    *   Treinamento de desenvolvedores em boas práticas de codificação segura.

### 2.4. A.5.24 Testes de Segurança em Desenvolvimento e Aceitação

*   **Descrição**: Testar a segurança do software durante e após o desenvolvimento.
*   **Contribuição do Projeto**:
    *   **Testes Automatizados**:
        *   **SAST (Static Application Security Testing)**: `Bandit` é executado no backend Python (`ci_qa.yml`) para identificar vulnerabilidades estáticas no código.
        *   **SCA (Software Composition Analysis)**: `npm audit` (frontend) e `pip-audit` (backend) são executados (`ci_qa.yml`) para identificar vulnerabilidades em dependências de terceiros.
        *   Testes de unidade/integração (pytest, vitest) e E2E (Playwright) podem incluir cenários de teste de segurança (ex: validação de entrada, testes de autorização).
    *   **Testes Manuais**: Os casos de teste manual (`qa/manual/test-cases-manual.csv`) foram expandidos para incluir verificações de segurança:
        *   **TC-MAN-009 (Verificação de Autorização)**: Testa o mecanismo de autorização do backend.
        *   **TC-MAN-010 (Robustez de Payload)**: Verifica a resiliência do backend a payloads inválidos/malformados.
*   **Próximos Passos Sugeridos**:
    *   Considerar a realização de testes de penetração (pentests) ou varreduras de vulnerabilidade regulares.

### 2.5. A.5.26 Gerenciamento de Segredos (Secrets Management)

*   **Descrição**: Proteger segredos como chaves criptográficas e credenciais.
*   **Contribuição do Projeto**:
    *   **Token de Autorização**: O `BackendAuthToken` é gerado em tempo de execução e não armazenado em arquivos de configuração estáticos no código-fonte.
*   **Próximos Passos Sugeridos**:
    *   Avaliar se outras credenciais ou segredos são usados pelo backend (Python) e como são gerenciados (ex: variáveis de ambiente, ferramentas de gerenciamento de segredos).
    *   Garantir que o token não seja exposto em logs ou na comunicação.

## 3. Avaliação de Riscos e Oportunidades (Cláusula 6.1 ISO 27001)

*   **Contribuição do Projeto**: O `ROADMAP OFICIAL DE DESENVOLVIMENTO.txt` já aborda riscos e oportunidades de forma geral. Para a ISO 27001, o foco seria nos riscos à segurança da informação.
*   **Próximos Passos Sugeridos**:
    *   Realizar uma análise de risco formal para segurança da informação, identificando ativos, ameaças, vulnerabilidades e impactos.
    *   Documentar o plano de tratamento de riscos para segurança da informação.

## 4. Resumo e Próximos Passos para o Projeto

O sisRUA já incorpora vários controles e práticas que suportam a ISO 27001, especialmente nas áreas de controle de acesso, logging e desenvolvimento seguro. Para avançar na certificação, a organização precisará:

1.  **Formalizar a documentação** dos controles existentes e dos "Próximos Passos Sugeridos" listados acima.
2.  **Integrar** essas práticas de segurança no SGSI organizacional.
3.  **Realizar** auditorias internas e externas de segurança da informação.
4.  **Conduzir** uma análise de risco formal e documentar o tratamento de riscos.

Este documento servirá como evidência da conformidade do projeto com os requisitos técnicos de segurança da informação da ISO 27001.
