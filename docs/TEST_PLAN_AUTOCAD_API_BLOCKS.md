# Plano de Testes Automatizados para API AutoCAD - Blocos (FASE 1.5)

## 1. Objetivo

Este documento descreve a estratégia para testar automaticamente a funcionalidade de inserção de blocos do plugin C# com a API do AutoCAD, conforme implementado na FASE 1.5.

## 2. Desafios de Testes Automatizados em C# para AutoCAD API

Testar diretamente componentes que interagem profundamente com a API do AutoCAD em um ambiente de teste tradicional (fora de uma instância do AutoCAD) apresenta desafios significativos:

*   A API do AutoCAD depende de um contexto de execução ativo (documento, database, editor).
*   Muitos objetos da API não podem ser instanciados ou "mockados" facilmente sem uma instância real do AutoCAD.
*   Frameworks de teste (como xUnit, NUnit) podem ser usados, mas a orquestração para rodar testes *dentro* do AutoCAD ou com mocks complexos exige infraestrutura específica.

## 3. Estratégia de Testes para Blocos no Plugin C#

Dada a complexidade, a estratégia se baseará em uma combinação de testes de integração automatizados (se possível) e uma forte dependência de testes manuais e validação end-to-end.

### 3.1. Testes de Unidade/Integração (C#) - Visão Futura (Complexo)

*   **Abordagem**: Se um framework de teste para plugins AutoCAD se tornar disponível ou se uma estratégia de mocking da API do AutoCAD for desenvolvida, poderíamos implementar:
    *   **Teste de Unidade para `EnsureBlockDefinitionLoaded`**: Verificar se o método consegue carregar corretamente um `.dxf`/`.dwg` simulado e adicionar sua definição ao `BlockTable` mockado.
    *   **Teste de Unidade para `InsertBlock`**: Verificar se `BlockReference`s são instanciados corretamente com as propriedades esperadas.
    *   **Teste de Integração de Desenho**: Simular o fluxo de `DrawCadFeatures` para verificar a correta delegação para polylines e blocos.
*   **Ferramentas Potenciais**: xUnit/NUnit com frameworks de mocking (ex: Moq, NSubstitute) ou frameworks de teste específicos para AutoCAD (se existirem e forem acessíveis).
*   **Status**: Esta parte da automação é considerada de **alta complexidade e custo** para ser implementada no contexto atual, dado o acesso limitado a ambientes de teste da API do AutoCAD.

### 3.2. Validação End-to-End Automatizada (Complexo, mas Possível)

*   **Abordagem**: Utilizar ferramentas que permitam a automação da UI do AutoCAD e a inspeção do desenho gerado.
*   **Exemplos**: Testes baseados em scripts AutoLISP/VBA que possam ser executados após a chamada do plugin, ou ferramentas de automação de UI mais avançadas que interagem diretamente com o AutoCAD.
*   **Status**: Esta abordagem é viável, mas exige **investimento significativo** em ferramentas e desenvolvimento de scripts de automação específicos para o AutoCAD.

### 3.3. Dependência de Testes Existentes e Manuais (Abordagem Atual)

Para a validação da FASE 1.5, o projeto dependerá fortemente dos seguintes mecanismos:

*   **Testes Automatizados de Backend (Python)**:
    *   `src/backend/tests/test_api_auth_and_jobs.py`: Casos de teste para `_prepare_osm_compute` e `_prepare_geojson_compute` que verificam se o backend está gerando `CadFeature`s do tipo `Point` com os metadados de bloco corretos. **(Já implementado)**
*   **Testes Manuais do Plugin C# no AutoCAD Real**:
    *   `qa/manual/test-cases-manual.csv`: Os casos de teste **TC-MAN-018**, **TC-MAN-019** e **TC-MAN-020** foram criados especificamente para validar a funcionalidade de inserção de blocos de ponta a ponta dentro de uma instância real do AutoCAD.
    *   **Verificação Visual**: Esses testes validam a correta inserção, layer, escala, rotação e nome dos blocos no desenho, conforme configurado em `blocks_mapping.json`.
    *   **Logging**: O logging detalhado no plugin C# (`SisRuaCommands.cs`) auxiliará na depuração de falhas. **(Já implementado)**

## 4. Próximos Passos Sugeridos

1.  **Priorizar Testes Manuais**: Focar na execução rigorosa dos `TC-MAN-018` a `TC-MAN-020` com evidências detalhadas.
2.  **Investigar Ferramentas de Teste AutoCAD**: Se a automação em C# se tornar um requisito crítico, pesquisar e avaliar frameworks de teste específicos para a API do AutoCAD ou soluções de automação de UI para o AutoCAD.
3.  **Monitoramento de Logs**: Utilizar os logs gerados pelo plugin para identificar e corrigir problemas durante a fase de testes.
