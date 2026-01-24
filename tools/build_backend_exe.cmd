@echo off
setlocal

REM ======================================================
REM  Gera Contents\backend\sisrua_backend.exe via PyInstaller
REM  Objetivo: rodar backend sem Python instalado no usuário.
REM ======================================================

set ROOT=%~dp0..
set BACKEND_DIR=%ROOT%\sisRUA.bundle\Contents\backend
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

if not exist "%BACKEND_DIR%\standalone.py" (
  echo ERRO: standalone.py nao encontrado em %BACKEND_DIR%
  exit /b 1
)

REM Se já existe um EXE pronto e não foi pedido rebuild, reutiliza.
REM Para forçar rebuild:
REM   set SISRUA_REBUILD_BACKEND_EXE=1
if exist "%BACKEND_DIR%\sisrua_backend.exe" (
  if not "%SISRUA_REBUILD_BACKEND_EXE%"=="1" (
    echo AVISO: sisrua_backend.exe ja existe. Pulando rebuild. Use SISRUA_REBUILD_BACKEND_EXE=1 para forcar.
    echo OK: %BACKEND_DIR%\sisrua_backend.exe
    exit /b 0
  )
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
"%PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
"%PY%" -m pip install pyinstaller

echo Gerando sisrua_backend.exe...
REM Gera em uma pasta temporária e só substitui no final (mais seguro).
if exist "%DIST_TMP%" rmdir /s /q "%DIST_TMP%" 2>nul
if not exist "%DIST_TMP%" mkdir "%DIST_TMP%"
"%PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --name sisrua_backend ^
  --copy-metadata osmnx ^
  --copy-metadata pyproj ^
  --collect-data pyproj ^
  --distpath "%DIST_TMP%" ^
  --workpath "%ROOT%\\build\\pyinstaller-work" ^
  --specpath "%ROOT%\\build\\pyinstaller-spec" ^
  "%BACKEND_DIR%\\standalone.py"

if not exist "%DIST_TMP%\\sisrua_backend.exe" (
  echo ERRO: sisrua_backend.exe nao foi gerado.
  exit /b 1
)

copy /Y "%DIST_TMP%\\sisrua_backend.exe" "%BACKEND_DIR%\\sisrua_backend.exe" >nul
echo OK: %BACKEND_DIR%\\sisrua_backend.exe
endlocal

