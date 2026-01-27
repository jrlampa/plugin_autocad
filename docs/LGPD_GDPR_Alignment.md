# Alinhamento do Projeto sisRUA com LGPD e GDPR

Este documento detalha como o projeto sisRUA e suas práticas de desenvolvimento estão alinhados com os princípios e requisitos da Lei Geral de Proteção de Dados (LGPD) do Brasil e do General Data Protection Regulation (GDPR) da União Europeia, focando nos aspectos técnicos e de documentação do software.

## 1. Princípios de Proteção de Dados (Art. 6º LGPD / Art. 5º GDPR)

### 1.1. Transparência e Aviso de Privacidade
*   **Cláusula Relevante**: Art. 6º, VI (Transparência) da LGPD; Art. 5º, 1 (a) (Licitude, lealdade e transparência) do GDPR.
*   **Contribuição do Projeto**: O plugin exibe um **aviso de privacidade explícito** (`MessageBox.Show` em `SisRuaPalette.cs`) no primeiro uso, informando o usuário sobre o tratamento de dados (geolocalização, importação de arquivos) e o acesso a serviços externos (OpenStreetMap). O usuário precisa aceitar para continuar usando a UI.
*   **Próximos Passos Sugeridos**:
    *   Garantir que a política de privacidade referenciada (`PRIVACY.md`) seja mantida atualizada e facilmente acessível.
    *   Avaliar se o consentimento via `MessageBox` é granular o suficiente para todas as operações de dados.

### 1.2. Finalidade e Adequação (Data Minimization)
*   **Cláusula Relevante**: Art. 6º, I (Finalidade) e II (Adequação) da LGPD; Art. 5º, 1 (c) (Minimização de dados) do GDPR.
*   **Contribuição do Projeto**: O `NFR-004 — Privacidade` estabelece "sem telemetria por padrão", garantindo que o projeto colete e processe apenas os dados estritamente necessários para a funcionalidade principal (gerar projetos CAD a partir de dados geográficos).
*   **Próximos Passos Sugeridos**:
    *   Documentar formalmente a finalidade específica de cada dado pessoal processado.
    *   Verificar periodicamente se a coleta e o uso de dados se mantêm estritamente necessários para a finalidade declarada.

### 1.3. Segurança (Integridade e Confidencialidade)
*   **Cláusula Relevante**: Art. 6º, VII (Segurança) da LGPD; Art. 5º, 1 (f) (Integridade e confidencialidade) do GDPR.
*   **Contribuição do Projeto**:
    *   **Controles de Acesso**: Mecanismo de `BackendAuthToken` para proteger a comunicação com o backend (NFR-001), conforme detalhado em `docs/ISO_27001_Alignment.md`.
    *   **Logging**: O logging robusto (`SisRuaPlugin.cs`, `SisRuaCommands.cs`) ajuda na detecção de anomalias e incidentes de segurança.
    *   **Segurança no Desenvolvimento**: Práticas de desenvolvimento seguro, SAST e SCA implementadas no pipeline de CI/CD.
    *   **Qualidade dos Dados Geométricos (FASE 1.5.2)**: A limpeza e simplificação de geometria OSM ajudam a garantir a integridade dos dados espaciais no CAD, reduzindo erros e ambiguidades.
*   **Próximos Passos Sugeridos**: Consultar `docs/ISO_27001_Alignment.md` para melhorias contínuas na segurança.

## 2. Mapeamento de Dados e Fluxo de Dados Pessoais no Projeto

Um "mapeamento de dados" detalhado é uma etapa organizacional, mas podemos descrever o fluxo técnico de dados pessoais dentro do projeto:

| Tipo de Dado Pessoal | Origem (Componente) | Processamento (Componente) | Armazenamento (Local) | Finalidade | Base Legal (Ex: Consentimento, Legítimo Interesse) |
| :------------------- | :------------------ | :------------------------- | :-------------------- | :--------- | :------------------------------------------------ |
| **Coordenadas Geográficas (Lat/Lon)** | UI (usuário), Arquivos GeoJSON (usuário), OSM (backend) | C# Plugin, Python Backend | Em memória, DWG, `%LOCALAPPDATA%\sisRUA\cache` (OSM) | Gerar/Desenhar projetos CAD; Cache de dados geográficos para desempenho. | Consentimento do usuário (ao usar a função) |
| **Token de Autorização do Backend** | C# Plugin (geração) | C# Plugin, Python Backend | `%LOCALAPPDATA%\sisRUA\backend_token.txt` | Autenticação local segura entre plugin e backend. | Legítimo Interesse (segurança interna do sistema) |
| **Dados de Logs (erros, avisos)** | C# Plugin, Python Backend | C# Plugin, Python Backend | `%LOCALAPPDATA%\sisRUA\logs` | Debugging, suporte técnico, auditoria de segurança. | Legítimo Interesse (manutenção e segurança do sistema) |
| **Dados do Sistema (SO, AutoCAD, Python)** | C# Plugin (para debug) | C# Plugin | Logs (local) | Informações de ambiente para depuração e suporte. | Legítimo Interesse (diagnóstico e melhoria do sistema) |

