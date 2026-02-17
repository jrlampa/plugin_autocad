# ROADMAP DA FASE 1.5.2 — LIMPEZA E SIMPLIFICAÇÃO DE GEOMETRIA OSM — sisRUA

## Visão da Fase 1.5.2
Melhorar a qualidade dos desenhos CAD gerados a partir de dados OSM, resolvendo problemas de linhas sobrepostas, duplicadas ou excessivamente complexas, resultando em desenhos mais limpos, performáticos e utilizáveis.

## PRINCÍPIOS ARQUITETURAIS (Aplicáveis à Fase)
*   **Offline-first**: O processamento de limpeza será realizado localmente pelo plugin.
*   **Otimização de Geometria**: Reduzir a complexidade geométrica sempre que possível para melhorar o desempenho do AutoCAD.
*   **Preservação da Fidelidade**: A simplificação deve manter a precisão topológica essencial.
*   **Configurável**: Parâmetros de limpeza (ex: tolerância de simplificação) podem ser configuráveis.

## FASE 1.5.2 — LIMPEZA E SIMPLIFICAÇÃO DE GEOMETRIA OSM
**Objetivo**: Implementar lógica no plugin C# para processar e otimizar os `CadFeature`s do tipo Polyline provenientes de dados OSM antes de seu desenho no AutoCAD.

### Entregas Detalhadas

#### 1. Definição do Escopo da Limpeza
*   **Sub-Objetivo**: Identificar os tipos específicos de problemas geométricos a serem resolvidos.
*   **Entregas**:
    *   **Remoção de Polylines Duplicadas Exatas**: Identificar e remover polylines com geometrias idênticas (mesmos vértices na mesma ordem).
    *   **Fusão de Polylines Colineares/Contíguas**: Unir segmentos de polylines que são colineares e adjacentes em uma única polyline (se representarem a mesma feição lógica).
    *   **Simplificação de Polylines**: Reduzir o número de vértices em polylines complexas, mantendo a forma geral da feição (utilizando um algoritmo de tolerância, como Douglas-Peucker).

#### 2. Implementação da Lógica de Limpeza no Plugin C#
*   **Sub-Objetivo**: Desenvolver os algoritmos para os diferentes tipos de limpeza geométrica.
*   **Entregas**:
    *   **Classe Auxiliar `GeometryCleaner`**: Criar uma nova classe (ex: `SisRuaCommands.GeometryCleaner`) para encapsular as funções de limpeza.
    *   **Método `RemoveDuplicatePolylines`**: Recebe uma lista de `CadFeature`s e retorna uma lista sem duplicatas exatas.
    *   **Método `MergeContiguousPolylines`**: Recebe uma lista de `CadFeature`s e tenta fundir polylines que se conectam e são colineares.
    *   **Método `SimplifyPolyline`**: Implementar um algoritmo de simplificação (ex: Douglas-Peucker) para reduzir vértices de uma única polyline. Integrar essa chamada em um método que itera sobre `CadFeature`s.
    *   **Integração com `DrawCadFeatures`**: Chamar a lógica de limpeza na função `DrawCadFeatures` (ou em uma nova função orquestradora anterior a ela), antes que as entidades sejam de fato desenhadas.

#### 3. Configuração (Opcional)
*   **Sub-Objetivo**: Permitir controle sobre os parâmetros de limpeza.
*   **Entregas**:
    *   **Parâmetro de Tolerância**: Adicionar um parâmetro configurável (ex: via `SisRuaSettings` ou no `blocks_mapping.json`) para a tolerância da simplificação (Douglas-Peucker).

#### 4. Atualização da Estratégia de Testes
*   **Sub-Objetivo**: Garantir que a funcionalidade de limpeza seja testada.
*   **Entregas**:
    *   **Novos FRs/NFRs**: Adicionar requisitos em `qa/requirements.md` para a limpeza e otimização da geometria OSM.
    *   **Casos de Teste Manuais**: Adicionar casos de teste em `qa/manual/test-cases-manual.csv` para verificar:
        *   Redução de polylines em áreas com sobreposição ou adjacência excessiva.
        *   Qualidade visual do desenho após a simplificação.
        *   Comportamento em cenários extremos (ex: polylines muito complexas, muito simples).
    *   **Testes Automatizados (Python/C#)**: Adicionar testes de unidade para a lógica de limpeza, simulando `CadFeature`s e verificando a saída otimizada.

## Critérios de Sucesso da Fase 1.5.2
*   ✔️ Desenhos CAD gerados a partir de OSM apresentam menos linhas sobrepostas/duplicadas.
*   ✔️ Polylines são simplificadas sem perda significativa de detalhes importantes.
*   ✔️ A qualidade visual e o desempenho do desenho são aprimorados.
*   ✔️ O processo de limpeza é transparente e não exige intervenção manual do usuário.

## ORDEM DE EXECUÇÃO IMEDIATA (MÃO NA MASSA)
1.  **Criar a classe `GeometryCleaner`** (ou métodos auxiliares em `SisRuaCommands.cs`).
2.  **Implementar a remoção de duplicatas** e a fusão de polylines.
3.  **Integrar a chamada da limpeza** antes do desenho em `DrawCadFeatures`.
4.  **Atualizar `qa/requirements.md` e `qa/manual/test-cases-manual.csv`** com testes específicos.
