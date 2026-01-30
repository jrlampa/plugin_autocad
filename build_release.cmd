@echo off

setlocal

REM ======================================================
REM  Configuracao para Assinatura de Codigo Digital
REM  Pre-requisito: Windows SDK instalado (signtool.exe)
REM ======================================================
set CODE_SIGN_THUMBPRINT=
REM Exemplo: set CODE_SIGN_THUMBPRINT=SEU_THUMBPRINT_AQUI

set SIGNSERVER_PATH=%SIGNSERVER_PATH%

if "%CODE_SIGN_THUMBPRINT%"=="" (
    echo AVISO: Variavel CODE_SIGN_THUMBPRINT nao definida. Nenhuma assinatura de codigo sera realizada.
) else if "%SIGNSERVER_PATH%"=="" (
    echo AVISO: CODE_SIGN_THUMBPRINT definido, mas SIGNSERVER_PATH nao configurado. Nenhuma assinatura sera realizada.
) else (
    echo INFO: Assinatura de codigo habilitada com signtool em "%SIGNSERVER_PATH%".
)


REM ======================================================
REM  Build completo para distribuicao (Multi-Targeting)
REM  - (opcional) build do backend EXE
REM  - bundle em release\
REM ======================================================

set ROOT=%~dp0
set CONFIG=Release
set PLUGIN_CSPROJ=%ROOT%src\plugin\sisRUA.csproj

echo [0.1/3] Compilando Multi-Target (net48 + net8.0-windows)...
dotnet build "%PLUGIN_CSPROJ%" -c Release -p:Platform=x64
if errorlevel 1 (
  echo ERRO: falha no dotnet build.
  exit /b 1
)

REM Assinando os binaires gerados
call :SIGN_FILE "%ROOT%src\plugin\bin\x64\%CONFIG%\net48\sisRUA.dll"
call :SIGN_FILE "%ROOT%src\plugin\bin\x64\%CONFIG%\net8.0-windows\sisRUA.dll"


echo [0.5/3] Build do frontend (Release)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\build_frontend.ps1"
if errorlevel 1 goto :SISRUA_FRONTEND_FAIL

echo [1/3] Gerando backend EXE (opcional, mas recomendado)...
REM Em Release, queremos garantir que o EXE reflita o código atual do backend.
set SISRUA_REBUILD_BACKEND_EXE=1
call "%ROOT%tools\\build_backend_exe.cmd"
if errorlevel 1 (
  echo ERRO: falha ao gerar backend exe.
  exit /b 1
)
call :SIGN_FILE "%ROOT%bundle-template\sisRUA.bundle\Contents\backend\sisrua_backend.exe"

echo [1.5/3] Smoke test do backend EXE (sem OSM)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\smoke_backend.ps1" -SkipOsm
if errorlevel 1 (
  echo ERRO: smoke test do backend falhou.
  exit /b 1
)

echo [2/3] Gerando bundle em release\\sisRUA.bundle...
set SISRUA_OUT_ROOT=%ROOT%release
set SISRUA_CONFIGURATION=Release
set SISRUA_NOPAUSE=1
call "%ROOT%tools\organizar_projeto.cmd" <nul
if errorlevel 1 (
  echo ERRO: falha ao empacotar o bundle via organizar_projeto.cmd.
  exit /b 1
)

echo [2.5/3] Verificando integridade dos artefatos...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\verify_release_artifacts.ps1"
if errorlevel 1 (
  echo ERRO: falha na verificacao de integridade dos artefatos.
  exit /b 1
)

echo [3/3] Gerando instalador...
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

set APP_VERSION=0.0.0
if exist "%ROOT%VERSION.txt" (
    for /f "usebackq delims=" %%v in ("%ROOT%VERSION.txt") do set APP_VERSION=%%v
)
if not exist "%ROOT%installer\out" mkdir "%ROOT%installer\out"
"%ISCC%" "%ROOT%installer\sisRUA.iss" /DAppVersion=%APP_VERSION% /O"%ROOT%installer\out"
if errorlevel 1 (
    echo ERRO: falha ao compilar o instalador.
    exit /b 1
)
echo OK: Instalador gerado em %ROOT%installer\out

:END_ISCC
echo OK: release\\sisRUA.bundle pronto.
goto :EOF

:SIGN_FILE
set SIGN_TARGET=%1
if not "%CODE_SIGN_THUMBPRINT%"=="" (
    if not "%SIGNSERVER_PATH%"=="" (
        echo INFO: Assinando digitalmente "%SIGN_TARGET%"...
        "%SIGNSERVER_PATH%" sign /fd SHA256 /sha1 %CODE_SIGN_THUMBPRINT% /tr http://timestamp.digicert.com /td SHA256 "%SIGN_TARGET%"
        if errorlevel 1 (
            echo ERRO: Falha ao assinar "%SIGN_TARGET%". Verifique o thumbprint e o certificado.
            exit /b 1
        )
    )
)
goto :EOF

endlocal

exit /b 0

:SISRUA_FRONTEND_FAIL
echo ERRO: falha ao gerar frontend (Vite). Sem isso o plugin cai em "modo minimo".
exit /b 1