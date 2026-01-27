# ROADMAP DA FASE 1.5.1 — PERSISTÊNCIA DE DADOS COM SQLITE — sisRUA

## Visão da Fase 1.5.1
Implementar um mecanismo de persistência de dados local usando SQLite para permitir a recuperação e redesenho rápido de projetos anteriores, sem depender de bibliotecas externas complexas.

## PRINCÍPIOS ARQUITETURAIS (Aplicáveis à Fase)
*   **Offline-first**: O banco de dados SQLite será local ao usuário e não dependerá de conexão à internet.
*   **Custo Zero / Sem dependências complexas**: Utilizar o SQLite (que é leve e embeddável) com o mínimo de bibliotecas externas possíveis (ex: `System.Data.SQLite` para .NET).
*   **Dados de Projeto Controlados**: As informações persistidas estarão sob controle direto do usuário e do plugin.
*   **Separação clara de responsabilidades**:
    *   **C# (Plugin AutoCAD)**: Responsável por gerenciar a conexão com o SQLite, armazenar os dados dos `CadFeature`s desenhados e recuperá-los para redesenho.
    *   **Python (Backend)**: Menor envolvimento direto com a persistência neste momento, a menos que o backend precise de dados históricos de projetos.

## FASE 1.5.1 — PERSISTÊNCIA DE DADOS COM SQLITE
**Objetivo**: Criar um sistema de persistência local para armazenar e recuperar dados de projetos (featurers CAD desenhadas) de forma eficiente.

### Entregas Detalhadas

#### 1. Definição do Esquema de Banco de Dados SQLite
*   **Sub-Objetivo**: Projetar a estrutura da(s) tabela(s) no SQLite para armazenar as informações de `CadFeature` e metadados do projeto.
*   **Entregas**:
    *   **Tabela `Projects`**:
        *   `project_id` (TEXT, PK, ex: A0XXXXXXX)
        *   `project_name` (TEXT)
        *   `creation_date` (DATETIME)
        *   `crs_out` (TEXT, EPSG do desenho)
    *   **Tabela `CadFeatures`**:
        *   `feature_id` (TEXT, PK)
        *   `project_id` (TEXT, FK para `Projects`)
        *   `feature_type` (TEXT, 'Polyline' ou 'Point')
        *   `layer` (TEXT)
        *   `name` (TEXT)
        *   `highway` (TEXT, opcional)
        *   `width_m` (REAL, opcional)
        *   `coords_xy_json` (TEXT, JSON da lista de `coords_xy` para Polyline)
        *   `insertion_point_xy_json` (TEXT, JSON da lista de `insertion_point_xy` para Point)
        *   `block_name` (TEXT, opcional para Point)
        *   `block_filepath` (TEXT, opcional para Point)
        *   `rotation` (REAL, opcional para Point)
        *   `scale` (REAL, opcional para Point)
        *   `original_geojson_properties_json` (TEXT, JSON de propriedades GeoJSON originais)

#### 2. Integração do SQLite no Plugin C#
*   **Sub-Objetivo**: Adicionar a capacidade de interagir com o banco de dados SQLite no C# sem dependências complexas.
*   **Entregas**:
    *   **Referência `System.Data.SQLite`**: Adicionar o pacote NuGet `System.Data.SQLite` ao projeto C#.
    *   **Classe `ProjectRepository`**: Uma nova classe auxiliar em C# para abstrair as operações CRUD (Create, Read, Update, Delete) com o banco de dados SQLite.
    *   **Caminho do Banco de Dados**: Definir o caminho para o arquivo `.db` (ex: `%LOCALAPPDATA%\sisRUA\projects.db`).

