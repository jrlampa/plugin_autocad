@echo off
SETLOCAL EnableDelayedExpansion

REM ======================================================
REM  sisRUA - Master Build Pipeline
REM  Orquestra todo o processo de build: clean -> compile -> package -> installer
REM  
REM  Pipeline:
REM    [1/4] limpar_projeto.cmd      - Limpa artefatos antigos
REM    [2/4] build_release.cmd       - Compila C#, Frontend, Backend
REM    [3/4] organizar_projeto.cmd   - Estrutura o .bundle (chamado por build_release.cmd)
REM    [4/4] build_installer.cmd     - Gera instalador Windows (chamado por build_release.cmd)
REM ======================================================

SET ROOT=%~dp0
SET START_TIME=%TIME%

REM --- Cores para output (Windows 10+) ---
SET "RED=[91m"
SET "GREEN=[92m"
SET "YELLOW=[93m"
SET "BLUE=[94m"
SET "RESET=[0m"

echo.
echo %BLUE%========================================%RESET%
echo %BLUE%   sisRUA - Master Build Pipeline%RESET%
echo %BLUE%========================================%RESET%
echo.

REM ======================================
REM  Pre-Flight Checks
REM ======================================
echo %YELLOW%[PRE-FLIGHT] Verificando dependencias...%RESET%

REM --- Check 1: Inno Setup (ISCC.exe) ---
SET ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" SET ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if not exist "%ISCC%" (
    echo %RED%ERRO: Inno Setup 6 nao encontrado!%RESET%
    echo.
    echo Caminhos testados:
    echo   - C:\Program Files ^(x86^)\Inno Setup 6\ISCC.exe
    echo   - C:\Program Files\Inno Setup 6\ISCC.exe
    echo.
    echo Download: https://jrsoftware.org/isdl.php
    echo.
    exit /b 1
)
echo   %GREEN%OK%RESET%: Inno Setup encontrado em %ISCC%

REM --- Check 2: dotnet CLI ---
dotnet --version >nul 2>&1
if errorlevel 1 (
    echo %RED%ERRO: dotnet CLI nao encontrado!%RESET%
    echo Instale o .NET SDK: https://dotnet.microsoft.com/download
    exit /b 1
)
echo   %GREEN%OK%RESET%: dotnet CLI disponivel

REM --- Check 3: Node.js (para frontend) ---
node --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%AVISO: Node.js nao encontrado - build do frontend pode falhar%RESET%
) else (
    echo   %GREEN%OK%RESET%: Node.js disponivel
)

REM --- Check 4: Python (para backend) ---
python --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%AVISO: Python nao encontrado - build do backend pode falhar%RESET%
) else (
    echo   %GREEN%OK%RESET%: Python disponivel
)

echo.
echo %GREEN%Pre-flight checks concluidos.%RESET%
echo.

REM ======================================
REM  STEP 1: CLEAN
REM ======================================
echo %BLUE%========================================%RESET%
echo %BLUE%[1/4] CLEAN - Limpando projeto...%RESET%
echo %BLUE%========================================%RESET%
echo.

if not exist "%ROOT%limpar_projeto.cmd" (
    echo %YELLOW%AVISO: limpar_projeto.cmd nao encontrado - pulando limpeza%RESET%
    echo Se quiser limpeza automatica, crie o script limpar_projeto.cmd
    echo.
) else (
    call "%ROOT%limpar_projeto.cmd"
    if errorlevel 1 (
        echo %RED%ERRO: Falha na limpeza do projeto!%RESET%
        echo Verifique erros acima e tente novamente.
        exit /b 1
    )
    echo %GREEN%OK: Limpeza concluida.%RESET%
    echo.
)

REM ======================================
REM  STEP 2-4: BUILD RELEASE
REM ======================================
echo %BLUE%========================================%RESET%
echo %BLUE%[2/4] BUILD - Compilando projeto completo...%RESET%
echo %BLUE%========================================%RESET%
echo.
echo Executando build_release.cmd (inclui backend, frontend, bundle e installer)...
echo.

call "%ROOT%build_release.cmd"
if errorlevel 1 (
    echo.
    echo %RED%========================================%RESET%
    echo %RED%   ERRO: Build falhou!%RESET%
    echo %RED%========================================%RESET%
    echo.
    echo Detalhes do erro estao acima.
    echo.
    echo Troubleshooting:
    echo   1. Verifique se todas as dependencias estao instaladas
    echo   2. Execute 'limpar_projeto.cmd' e tente novamente
    echo   3. Verifique logs em logs\backend.log
    echo   4. Verifique erros de compilacao do C#
    echo.
    exit /b 1
)

echo.
echo %GREEN%OK: Build concluido com sucesso.%RESET%
echo.

REM ======================================
REM  STEP 3: VERIFY ARTIFACTS
REM ======================================
echo %BLUE%========================================%RESET%
echo %BLUE%[3/4] VERIFY - Verificando artefatos...%RESET%
echo %BLUE%========================================%RESET%
echo.

