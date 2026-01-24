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

## Gerar instalador (EXE)

Pré‑requisito:

- Inno Setup 6 instalado (inclui `ISCC.exe`)

Depois rode:

- `installer\build_installer.cmd`

Saída:

- `installer\out\sisRUA-Installer.exe`

## Variáveis úteis

### `SISRUA_OUT_ROOT`

O script `organizar_projeto.cmd` aceita sobrescrever o diretório de saída.

Isso é útil para evitar lock/sincronização (Google Drive):

- exemplo:
  - `set SISRUA_OUT_ROOT=%CD%\release`
  - `organizar_projeto.cmd`

