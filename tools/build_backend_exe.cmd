@echo off
setlocal

REM ======================================================
REM  Gera Contents\backend\sisrua_backend.exe via PyInstaller
REM  Objetivo: rodar backend sem Python instalado no usuário.
REM ======================================================

set ROOT=%~dp0..
set BACKEND_DIR=%ROOT%\sisRUA.bundle\Contents\backend
set BUILD_VENV=%ROOT%\.venv-backend-build
set PY=%BUILD_VENV%\Scripts\python.exe

if not exist "%BACKEND_DIR%\standalone.py" (
  echo ERRO: standalone.py nao encontrado em %BACKEND_DIR%
  exit /b 1
)

if not exist "%PY%" (
  echo Criando venv de build: %BUILD_VENV%
  python -m venv "%BUILD_VENV%"
)

echo Instalando dependencias do build (pode demorar)...
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
"%PY%" -m pip install pyinstaller

echo Gerando sisrua_backend.exe...
"%PY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --name sisrua_backend ^
  --copy-metadata osmnx ^
  --distpath "%BACKEND_DIR%" ^
  --workpath "%ROOT%\\build\\pyinstaller-work" ^
  --specpath "%ROOT%\\build\\pyinstaller-spec" ^
  "%BACKEND_DIR%\\standalone.py"

if not exist "%BACKEND_DIR%\\sisrua_backend.exe" (
  echo ERRO: sisrua_backend.exe nao foi gerado.
  exit /b 1
)

echo OK: %BACKEND_DIR%\\sisrua_backend.exe
endlocal

