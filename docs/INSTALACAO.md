# Instalação (usuário final)

## Objetivo

Instalar o plugin **sem NETLOAD**, via `.bundle`, com experiência **1‑clique**.

O instalador copia o `sisRUA.bundle` para:

- **Global (recomendado)**: `C:\ProgramData\Autodesk\ApplicationPlugins\sisRUA.bundle`

Quando o AutoCAD inicia, ele detecta o `PackageContents.xml` e carrega o plugin.

## Instalação via instalador (EXE)

1) Execute o instalador `sisRUA-Installer.exe`
2) Abra/reabra o AutoCAD
3) Rode o comando `SISRUA`

## Desinstalação

Use “Adicionar/Remover Programas” do Windows:

- Procure por **sisRUA (AutoCAD Plugin)** e desinstale.

Isso remove a pasta:

- `C:\ProgramData\Autodesk\ApplicationPlugins\sisRUA.bundle`

## Instalação manual (fallback)

Se precisar instalar manualmente:

1) Copie a pasta `sisRUA.bundle` para:
   - `C:\ProgramData\Autodesk\ApplicationPlugins\`
2) Abra/reabra o AutoCAD
3) Rode `SISRUA`

## Pré‑requisitos

- AutoCAD 64‑bit
- WebView2 Runtime (geralmente já presente no Windows 10/11; se faltar, instale o runtime da Microsoft)

## Backend

Em produção, o plugin dá preferência para executar o backend empacotado:

- `bundle-template\sisRUA.bundle\Contents\backend\sisrua_backend.exe` (código-fonte do backend fica em `src\backend`)

Assim **não depende de Python** instalado na máquina do usuário.

