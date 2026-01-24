# Release e distribuição

## Objetivo

Gerar uma distribuição “de produção” com:

- `sisRUA.bundle` pronto para `ApplicationPlugins`
- backend empacotado (`sisrua_backend.exe`)
- instalador 1‑clique (Inno Setup)

## Passo a passo (recomendado)

1) Gerar backend EXE (sem Python no usuário final):

- rode `tools\build_backend_exe.cmd`

2) Gerar o bundle de release:

- rode `build_release.cmd`

Saída:

- `release\sisRUA.bundle`

3) Smoke test do backend (sem AutoCAD):

- rode `powershell -ExecutionPolicy Bypass -File tools\smoke_backend.ps1 -SkipOsm`

## Gerar instalador (EXE)

Pré‑requisito:

- Inno Setup 6 instalado (inclui `ISCC.exe`)

Depois rode:

- `installer\build_installer.cmd`

Saída:

- `installer\out\sisRUA-Installer.exe`

## Assinatura digital (recomendado para App Store)

- rode `tools\sign_artifacts.cmd` (requer Windows SDK + certificado)

## Variáveis úteis

### `SISRUA_OUT_ROOT`

O script `organizar_projeto.cmd` aceita sobrescrever o diretório de saída.

Isso é útil para evitar lock/sincronização (Google Drive):

- exemplo:
  - `set SISRUA_OUT_ROOT=%CD%\release`
  - `organizar_projeto.cmd`

### `SISRUA_BUILD_ROOT`

Onde o build do backend EXE (PyInstaller) vai gravar venv/temporários.
Útil para evitar falhas por **paths com espaços**:

- exemplo:
  - `set SISRUA_BUILD_ROOT=C:\sisrua_build`

### `SISRUA_REBUILD_BACKEND_EXE`

Força rebuild do `sisrua_backend.exe` mesmo se já existir:

- `set SISRUA_REBUILD_BACKEND_EXE=1`

### `SISRUA_BUILD_NET48`

Força build do plugin para AutoCAD 2024 (net48). Depende das DLLs do AutoCAD 2024:

- `set SISRUA_BUILD_NET48=1`