#### 3. Implementação do Armazenamento de Dados (Plugin C#)
*   **Sub-Objetivo**: Salvar os `CadFeature`s desenhados no banco de dados SQLite.
*   **Entregas**:
    *   **Modificação de `DrawCadFeatures`**: Após a transação de desenho ser commitada, adicionar lógica para:
        *   **Obter `project_id`**: Implementar um `PromptString` ou similar para o usuário fornecer um `project_id`. Se o usuário não fornecer, gerar automaticamente um ID sequencial (ex: `YYYYMMDDHHMMss` ou um GUID).
        *   Persistir o `project_id` e `crs_out` na tabela `Projects`.
        *   Iterar sobre todos os `CadFeature`s desenhados e salvá-los na tabela `CadFeatures`, convertendo listas de coordenadas para JSON.
    *   **Comando `SISRUA_SAVE_PROJECT`**: Um comando explícito para o usuário salvar o projeto atual no banco de dados, com a opção de fornecer um `project_id`.

#### 4. Implementação da Recuperação e Redesenho (Plugin C#)
*   **Sub-Objetivo**: Permitir que o usuário selecione um projeto salvo e redesenhe suas feições.
*   **Entregas**:
    *   **Novo Comando AutoCAD `SISRUA_RELOAD_PROJECT`**: Um comando para:
        *   Listar projetos salvos (IDs e nomes).
        *   Permitir que o usuário selecione um `project_id`.
        *   Recuperar todos os `CadFeature`s associados ao `project_id` do SQLite.
        *   Chamar a função `DrawCadFeatures` (ou uma variante dela) para redesenhar as feições no CAD.
    *   **Limpeza Antes do Redesenho**: Lógica para opcionalmente apagar o conteúdo anterior do Model Space ou desenhar em um novo desenho.

#### 5. Consideração (Adiada): Backup LISP para Redesenho
*   **Decisão**: A implementação de um sistema de backup LISP para redesenho completo é considerada de alta complexidade e **adiada para uma fase futura** (ex: FASE 3.1.1 "Recuperação e Auditoria"). O foco da FASE 1.5.1 será na persistência e recuperação via SQLite.

#### 6. Atualização da Estratégia de Testes
*   **Sub-Objetivo**: Garantir que as funcionalidades de persistência e recuperação sejam testadas.
*   **Entregas**:
    *   **Novos FRs/NFRs**: Adicionar requisitos em `qa/requirements.md` para persistência, recuperação e manuseio de dados de projeto.
    *   **Casos de Teste Manuais**: Adicionar casos de teste em `qa/manual/test-cases-manual.csv` para:
        *   Salvamento de projeto após o desenho.
        *   Recuperação de projeto existente.
        *   Redesenho de projeto salvo.
        *   Verificação da integridade dos dados salvos (blocos, polylines, propriedades).
    *   **Testes Automatizados (C#)**: Se possível, adicionar testes de unidade para a classe `ProjectRepository` e suas interações com o SQLite.

#### 6. Atualização do Roadmap Principal e Documentação
*   **Sub-Objetivo**: Integrar a FASE 1.5.1 no roadmap geral e nos documentos de conformidade.
*   **Entregas**:
    *   Atualizar `ROADMAP OFICIAL DE DESENVOLVIMENTO.txt` para incluir FASE 1.5.1.
    *   Atualizar `docs/ISO_9001_Alignment.md` e `docs/LGPD_GDPR_Alignment.md` com menções à persistência local e proteção de dados.

### Critérios de Sucesso da Fase 1.5.1
*   ✔️ Dados de `CadFeature` (polylines e blocos) são persistidos corretamente em um banco de dados SQLite local.
*   ✔️ Usuário pode recuperar e redesenhar projetos anteriores usando um `project_id`.
*   ✔️ A recuperação preserva as propriedades dos `CadFeature`s (tipo, camadas, coordenadas, metadados de bloco).
*   ✔️ O processo de persistência é transparente e não interfere na experiência de desenho principal.

### ORDEM DE EXECUÇÃO IMEDIATA (MÃO NA MASSA)
1.  **Instalar NuGet `System.Data.SQLite`** no projeto C#.
2.  **Definir e implementar a classe `ProjectRepository`** no plugin C#.
3.  **Implementar a lógica de salvamento** em `DrawCadFeatures`.
4.  **Criar o comando AutoCAD `SISRUA_SAVE_PROJECT`** para formalizar o salvamento.
5.  **Criar o comando AutoCAD `SISRUA_LOAD_PROJECT`** para formalizar o carregamento/redesenho.
