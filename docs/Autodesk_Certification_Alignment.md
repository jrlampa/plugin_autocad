# Alinhamento do Projeto sisRUA com os Requisitos de Certificação Autodesk

Este documento detalha como o projeto sisRUA se alinha com os requisitos para ser reconhecido como um "Autodesk Certified Application", focando nos aspectos técnicos e de documentação do software.

## Requisitos de Certificação Autodesk e Alinhamento do sisRUA

### 1. Membro da Autodesk Developer Network (ADN)
*   **Requisito**: Ser membro da Autodesk Developer Network (ADN) é um pré-requisito para participar do programa de certificação.
*   **Alinhamento do Projeto**: Este é um requisito organizacional. O projeto não tem controle direto sobre a adesão à ADN.
*   **Próximos Passos Sugeridos**: Assegurar a adesão à ADN.

### 2. Integração Aprimorada com o AutoCAD
*   **Requisito**: O plugin deve demonstrar uma experiência de integração superior, incluindo presença dentro da janela do AutoCAD, manipulação nativa de arquivos e associatividade.
*   **Alinhamento do Projeto**:
    *   **Presença In-window**: O plugin utiliza um `PaletteSet` que hospeda uma interface WebView2 (`SisRuaPalette.cs`), proporcionando uma experiência de usuário integrada dentro da janela do AutoCAD, em vez de um aplicativo externo separado. **TC-MAN-015** verifica este aspecto.
    *   **Manipulação de Arquivos Nativos**: O plugin desenha diretamente no `ModelSpace` do AutoCAD (`SisRuaCommands.cs`), criando entidades nativas (polylines, MText) e gerenciando layers.
*   **Gaps & Próximos Passos Sugeridos**:
    *   **Associatividade e Notificação de Alterações (FR-009)**: Atualmente, o plugin desenha entidades, mas não gerencia explicitamente a associatividade entre os dados de origem (OSM/GeoJSON) e os objetos CAD, nem notifica o usuário sobre alterações nos arquivos de origem.
        *   **Implementação Futura**: O `FR-009` e o `TC-MAN-016` foram adicionados para guiar a implementação e teste desta funcionalidade crítica para a Autodesk.
    *   **UI/UX Consistente**: Garantir que a interface do usuário Web (WebView2) siga as diretrizes de UI/UX do AutoCAD/Autodesk, se houver.

### 3. Compatibilidade de Versão
*   **Requisito**: O plugin deve ser compatível com a versão anual mais recente do AutoCAD e com a versão imediatamente anterior (suporte a 2 versões).
*   **Alinhamento do Projeto**: O projeto já excedeu este requisito:
    *   **Multi-targeting**: O plugin é compilado para `.NET 8` (AutoCAD 2025/2026+) e `.NET Framework 4.8` (AutoCAD 2021-2024).
    *   **Suporte Abrangente**: A `PackageContents.xml` e o pipeline de build estão configurados para suportar AutoCAD 2021, 2024 e 2025/2026+, garantindo compatibilidade retroativa e futura.
    *   **Testes**: O `docs/TEST_PLAN_V0.1.1_AUTOCAD_COMPAT.md` detalha testes para validar a compatibilidade em múltiplas versões.
*   **Gaps & Próximos Passos Sugeridos**: Manter a estratégia de multi-targeting e validação em versões futuras do AutoCAD.

### 4. Qualidade e Estabilidade
*   **Requisito**: O aplicativo deve ser seguro, estável, completo e livre de defeitos, aderindo a leis e regulamentos relevantes.
*   **Alinhamento do Projeto**:
    *   **Processos de QA Robustos**: A pasta `qa/` contém requisitos (FR/NFR), plano de testes, testes automatizados (backend/frontend/E2E), e roteiros de testes manuais com evidências.
    *   **Rastreabilidade**: `traceability.csv` (implícito) vincula requisitos a testes.
    *   **Logging Aprimorado**: O logging baseado em arquivo (`SisRuaPlugin.cs`) facilita a depuração e o diagnóstico de problemas, contribuindo para a estabilidade.
    *   **Conformidade Legal**: `docs/ISO_9001_Alignment.md` e `docs/LGPD_GDPR_Alignment.md` demonstram o compromisso com a qualidade e conformidade regulatória.
    *   **Segurança**: SAST (Bandit) e SCA (npm audit, pip-audit) foram integrados para identificar e mitigar vulnerabilidades.
*   **Gaps & Próximos Passos Sugeridos**:
    *   **Resolução de Vulnerabilidades**: Endereçar e corrigir quaisquer vulnerabilidades identificadas pelas ferramentas SAST/SCA.
    *   **Documentação de Defeitos**: Formalizar o processo de gestão de defeitos (relato, priorização, correção, reteste). O `qa/manual/execution-record-template.md` já inclui uma seção para incidentes.

### 5. Documentação e Suporte
*   **Requisito**: O desenvolvedor é responsável por fornecer documentação abrangente, suporte ao cliente e garantia para o aplicativo certificado.
*   **Alinhamento do Projeto**:
    *   **Documentação Interna**: O projeto possui extensa documentação interna (`README.md`, `ROADMAP`, `qa/`, `docs/`) que serve de base.
    *   **Guia de Usuário e Suporte (FR-010)**: Foi proposto o `FR-010` para a criação de um guia de usuário e documentação de suporte.
*   **Gaps & Próximos Passos Sugeridos**:
    *   **Criação da Documentação (FR-010)**: Implementar o `FR-010` para criar um guia de usuário abrangente, incluindo instruções de instalação, uso, funcionalidades, solução de problemas comuns (FAQ). `TC-MAN-017` verificará este FR.
    *   **Canais de Suporte**: Estabelecer e documentar canais de suporte ao cliente.
    *   **Termos de Garantia**: Definir os termos de garantia para o aplicativo.

### 6. Tecnologia de Desenvolvimento
*   **Requisito**: Plugins .NET devem ser desenvolvidos usando linguagens compatíveis com .NET (C#) e a API .NET do AutoCAD. Suporte a .NET 8 para AutoCAD 2025+.
*   **Alinhamento do Projeto**: O projeto utiliza C# com o AutoCAD .NET API e já suporta .NET 8, estando em total conformidade com este requisito.

### 7. Processo de Certificação (Envio e Avaliação)
*   **Requisito**: Inclui aplicação, confirmação de elegibilidade, demonstração da funcionalidade (WebEx) e testes adicionais pela Autodesk.
*   **Alinhamento do Projeto**: Este é um processo externo e organizacional.
*   **Próximos Passos Sugeridos**: Organizar a demonstração e preparar-se para a avaliação da Autodesk, utilizando este documento de alinhamento e os artefatos de QA como evidência.

## Conclusão

O projeto sisRUA possui uma base técnica muito sólida para buscar a certificação Autodesk, especialmente em termos de compatibilidade de versão, qualidade, estabilidade e tecnologia de desenvolvimento. Os principais esforços adicionais no nível do projeto envolverão aprimorar a associatividade com o CAD, aprofundar a documentação de usuário/suporte e garantir que todas as vulnerabilidades de segurança sejam tratadas.