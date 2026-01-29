@echo off
SETLOCAL EnableDelayedExpansion

REM ======================================================
REM  Organiza um bundle de DEPLOY (Multi-Targeting)
REM  Saida: .\dist\sisRUA.bundle
REM ======================================================

SET ROOT=%~dp0
SET SRC_BUNDLE=%ROOT%bundle-template\sisRUA.bundle
if defined SISRUA_OUT_ROOT (
  SET OUT_ROOT=%SISRUA_OUT_ROOT%
) else (
  SET OUT_ROOT=%ROOT%dist
)
SET OUT_BUNDLE=%OUT_ROOT%\sisRUA.bundle
SET OUT_CONTENTS=%OUT_BUNDLE%\Contents
if defined SISRUA_CONFIGURATION (
  SET CONFIG=%SISRUA_CONFIGURATION%
) else (
  SET CONFIG=Debug
)

SET BIN_NET8=%ROOT%src\plugin\bin\x64\%CONFIG%\net8.0-windows
SET BIN_NET48=%ROOT%src\plugin\bin\x64\%CONFIG%\net48
SET FRONTEND_DIST=%ROOT%src\frontend\dist
SET SISRUA_STEP=

echo [1/6] Preparando pasta de saida (deploy)...
if exist "%OUT_BUNDLE%" (
  SET SISRUA_STEP=apagando bundle de saida
  rd /s /q "%OUT_BUNDLE%"
  if exist "%OUT_BUNDLE%" goto :SISRUA_FAIL
)
if not exist "%OUT_CONTENTS%" (
  SET SISRUA_STEP=criando pasta Contents
  mkdir "%OUT_CONTENTS%"
  if not exist "%OUT_CONTENTS%" goto :SISRUA_FAIL
)

REM --- Versionamento ---
set APP_VERSION=0.0.0
if exist "%ROOT%\VERSION.txt" (
  for /f "usebackq delims=" %%v in ("%ROOT%\VERSION.txt") do set APP_VERSION=%%v
)
echo INFO: Usando versao do projeto: %APP_VERSION%

echo [1.5/6] Atualizando AppVersion em PackageContents.xml...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\tools\update_package_contents_xml.ps1" -PackageContentsPath "%SRC_BUNDLE%\PackageContents.xml" -AppVersion "%APP_VERSION%"
if errorlevel 1 goto :SISRUA_FAIL

echo [2/6] Copiando PackageContents.xml...
copy /Y "%SRC_BUNDLE%\PackageContents.xml" "%OUT_BUNDLE%\" >nul
if errorlevel 1 goto :SISRUA_FAIL

echo [3/6] Copiando binarios .NET (Multi-Targeting)...

REM --- NET 8.0 (AutoCAD 2025+) ---
if not exist "%BIN_NET8%" (
    echo ERRO: Build net8.0-windows nao encontrado em %BIN_NET8%
    goto :SISRUA_FAIL
)
if not exist "%OUT_CONTENTS%\net8.0-windows" mkdir "%OUT_CONTENTS%\net8.0-windows"
echo   [net8.0-windows] Copiando...
xcopy /Y /I /E "%BIN_NET8%\*" "%OUT_CONTENTS%\net8.0-windows\" >nul
if errorlevel 1 goto :SISRUA_FAIL

REM --- NET 4.8 (AutoCAD 2021-2024) ---
if not exist "%BIN_NET48%" (
    echo ERRO: Build net48 nao encontrado em %BIN_NET48%
    goto :SISRUA_FAIL
)
if not exist "%OUT_CONTENTS%\net48" mkdir "%OUT_CONTENTS%\net48"
echo   [net48] Copiando...
xcopy /Y /I /E "%BIN_NET48%\*" "%OUT_CONTENTS%\net48\" >nul
if errorlevel 1 goto :SISRUA_FAIL


echo [4/6] Copiando backend Python...
if not exist "%SRC_BUNDLE%\Contents\backend" (
    echo ERRO: Backend nao encontrado
    exit /b 1
)
xcopy /E /I /Y "%SRC_BUNDLE%\Contents\backend" "%OUT_CONTENTS%\backend" >nul
if errorlevel 1 goto :SISRUA_FAIL

echo [5/6] Copiando frontend (dist)...
if exist "%FRONTEND_DIST%" (
    xcopy /E /I /Y "%FRONTEND_DIST%" "%OUT_CONTENTS%\frontend\dist" >nul
    if errorlevel 1 goto :SISRUA_FAIL
) else (
    echo AVISO: Frontend dist nao encontrado.
)

echo [5.5/6] Copiando Blocos CAD...
if exist "%ROOT%Blocks" (
    xcopy /E /I /Y "%ROOT%Blocks" "%OUT_CONTENTS%\Blocks" >nul
)

echo [6/6] Copiando Resources...
if exist "%SRC_BUNDLE%\Contents\Resources" (
    xcopy /E /I /Y "%SRC_BUNDLE%\Contents\Resources" "%OUT_CONTENTS%\Resources" >nul
)

echo.
echo ======================================================
echo ESTRUTURA ORGANIZADA COM SUCESSO!
echo Local: %OUT_BUNDLE%
echo ======================================================
if not defined SISRUA_NOPAUSE pause
exit /b 0

:SISRUA_FAIL
echo ERRO: falha durante %SISRUA_STEP%
exit /b 1
