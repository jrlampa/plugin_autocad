@echo off
setlocal

REM Entry point for sisRUA Backend (Non-PyInstaller)
REM Usage: sisrua_backend.bat --host <host> --port <port> ...

set BIN_DIR=%~dp0
cd /d "%BIN_DIR%"

REM 1. Identify Python Executable
REM Check for portable python in 'python' subfolder first
if exist "%BIN_DIR%python\python.exe" (
    set PY="%BIN_DIR%python\python.exe"
) else (
    REM Fallback to system python if not bundled
    set PY=python
)

REM 2. Execute Backend
REM prioritized order: standalone.py (obfuscated) -> standalone.pyc -> uvicorn fallback
if exist "%BIN_DIR%standalone.py" (
    %PY% "%BIN_DIR%standalone.py" %*
) else if exist "%BIN_DIR%standalone.pyc" (
    %PY% "%BIN_DIR%standalone.pyc" %*
) else (
    REM Fallback to module mode if standalone is missing
    %PY% -m uvicorn backend.api:app %*
)

if errorlevel 1 (
    echo [ERROR] Backend execution failed with code %errorlevel%
    exit /b %errorlevel%
)

endlocal