### 2.1. Locais de Armazenamento e Retenção

*   **Cache de Dados Geográficos**: `%LOCALAPPDATA%\sisRUA\cache` - Retenção: Variável, pode ser gerenciada pelo usuário (ex: comando para limpar cache).
*   **Tokens e PIDs de Backend**: `%LOCALAPPDATA%\sisRUA\backend_port.txt`, `backend_token.txt`, `backend_pid.txt` - Retenção: Até o encerramento do AutoCAD ou reinício do sistema/plugin.
*   **Logs**: `%LOCALAPPDATA%\sisRUA\logs` - Retenção: Não definida, sujeita a rotação ou política de retenção da organização.
*   **Banco de Dados de Projetos (FASE 1.5.1)**: `%LOCALAPPDATA%\sisRUA\projects.db` - Armazena detalhes de projetos salvos (`CadFeature`s), permitindo recuperação e redesenho. Retenção: Gerenciada pelo usuário.
*   **Arquivos DWG**: Persistidos pelo usuário, fora do controle direto do plugin após o desenho.

### 2.2. Acesso aos Dados

*   Todos os dados processados e armazenados localmente pelo plugin são acessíveis apenas pelo usuário da máquina onde o AutoCAD está em execução. Não há transmissão de dados pessoais para a nuvem ou para servidores externos (exceto dados OSM para o provedor OSM, que são públicos, mas a requisição pode ter origem geográfica).

## 3. Direitos dos Titulares de Dados (Art. 18 LGPD / Art. 15-22 GDPR)

*   **Descrição**: O titular tem direito a acesso, correção, exclusão, etc., de seus dados.
*   **Contribuição do Projeto**:
    *   **Transparência**: O aviso de privacidade já informa sobre o tratamento de dados.
    *   **Controle do Usuário**: Como o projeto é "offline-first" e os dados são processados e armazenados localmente (incluindo o banco de dados SQLite da FASE 1.5.1), o usuário tem controle direto sobre seus dados.
        *   **Acesso**: O usuário pode acessar os dados diretamente nos arquivos DWG, no banco de dados SQLite (`%LOCALAPPDATA%\sisRUA\projects.db`) e em `%LOCALAPPDATA%\sisRUA`.
        *   **Exclusão**: O usuário pode excluir os arquivos de cache, logs e o banco de dados de projetos localmente.
        *   **Limpar Dados Locais (FR-008)**: Foi proposto um novo requisito funcional para um comando no plugin que facilitará a exclusão de todos os dados gerados/armazenados pelo sisRUA em `%LOCALAPPDATA%\sisRUA` (cache, logs, tokens, **e o banco de dados de projetos**).
*   **Próximos Passos Sugeridos**:
    *   **Implementar o comando "Limpar Dados Locais" (FR-008)**.
    *   Garantir que a documentação (`PRIVACY.md`) informe claramente sobre esses direitos e como exercê-los.

## 4. Medidas de Segurança Adicionais (Revisão Contínua)

*   **Contribuição do Projeto**: O alinhamento com a ISO 27001 (`docs/ISO_27001_Alignment.md`) já endereça a segurança da informação, que é um pilar da LGPD/GDPR.
*   **Cobertura de Testes**: Novas suítes de testes foram adicionadas para LGPD/GDPR:
    *   **TC-MAN-011**: Verifica a exibição do aviso de privacidade no primeiro uso.
    *   **TC-MAN-012**: Confirma a ausência de telemetria ou tráfego de rede não autorizado.
    *   **TC-MAN-013**: Valida a acessibilidade dos dados locais armazenados pelo plugin.
    *   **TC-MAN-014**: Caso de teste para a futura funcionalidade "Limpar Dados Locais".
*   **Próximos Passos Sugeridos**:
    *   Realizar avaliações de impacto à proteção de dados (DPIA/RIPD) se novas funcionalidades com processamento de dados pessoais forem introduzidas.
    *   Revisar periodicamente as configurações de segurança e as práticas de manuseio de dados.

## 5. Resumo e Próximos Passos para o Projeto

O projeto sisRUA adota uma abordagem "privacidade by design" com sua filosofia "offline-first" e "sem telemetria por padrão". Para formalizar a conformidade com LGPD/GDPR, a organização precisará:

1.  **Formalizar a Política de Privacidade** (documento legal) baseada nas práticas do projeto.
2.  **Educar os usuários** sobre seus direitos e como exercê-los.
3.  **Implementar o comando "Limpar Dados Locais"** para facilitar o exercício do direito de exclusão.
4.  Realizar avaliações de impacto (DPIA/RIPD) quando necessário.
5.  Garantir que os contratos com terceiros (ex: provedores de serviços OSM, se houver) também estejam em conformidade.

Este documento servirá como um registro técnico das medidas de proteção de dados implementadas no projeto.