REM --- Verifica Bundle ---
if not exist "%ROOT%release\sisRUA.bundle\PackageContents.xml" (
    echo %RED%ERRO: Bundle nao encontrado em release\sisRUA.bundle\%RESET%
    echo O script organizar_projeto.cmd pode ter falhado.
    exit /b 1
)
echo   %GREEN%OK%RESET%: Bundle estruturado em release\sisRUA.bundle\

REM --- Verifica DLLs Multi-Target ---
if not exist "%ROOT%release\sisRUA.bundle\Contents\net48\sisRUA.dll" (
    echo %YELLOW%AVISO: sisRUA.dll (net48) nao encontrado%RESET%
)
if not exist "%ROOT%release\sisRUA.bundle\Contents\net8.0-windows\sisRUA.dll" (
    echo %YELLOW%AVISO: sisRUA.dll (net8.0-windows) nao encontrado%RESET%
)

REM --- Verifica Frontend ---
if not exist "%ROOT%release\sisRUA.bundle\Contents\frontend\dist\index.html" (
    echo %YELLOW%AVISO: Frontend dist nao encontrado%RESET%
)

REM --- Verifica Backend ---
REM Nota: backend pode estar como fonte Python ou EXE empacotado
if exist "%ROOT%release\sisRUA.bundle\Contents\backend\backend\api.py" (
    echo   %GREEN%OK%RESET%: Backend Python (fonte) encontrado
) else if exist "%ROOT%release\sisRUA.bundle\Contents\backend\sisrua_backend.exe" (
    echo   %GREEN%OK%RESET%: Backend EXE (PyInstaller) encontrado
) else (
    echo %YELLOW%AVISO: Backend nao encontrado (nem fonte nem EXE)%RESET%
)

echo.

REM ======================================
REM  STEP 4: LOCATE INSTALLER
REM ======================================
echo %BLUE%========================================%RESET%
echo %BLUE%[4/4] PACKAGE - Localizando instalador...%RESET%
echo %BLUE%========================================%RESET%
echo.

REM O build_release.cmd ja chama o build_installer.cmd
REM Vamos verificar se o instalador foi gerado

SET INSTALLER_DIR=%ROOT%installer\out
SET INSTALLER_FOUND=0

if exist "%INSTALLER_DIR%\sisRUA-Setup-*.exe" (
    SET INSTALLER_FOUND=1
    echo %GREEN%OK: Instalador gerado com sucesso!%RESET%
    echo.
    echo %GREEN%========================================%RESET%
    echo %GREEN%   BUILD COMPLETO - SUCESSO!%RESET%
    echo %GREEN%========================================%RESET%
    echo.
    echo Localizacao do instalador:
    echo   %INSTALLER_DIR%\
    echo.
    for %%F in ("%INSTALLER_DIR%\sisRUA-Setup-*.exe") do (
        echo   Arquivo: %%~nxF
        echo   Tamanho: %%~zF bytes
    )
    echo.
) else if exist "%ROOT%tools\out\sisRUA-Setup-*.exe" (
    SET INSTALLER_FOUND=1
    echo %GREEN%OK: Instalador gerado com sucesso!%RESET%
    echo.
    echo %GREEN%========================================%RESET%
    echo %GREEN%   BUILD COMPLETO - SUCESSO!%RESET%
    echo %GREEN%========================================%RESET%
    echo.
    echo Localizacao do instalador:
    echo   %ROOT%tools\out\
    echo.
    for %%F in ("%ROOT%tools\out\sisRUA-Setup-*.exe") do (
        echo   Arquivo: %%~nxF
        echo   Tamanho: %%~zF bytes
    )
    echo.
) else (
    echo %YELLOW%AVISO: Instalador nao encontrado em localizacoes padrao%RESET%
    echo.
    echo Locais verificados:
    echo   - %INSTALLER_DIR%\
    echo   - %ROOT%tools\out\
    echo.
    echo O bundle ainda esta disponivel em:
    echo   %ROOT%release\sisRUA.bundle\
    echo.
)

REM ======================================
REM  BUILD SUMMARY
REM ======================================
SET END_TIME=%TIME%

echo %BLUE%========================================%RESET%
echo %BLUE%   Build Summary%RESET%
echo %BLUE%========================================%RESET%
echo.
echo Inicio: %START_TIME%
echo Fim:    %END_TIME%
echo.
echo Artefatos gerados:
echo   - Bundle:     release\sisRUA.bundle\

if %INSTALLER_FOUND%==1 (
    echo   - Instalador: %INSTALLER_DIR%\ (ou tools\out\^)
    echo.
    echo %GREEN%Pronto para distribuicao!%RESET%
) else (
    echo   - Instalador: NAO ENCONTRADO
    echo.
    echo %YELLOW%Bundle disponivel, mas instalador pode ter falhado.%RESET%
    echo Verifique logs acima para detalhes.
)

echo.
echo Para instalar manualmente:
echo   1. Copie release\sisRUA.bundle\ para:
echo      "%APPDATA%\Autodesk\ApplicationPlugins\sisRUA.bundle\"
echo   2. Reinicie o AutoCAD
echo.

endlocal
exit /b 0
