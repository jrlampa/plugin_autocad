@echo off
SETLOCAL EnableDelayedExpansion

REM ======================================================
REM  Script de Limpeza Completa do Projeto sisRUA
REM  Remove todos os artefatos de build, caches, e prepara
REM  o repositorio para um build limpo (clean slate).
REM ======================================================

SET ROOT=%~dp0

echo.
echo ========================================
echo    sisRUA - Limpeza Completa
echo ========================================
echo.

REM ======================================
REM  1. Limpar builds do C# (.NET)
REM ======================================
echo [1/8] Limpando builds do plugin C#...

if exist "%ROOT%src\plugin\bin" (
    echo   - Removendo src\plugin\bin\...
    rd /s /q "%ROOT%src\plugin\bin" 2>nul
    if exist "%ROOT%src\plugin\bin" (
        echo   ! AVISO: Nao foi possivel remover completamente src\plugin\bin\
    )
)

if exist "%ROOT%src\plugin\obj" (
    echo   - Removendo src\plugin\obj\...
    rd /s /q "%ROOT%src\plugin\obj" 2>nul
    if exist "%ROOT%src\plugin\obj" (
        echo   ! AVISO: Nao foi possivel remover completamente src\plugin\obj\
    )
)

if exist "%ROOT%build\bin" (
    echo   - Removendo build\bin\...
    rd /s /q "%ROOT%build\bin" 2>nul
)

if exist "%ROOT%build\obj" (
    echo   - Removendo build\obj\...
    rd /s /q "%ROOT%build\obj" 2>nul
)

echo   OK: Builds C# limpos.

REM ======================================
REM  2. Limpar frontend (Node.js/Vite)
REM ======================================
echo [2/8] Limpando builds do frontend...

if exist "%ROOT%src\frontend\dist" (
    echo   - Removendo src\frontend\dist\...
    rd /s /q "%ROOT%src\frontend\dist" 2>nul
)

if exist "%ROOT%src\frontend\node_modules\.vite" (
    echo   - Removendo cache do Vite...
    rd /s /q "%ROOT%src\frontend\node_modules\.vite" 2>nul
)

REM Opcional: remover node_modules (descomente se quiser limpeza total)
REM if exist "%ROOT%src\frontend\node_modules" (
REM     echo   - Removendo node_modules (pode demorar)...
REM     rd /s /q "%ROOT%src\frontend\node_modules" 2>nul
REM )

echo   OK: Frontend limpo.

REM ======================================
REM  3. Limpar backend Python
REM ======================================
echo [3/8] Limpando builds do backend Python...

if exist "%ROOT%src\backend\dist" (
    echo   - Removendo src\backend\dist\...
    rd /s /q "%ROOT%src\backend\dist" 2>nul
)

if exist "%ROOT%src\backend\build" (
    echo   - Removendo src\backend\build\...
    rd /s /q "%ROOT%src\backend\build" 2>nul
)

REM Limpar cache do PyInstaller
if exist "%ROOT%src\backend\__pycache__" (
    echo   - Removendo __pycache__...
    rd /s /q "%ROOT%src\backend\__pycache__" 2>nul
)

REM Limpar .pyc recursivamente
echo   - Removendo arquivos .pyc...
for /r "%ROOT%src\backend" %%F in (*.pyc) do (
    del /q "%%F" 2>nul
)

REM Limpar diret?rios __pycache__ recursivamente
for /d /r "%ROOT%src\backend" %%D in (__pycache__) do (
    if exist "%%D" rd /s /q "%%D" 2>nul
)

echo   OK: Backend Python limpo.

REM ======================================
REM  4. Limpar bundles de sa?da
REM ======================================
echo [4/8] Limpando bundles e releases...

if exist "%ROOT%dist" (
    echo   - Removendo dist\...
    rd /s /q "%ROOT%dist" 2>nul
)

if exist "%ROOT%release" (
    echo   - Removendo release\...
    rd /s /q "%ROOT%release" 2>nul
)

if exist "%ROOT%release_new" (
    echo   - Removendo release_new\...
    rd /s /q "%ROOT%release_new" 2>nul
)

echo   OK: Bundles limpos.

REM ======================================
REM  5. Limpar instaladores
REM ======================================
echo [5/8] Limpando instaladores...

if exist "%ROOT%installer\out" (
    echo   - Removendo installer\out\...
    rd /s /q "%ROOT%installer\out" 2>nul
)

if exist "%ROOT%tools\out" (
    echo   - Removendo tools\out\...
    rd /s /q "%ROOT%tools\out" 2>nul
)

echo   OK: Instaladores limpos.

REM ======================================
REM  6. Limpar caches locais do sisRUA
REM ======================================
echo [6/8] Limpando caches locais...

if exist "%ROOT%cache" (
    echo   - Removendo cache\...
    rd /s /q "%ROOT%cache" 2>nul
)

if exist "%ROOT%logs" (
    echo   - Removendo logs\...
    rd /s /q "%ROOT%logs" 2>nul
)

echo   OK: Caches limpos.

REM ======================================
REM  7. Limpar arquivos tempor?rios
REM ======================================
echo [7/8] Limpando arquivos temporarios...

REM Remover arquivos de sa?da de build/teste
del /q "%ROOT%*.txt" 2>nul
del /q "%ROOT%build_*.txt" 2>nul
del /q "%ROOT%*_output.txt" 2>nul
del /q "%ROOT%test_out.txt" 2>nul

REM Remover .pytest_cache se existir
if exist "%ROOT%.pytest_cache" (
    rd /s /q "%ROOT%.pytest_cache" 2>nul
)

echo   OK: Temporarios limpos.

REM ======================================
REM  8. Limpar estado do NuGet (opcional)
REM ======================================
echo [8/8] Limpando cache do NuGet (opcional)...

REM Descomente para limpar cache global do NuGet
REM dotnet nuget locals all --clear

echo   - Pulando limpeza de cache global (descomente no script se necessario)
echo   OK: Concluido.

REM ======================================
REM  Finaliza??o
REM ======================================
echo.
echo ========================================
echo  Limpeza concluida com sucesso!
echo ========================================
echo.
echo O repositorio esta pronto para um build limpo.
echo Execute: build_all.cmd
echo.

endlocal
exit /b 0
