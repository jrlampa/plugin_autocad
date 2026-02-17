# ROADMAP SUPLEMENTAR (FUTURO) — FASE D.2 — SINCRONIZAÇÃO BIDIRECIONAL (CAD ↔ GIS)

## Visão da Fase D.2
Quebrar a barreira do "fluxo de mão única" e transformar o sisRUA em uma verdadeira plataforma de edição geoespacial. O AutoCAD se tornará não apenas um destino para os dados GIS, mas também uma origem, permitindo que alterações feitas no ambiente CAD sejam sincronizadas de volta para a fonte de dados GIS, estabelecendo um ciclo de vida de dados completo e integrado.

## PRINCÍPIOS ARQUITETURAIS
*   **Rastreabilidade de Feições**: Cada entidade CAD desenhada pelo sisRUA deve manter um identificador único e persistente que a vincule à sua feição de origem no GIS.
*   **Detecção de Mudanças**: O sistema precisa de um mecanismo robusto para detectar quais entidades foram modificadas, criadas ou deletadas no AutoCAD.
*   **Resolução de Conflitos**: A arquitetura deve prever mecanismos para lidar com conflitos (ex: se o dado foi alterado tanto no CAD quanto na fonte GIS desde a última sincronização).
*   **Conectores de "Escrita"**: A lógica de "escrita" deve ser modular para suportar diferentes destinos (atualizar um arquivo GeoJSON, fazer um POST para uma API, commitar em um banco de dados PostGIS).

## FASE D.2 — SINCRONIZAÇÃO BIDIRECIONAL (CAD ↔ GIS)
**Objetivo**: Implementar a capacidade de detectar alterações feitas em entidades CAD (geometria e atributos) e sincronizar essas alterações de volta para a fonte de dados original.

### Entregas Detalhadas

#### 1. Rastreabilidade Persistente de Entidades
*   **Sub-Objetivo**: Garantir que cada entidade no CAD "saiba" a que feição GIS ela corresponde.
*   **Entregas**:
    *   **Uso de `XData` ou `ExtensionDictionary` (C#)**: Ao desenhar uma entidade (polyline, bloco), o plugin C# irá anexar metadados a ela, incluindo:
        *   `sisrua_feature_id`: Um ID único e global para a feição.
        *   `source_hash`: Um hash do estado original da geometria/atributos para detecção de mudanças.
    *   **Persistência**: Estes dados são salvos diretamente no objeto dentro do arquivo `.dwg`.

#### 2. Detecção de Mudanças no CAD
*   **Sub-Objetivo**: Criar um mecanismo para identificar o que mudou no desenho.
*   **Entregas**:
    *   **Novo Comando `SISRUA_SYNC`**: Um novo comando no AutoCAD.
    *   **Lógica de Verificação (C#)**:
        *   O comando irá iterar por todas as entidades no desenho que possuem os metadados `sisrua_feature_id`.
        *   Para cada entidade, ele comparará seu estado atual (geometria, atributos) com o `source_hash` armazenado.
        *   Ele irá gerar uma lista de "deltas" (mudanças):
            *   **Modificado**: Geometria ou atributos mudaram.
            *   **Deletado**: O `sisrua_feature_id` existia na última sincronização, mas a entidade não existe mais no DWG.
            *   **Novo**: Uma nova entidade foi criada no CAD (ex: uma rua desenhada manualmente).

#### 3. "Commit" das Mudanças para a Fonte de Dados
*   **Sub-Objetivo**: Enviar as mudanças detectadas para serem aplicadas na fonte de dados.
*   **Entregas**:
    *   **Endpoint de "Patch" no Backend (Python)**: Um novo endpoint na API (ex: `/api/v1/sync/patch_features`) que recebe a lista de "deltas".
    *   **Lógica de "Escrita" no Backend**:
        *   O backend receberá os deltas e, com base na fonte de dados original, aplicará as alterações.
        *   **Para Arquivos (GeoJSON/Shapefile)**: O backend pode criar uma nova versão do arquivo com as alterações aplicadas.
        *   **Para Bancos de Dados (PostGIS - fase futura)**: O backend executaria comandos `UPDATE`, `INSERT`, `DELETE` no banco de dados.

#### 4. Interface do Usuário para Sincronização
*   **Sub-Objetivo**: Fornecer ao usuário uma interface para revisar e confirmar as mudanças antes de sincronizar.
*   **Entregas**:
    *   **Painel "Sincronização" na UI**: Ao rodar `SISRUA_SYNC`, a UI do sisRUA exibiria um painel mostrando:
        *   Uma lista das entidades modificadas, novas e deletadas.
        *   Um "diff" visual ou textual para cada mudança.
    *   **Botão "Confirmar e Sincronizar"**: O usuário revisa as mudanças e aprova o "commit" para a fonte de dados.

### Critérios de Sucesso
*   ✔️ Entidades desenhadas pelo sisRUA no AutoCAD contêm metadados de rastreabilidade.
*   ✔️ O comando `SISRUA_SYNC` consegue detectar quais entidades foram movidas, modificadas ou deletadas.
*   ✔️ O usuário pode revisar as mudanças em uma UI antes de confirmá-las.
*   ✔️ Após a confirmação, a fonte de dados original (ex: um arquivo GeoJSON) é atualizada para refletir as mudanças feitas no CAD.
