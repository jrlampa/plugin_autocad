# Instalador (EXE) do sisRUA

Este diretório contém um instalador **1‑clique** (Inno Setup) que copia o `sisRUA.bundle` para:

`C:\ProgramData\Autodesk\ApplicationPlugins\sisRUA.bundle`

Assim o AutoCAD carrega o plugin automaticamente, sem `NETLOAD`.

## Pré-requisitos (para compilar o instalador)

- Inno Setup 6 instalado (inclui `ISCC.exe`)

## Pré-requisito do usuário final

- O sisRUA precisa do **Microsoft Edge WebView2 Runtime (Evergreen)**.
  - O instalador detecta e, se necessário, abre o link oficial: `https://go.microsoft.com/fwlink/?LinkId=2124703`

## Como gerar o bundle e o instalador

1) Gere o bundle de deploy (recomendado: com backend EXE):

- execute `build_release.cmd` na raiz do projeto (ele cria `release\sisRUA.bundle`)
  - opcional: para evitar paths com espaços no build do PyInstaller, use:
    - `set SISRUA_BUILD_ROOT=C:\sisrua_build`

2) Compile o instalador:

- execute `installer\build_installer.cmd`

O executável final sairá em `installer\out\`.

## Versão do instalador

- A versão vem de `VERSION.txt` na raiz do projeto.
- Atualize esse arquivo antes de gerar um release.

