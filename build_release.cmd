@echo off

setlocal

REM ======================================================
REM  Configuracao para Assinatura de Codigo Digital
REM  Pre-requisito: Windows SDK instalado (signtool.exe)
REM ======================================================
set CODE_SIGN_THUMBPRINT=
REM Exemplo: set CODE_SIGN_THUMBPRINT=SEU_THUMBPRINT_AQUI

REM Opcionalmente, o usuario pode configurar assinatura de codigo.
REM Para evitar problemas de parsing com parenteses em caminhos, NENHUMA
REM deteccao automatica de signtool.exe e feita aqui.
set SIGNSERVER_PATH=%SIGNSERVER_PATH%

if "%CODE_SIGN_THUMBPRINT%"=="" (
    echo AVISO: Variavel CODE_SIGN_THUMBPRINT nao definida. Nenhuma assinatura de codigo sera realizada.
) else if "%SIGNSERVER_PATH%"=="" (
    echo AVISO: CODE_SIGN_THUMBPRINT definido, mas SIGNSERVER_PATH nao configurado. Nenhuma assinatura sera realizada.
) else (
    echo INFO: Assinatura de codigo habilitada com signtool em "%SIGNSERVER_PATH%".
)


REM ======================================================
REM  Build completo para distribuicao
REM  - (opcional) build do backend EXE
REM  - bundle em release\
REM ======================================================

set ROOT=%~dp0
set CONFIG=Release
set PLUGIN_CSPROJ=%ROOT%src\plugin\sisRUA.csproj

dotnet build "%PLUGIN_CSPROJ%" -c Release -f net8.0-windows
if errorlevel 1 (
  echo ERRO: falha ao compilar o plugin net8.
  exit /b 1
)
call :SIGN_FILE "%ROOT%src\plugin\bin\x64\%CONFIG%\net8.0-windows\sisRUA_NET8.dll"

REM net48 (AutoCAD 2021) é opcional.
if "%SISRUA_BUILD_NET48_ACAD2021%"=="1" (
  echo Building net48 for AutoCAD 2021...
  dotnet build "%PLUGIN_CSPROJ%" -c Release -f net48 -p:SISRUA_INCLUDE_NET48=true -p:TargetAcadVersion=2021 -p:OutputPath="%ROOT%src\plugin\bin\x64\%CONFIG%\net48\2021"
  if errorlevel 1 (
    echo ERRO: falha ao compilar o plugin net48 para AutoCAD 2021. Verifique AutoCAD 2021 instalado e Acad2021Dir no csproj.
    exit /b 1
  )
  copy /Y "%ROOT%src\plugin\bin\x64\%CONFIG%\net48\2021\sisRUA_NET48_ACAD2021.dll" "%ROOT%src\plugin\bin\x64\%CONFIG%\net48\sisRUA_NET48_ACAD2021.dll" >nul
  call :SIGN_FILE "%ROOT%src\plugin\bin\x64\%CONFIG%\net48\sisRUA_NET48_ACAD2021.dll"
)

REM net48 (AutoCAD 2024) é opcional e depende das DLLs do AutoCAD 2024 instaladas.
if "%SISRUA_BUILD_NET48_ACAD2024%"=="1" (
  echo Building net48 for AutoCAD 2024...
  dotnet build "%PLUGIN_CSPROJ%" -c Release -f net48 -p:SISRUA_INCLUDE_NET48=true -p:TargetAcadVersion=2024 -p:OutputPath="%ROOT%src\plugin\bin\x64\%CONFIG%\net48\2024"
  if errorlevel 1 (
    echo ERRO: falha ao compilar o plugin net48 para AutoCAD 2024. Verifique AutoCAD 2024 instalado e Acad2024Dir no csproj.
    exit /b 1
  )
  copy /Y "%ROOT%src\plugin\bin\x64\%CONFIG%\net48\2024\sisRUA_NET48_ACAD2024.dll" "%ROOT%src\plugin\bin\x64\%CONFIG%\net48\sisRUA_NET48_ACAD2024.dll" >nul
  call :SIGN_FILE "%ROOT%src\plugin\bin\x64\%CONFIG%\net48\sisRUA_NET48_ACAD2024.dll"
)


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
call "%ROOT%organizar_projeto.cmd" <nul
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