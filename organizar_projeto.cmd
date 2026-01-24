@echo off
SETLOCAL EnableDelayedExpansion

REM ======================================================
REM  Organiza um bundle de DEPLOY (sem node_modules)
REM  Saida: .\dist\sisRUA.bundle
REM ======================================================

SET ROOT=%~dp0
SET SRC_BUNDLE=%ROOT%sisRUA.bundle
REM Permite sobrescrever a pasta de saída (ex.: para evitar lock em pastas sincronizadas).
REM Exemplo:
REM   set SISRUA_OUT_ROOT=%CD%\release
REM   organizar_projeto.cmd
if defined SISRUA_OUT_ROOT (
  SET OUT_ROOT=%SISRUA_OUT_ROOT%
) else (
  SET OUT_ROOT=%ROOT%dist
)
SET OUT_BUNDLE=%OUT_ROOT%\sisRUA.bundle
SET OUT_CONTENTS=%OUT_BUNDLE%\Contents
SET BIN_DEBUG=%ROOT%bin\x64\Debug\net8.0-windows

echo [1/6] Preparando pasta de saida (deploy)...
if exist "%OUT_BUNDLE%" rd /s /q "%OUT_BUNDLE%"
if not exist "%OUT_CONTENTS%" mkdir "%OUT_CONTENTS%"

echo [2/6] Copiando PackageContents.xml...
if not exist "%SRC_BUNDLE%\PackageContents.xml" (
    echo ERRO: PackageContents.xml nao encontrado em %SRC_BUNDLE%
    pause
    exit /b 1
)
copy /Y "%SRC_BUNDLE%\PackageContents.xml" "%OUT_BUNDLE%\" >nul

echo [3/6] Copiando binarios .NET (plugin + dependencias)...
if not exist "%BIN_DEBUG%" (
    echo ERRO: Pasta de build nao encontrada: %BIN_DEBUG%
    echo Compile o projeto antes: Debug/x64.
    pause
    exit /b 1
)
copy /Y "%BIN_DEBUG%\*.dll" "%OUT_CONTENTS%" >nul
copy /Y "%BIN_DEBUG%\*.pdb" "%OUT_CONTENTS%" >nul
copy /Y "%BIN_DEBUG%\*.json" "%OUT_CONTENTS%" >nul
if exist "%BIN_DEBUG%\runtimes" (
    xcopy /E /I /Y "%BIN_DEBUG%\runtimes" "%OUT_CONTENTS%\runtimes" >nul
)

echo [4/6] Copiando backend Python...
if not exist "%SRC_BUNDLE%\Contents\backend" (
    echo ERRO: Backend nao encontrado em %SRC_BUNDLE%\Contents\backend
    pause
    exit /b 1
)
xcopy /E /I /Y "%SRC_BUNDLE%\Contents\backend" "%OUT_CONTENTS%\backend" >nul

echo [5/6] Copiando frontend (somente dist)...
if exist "%SRC_BUNDLE%\Contents\frontend\dist" (
    xcopy /E /I /Y "%SRC_BUNDLE%\Contents\frontend\dist" "%OUT_CONTENTS%\frontend\dist" >nul
) else (
    echo AVISO: Frontend build dist nao encontrado em %SRC_BUNDLE%\Contents\frontend\dist
    echo Gere o build do Vite e tente novamente.
)

echo [6/6] Copiando Resources (mapeamento, prancha, etc)...
if exist "%SRC_BUNDLE%\Contents\Resources" (
    xcopy /E /I /Y "%SRC_BUNDLE%\Contents\Resources" "%OUT_CONTENTS%\Resources" >nul
) else (
    echo AVISO: Resources nao encontrado em %SRC_BUNDLE%\Contents\Resources
)

echo.
echo ======================================================
echo ESTRUTURA ORGANIZADA COM SUCESSO!
echo Local: %OUT_BUNDLE%
echo ======================================================
if not defined SISRUA_NOPAUSE pause
