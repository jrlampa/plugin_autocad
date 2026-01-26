# Release e distribuição - Guia de Processo Controlado

## Objetivo

Gerar uma distribuição “de produção” com:

-   `sisRUA.bundle` pronto para `ApplicationPlugins`
-   backend empacotado (`sisrua_backend.exe`)
-   instalador 1‑clique (Inno Setup)

Este processo segue princípios de controle de qualidade para garantir a rastreabilidade e consistência das entregas.

## Controle de Versão e Nomenclatura

*   **Versão do Produto**: A versão atual do software é definida em `VERSION.txt`. Este arquivo deve ser atualizado de acordo com as diretrizes de versionamento semântico (MAJOR.MINOR.PATCH) antes de cada release.
*   **Tags Git**: Cada release oficial **DEVE** ser marcada com uma tag Git correspondente à versão do produto (ex: `v1.0.0`). Isso garante a rastreabilidade completa do código-fonte para a release.
*   **Nomeclatura dos Artefatos**: Os artefatos de build (DLLs, EXE do instalador) devem incorporar a versão do produto para fácil identificação.

## Passo a passo (recomendado)

1.  **Gerar o bundle de release (inclui backend EXE + smoke test)**:

    *   Atualize o `VERSION.txt` para a versão da release.
    *   Rode `build_release.cmd`.

    Saída:
    *   `release\sisRUA.bundle`

    Observação: o `build_release.cmd` executa o smoke test do backend automaticamente (modo `-SkipOsm`).

2.  **Controle de Builds Multi-alvo**

    O `build_release.cmd` agora permite gerar builds específicos para diferentes versões do AutoCAD, usando as seguintes variáveis de ambiente:

    *   **AutoCAD 2021-2023 (net48)**:
        ```bash
        set SISRUA_BUILD_NET48_ACAD2021=1 && build_release.cmd
        ```
        (Gera `sisRUA_NET48_ACAD2021.dll`)

    *   **AutoCAD 2024 (net48)**:
        ```bash
        set SISRUA_BUILD_NET48_ACAD2024=1 && build_release.cmd
        ```
        (Gera `sisRUA_NET48_ACAD2024.dll`)

    *   **AutoCAD 2025+ (net8)**:
        ```bash
        build_release.cmd
        ```
        (Gera `sisRUA_NET8.dll` por padrão)

    Certifique-se de executar os builds necessários para as plataformas que deseja suportar na release. O `organizar_projeto.cmd` irá coletar todos os DLLs gerados no bundle.

3.  **Gerar instalador (EXE)**

    Pré‑requisito:
    *   Inno Setup 6 instalado (inclui `ISCC.exe`)

    Depois rode:
    *   `installer\build_installer.cmd`

    Saída:
    *   `installer\out\sisRUA-Installer-<versão>.exe` (a versão é automaticamente lida do `VERSION.txt`)

4.  **Assinatura digital (obrigatório para distribuição controlada)**

    *   **Requisito**: Windows SDK instalado + Certificado de Assinatura de Código (Thumbprint configurado em `CODE_SIGN_THUMBPRINT` no `build_release.cmd`).
    *   Os scripts `build_release.cmd` já foram atualizados para assinar automaticamente as DLLs do plugin e o EXE do backend se a variável `CODE_SIGN_THUMBPRINT` estiver configurada.
    *   **Verificação**: Após o build, é crucial verificar a assinatura dos artefatos (`.dll`, `.exe`) usando `signtool verify /pa <arquivo>`.

## Aprovação de Release

Toda release oficial **DEVE** ser aprovada por [Cargo/Pessoa Responsável pela Qualidade ou Gerente de Projeto]. A aprovação implica na verificação de que:

*   Todos os testes relevantes foram executados e passaram (`qa/test-plan.md`, `qa/manual/execution-record.md`).
*   Nenhuma não-conformidade crítica está aberta.
*   A documentação (`VERSION.txt`, changelogs, etc.) está atualizada.
*   Os artefatos de release foram gerados e verificados (incluindo assinatura digital).

## Variáveis úteis

### `SISRUA_OUT_ROOT`

O script `organizar_projeto.cmd` aceita sobrescrever o diretório de saída.

Isso é útil para evitar lock/sincronização (Google Drive):

-   exemplo:
    -   `set SISRUA_OUT_ROOT=%CD%\release`
    -   `organizar_projeto.cmd`

### `SISRUA_BUILD_ROOT`

Onde o build do backend EXE (PyInstaller) vai gravar venv/temporários.
Útil para evitar falhas por **paths com espaços**:

-   exemplo:
    -   `set SISRUA_BUILD_ROOT=C:\sisrua_build`

### `SISRUA_REBUILD_BACKEND_EXE`

Força rebuild do `sisrua_backend.exe` mesmo se já existir:

-   `set SISRUA_REBUILD_BACKEND_EXE=1`


