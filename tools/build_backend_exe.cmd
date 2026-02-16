@echo off
setlocal

REM ======================================================
REM  Gera Contents\backend\sisrua_backend.exe via PyInstaller
REM  Objetivo: rodar backend sem Python instalado no usuário.
REM ======================================================

set ROOT_UNSAFE=%~dp0..
for %%i in ("%ROOT_UNSAFE%") do set ROOT=%%~fi
set BACKEND_SRC=%ROOT%\src\backend
set BACKEND_OUT=%ROOT%\bundle-template\sisRUA.bundle\Contents\backend
REM Por padrão, fazemos build fora do "Meu Drive" (path com espaços), pois venv/ensurepip/PyInstaller
REM tendem a falhar em caminhos com espaços em alguns ambientes.
REM Você pode sobrescrever com:
REM   set SISRUA_BUILD_ROOT=C:\algum_lugar
if defined SISRUA_BUILD_ROOT (
  set BUILD_ROOT=%SISRUA_BUILD_ROOT%
) else (
  set BUILD_ROOT=%SystemDrive%\sisrua_build
)

set BUILD_VENV=%BUILD_ROOT%\.venv-backend-build
set PY=%BUILD_VENV%\Scripts\python.exe
set BUILD_TMP=%BUILD_ROOT%\tmp
set DIST_TMP=%BUILD_ROOT%\pyinstaller-dist

REM Força temporários em um caminho sem espaços
if not exist "%BUILD_TMP%" mkdir "%BUILD_TMP%"
set TEMP=%BUILD_TMP%
set TMP=%BUILD_TMP%

echo Matando processos sisrua_backend.exe antigos...
taskkill /F /IM sisrua_backend.exe /T 2>nul


if not exist "%BACKEND_SRC%\standalone.py" (
  echo ERRO: standalone.py nao encontrado em %BACKEND_SRC%
  exit /b 1
)

REM --- Versionamento (lê VERSION.txt e cria .rc file para PyInstaller) ---
set APP_VERSION=0.0.0
if exist "%ROOT%\VERSION.txt" (
  for /f "usebackq delims=" %%v in ("%ROOT%\VERSION.txt") do set APP_VERSION=%%v
)
echo INFO: Usando versao do projeto: %APP_VERSION%

REM PyInstaller espera um arquivo .rc para incorporar a versao no EXE.
REM Criamos um temporario.
set VERSION_RC_FILE="%BUILD_TMP%\version.rc"
set MAJOR_VERSION=0
set MINOR_VERSION=0
set PATCH_VERSION=0
for /f "tokens=1-3 delims=." %%a in ("%APP_VERSION%") do (
  set MAJOR_VERSION=%%a
  set MINOR_VERSION=%%b
  set PATCH_VERSION=%%c
)

echo # UTF-8
echo #include "winver.h"> %VERSION_RC_FILE%
echo 1 VERSIONINFO>> %VERSION_RC_FILE%
echo FILEVERSION %MAJOR_VERSION%,%MINOR_VERSION%,%PATCH_VERSION%,0>> %VERSION_RC_FILE%
echo PRODUCTVERSION %MAJOR_VERSION%,%MINOR_VERSION%,%PATCH_VERSION%,0>> %VERSION_RC_FILE%
echo FILEFLAGSMASK 0x17>> %VERSION_RC_FILE%
echo #ifdef _DEBUG>> %VERSION_RC_FILE%
echo FILEFLAGS 0x1>> %VERSION_RC_FILE%
echo #else>> %VERSION_RC_FILE%
echo FILEFLAGS 0x0>> %VERSION_RC_FILE%
echo #endif>> %VERSION_RC_FILE%
echo BEGIN>> %VERSION_RC_FILE%
echo   BLOCK "StringFileInfo">> %VERSION_RC_FILE%
echo   BEGIN>> %VERSION_RC_FILE%
echo     BLOCK "040904b0">> %VERSION_RC_FILE%
echo     BEGIN>> %VERSION_RC_FILE%
echo       VALUE "CompanyName", "sisRUA">> %VERSION_RC_FILE%
echo       VALUE "FileDescription", "sisRUA Backend">> %VERSION_RC_FILE%
echo       VALUE "FileVersion", "%APP_VERSION%">> %VERSION_RC_FILE%
echo       VALUE "InternalName", "sisrua_backend">> %VERSION_RC_FILE%
echo       VALUE "LegalCopyright", "Copyright (C) sisRUA">> %VERSION_RC_FILE%
echo       VALUE "OriginalFilename", "sisrua_backend.exe">> %VERSION_RC_FILE%
echo       VALUE "ProductName", "sisRUA Backend">> %VERSION_RC_FILE%
echo       VALUE "ProductVersion", "%APP_VERSION%">> %VERSION_RC_FILE%
echo     END>> %VERSION_RC_FILE%
echo   END>> %VERSION_RC_FILE%
echo   BLOCK "VarFileInfo">> %VERSION_RC_FILE%
echo   BEGIN>> %VERSION_RC_FILE%
echo     VALUE "Translation", 0x0409, 0x04B0>> %VERSION_RC_FILE%
echo   END>> %VERSION_RC_FILE%
echo END>> %VERSION_RC_FILE%
REM --- Fim Versionamento ---

