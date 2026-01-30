@echo off
SETLOCAL EnableDelayedExpansion

SET ROOT=%~dp0
SET OUT_ROOT=%ROOT%dist

echo [1/4] Limpando pastas de compilacao .NET...
if exist "%ROOT%bin" rd /s /q "%ROOT%bin"
if exist "%ROOT%obj" rd /s /q "%ROOT%obj"

echo [2/4] Removendo caches de Python (__pycache__)...
for /d /r "%ROOT%" %%d in (__pycache__) do (
    if exist "%%d" (
        echo Apagando: %%d
        rd /s /q "%%d"
    )
)

echo [3/4] Limpando arquivos temporarios do sistema...
del /q "%TEMP%\sisrua_*.geojson" 2>nul
del /q "%TEMP%\sisrua_*.dxf" 2>nul
del /q "%TEMP%\sisrua_download_*.dxf" 2>nul

echo [4/4] Limpando bundle de deploy (dist)...
if exist "%OUT_ROOT%" rd /s /q "%OUT_ROOT%"

echo.
echo ======================================================
echo LIMPEZA CONCLUIDA! Ambiente pronto para novo Build.
echo ======================================================
pause
