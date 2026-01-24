# Instalador (EXE) do sisRUA

Este diretório contém um instalador **1‑clique** (Inno Setup) que copia o `sisRUA.bundle` para:

`C:\ProgramData\Autodesk\ApplicationPlugins\sisRUA.bundle`

Assim o AutoCAD carrega o plugin automaticamente, sem `NETLOAD`.

## Pré-requisitos (para compilar o instalador)

- Inno Setup 6 instalado (inclui `ISCC.exe`)

## Como gerar o bundle e o instalador

1) Gere o bundle de deploy (recomendado: com backend EXE):

- execute `build_release.cmd` na raiz do projeto (ele cria `release\sisRUA.bundle`)

2) Compile o instalador:

- execute `installer\build_installer.cmd`

O executável final sairá em `installer\out\`.