REM Se já existe um EXE pronto e não foi pedido rebuild, reutiliza.
REM Para forçar rebuild:
REM   set SISRUA_REBUILD_BACKEND_EXE=1
if not exist "%BACKEND_OUT%" mkdir "%BACKEND_OUT%"
if exist "%BACKEND_OUT%\sisrua_backend.exe" (
  if not "%SISRUA_REBUILD_BACKEND_EXE%"=="1" (
    echo AVISO: sisrua_backend.exe ja existe. Pulando rebuild. Use SISRUA_REBUILD_BACKEND_EXE=1 para forcar.
    echo OK: %BACKEND_OUT%\sisrua_backend.exe
    exit /b 0
  )
)

REM --- Build Hygiene (ISO 27001) ---
if "%SISRUA_CLEAN_BUILD%"=="1" (
  echo INFO: SISRUA_CLEAN_BUILD=1 detectado. Limpando ambiente de build...
  if exist "%BUILD_VENV%" rmdir /s /q "%BUILD_VENV%"
  if exist "%DIST_TMP%" rmdir /s /q "%DIST_TMP%"
)

if not exist "%PY%" (
  echo Criando venv de build: %BUILD_VENV%
  python -m venv "%BUILD_VENV%"
  if errorlevel 1 (
    echo AVISO: falha ao criar venv com pip. Tentando fallback --without-pip + ensurepip...
    if exist "%BUILD_VENV%" rmdir /s /q "%BUILD_VENV%" 2>nul
    python -m venv --without-pip "%BUILD_VENV%"
    if errorlevel 1 (
      echo ERRO: nao foi possivel criar o venv de build.
      exit /b 1
    )
    "%PY%" -m ensurepip --upgrade
    if errorlevel 1 (
      echo ERRO: ensurepip falhou no venv de build.
      exit /b 1
    )
  )
)

echo Instalando dependencias do build (pode demorar)...
REM Se o venv existir mas estiver sem pip, tenta recuperar via ensurepip.
"%PY%" -m pip --version >nul 2>nul
if errorlevel 1 (
  echo AVISO: pip ausente no venv. Tentando ensurepip...
  "%PY%" -m ensurepip --upgrade
  if errorlevel 1 (
    echo ERRO: pip nao esta disponivel no venv de build.
    exit /b 1
  )
)

"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r "%BACKEND_SRC%\requirements.txt"
"%PY%" -m pip install pyinstaller

echo [licenses] Auditando licencas do backend (pip-licenses)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\tools\audit_licenses_backend.ps1"
if errorlevel 1 (
  echo ERRO: auditoria de licencas falhou. Possivel GPL/LGPL/AGPL ou problema de coleta.
  exit /b 1
)

echo [IP-PROTECT] Running Obfuscation Engine (sisRUA GIS Core)...
set SISRUA_BUILD_ROOT=%BUILD_ROOT%
"%PY%" "%ROOT%\tools\obfuscate_backend.py"
if errorlevel 1 (
  echo ERRO: Falha na ofuscacao do codigo. Abortando build para proteger IP.
  exit /b 1
)

echo Preparando pasta de backend para o bundle...
if exist "%BACKEND_OUT%" rmdir /s /q "%BACKEND_OUT%" 2>nul
mkdir "%BACKEND_OUT%"

REM Copia o código ofuscado
xcopy /E /I /Y "%BUILD_ROOT%\obfuscated_backend\*" "%BACKEND_OUT%\" >nul

REM Copia o frontend dist (agora reside dentro do backend no novo modelo)
if exist "%ROOT%\src\frontend\dist" (
    mkdir "%BACKEND_OUT%\frontend\dist" 2>nul
    xcopy /E /I /Y "%ROOT%\src\frontend\dist\*" "%BACKEND_OUT%\frontend\dist\" >nul
)

REM Copia o launcher .bat
copy /Y "%BACKEND_SRC%\sisrua_backend.bat" "%BACKEND_OUT%\sisrua_backend.bat" >nul

REM Copia requirements.txt (caso precise de install no destino)
copy /Y "%BACKEND_SRC%\requirements.txt" "%BACKEND_OUT%\requirements.txt" >nul

echo OK: Fonte preparado em %BACKEND_OUT%
endlocal

