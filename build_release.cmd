@echo off
setlocal

REM ======================================================
REM  Build completo para distribuicao
REM  - (opcional) build do backend EXE
REM  - bundle em release\
REM ======================================================

set ROOT=%~dp0
set PLUGIN_CSPROJ=%ROOT%src\plugin\sisRUA.csproj

echo [0/3] Build do plugin .NET (Release)...
REM net8 (AutoCAD 2025–2026) é obrigatório
dotnet build "%PLUGIN_CSPROJ%" -c Release -f net8.0-windows
if errorlevel 1 (
  echo ERRO: falha ao compilar o plugin net8.
  exit /b 1
)

REM net48 (AutoCAD 2024) é opcional e depende das DLLs do AutoCAD 2024 instaladas.
REM Para forçar, use:
REM   set SISRUA_BUILD_NET48=1
if "%SISRUA_BUILD_NET48%"=="1" (
  dotnet build "%PLUGIN_CSPROJ%" -c Release -f net48 -p:SISRUA_INCLUDE_NET48=true
  if errorlevel 1 (
    echo ERRO: falha ao compilar o plugin net48. Verifique AutoCAD 2024 instalado e Acad2024Dir no csproj.
    exit /b 1
  )
)

echo [1/3] Gerando backend EXE (opcional, mas recomendado)...
REM Em Release, queremos garantir que o EXE reflita o código atual do backend.
set SISRUA_REBUILD_BACKEND_EXE=1
call "%ROOT%tools\\build_backend_exe.cmd"
if errorlevel 1 (
  echo ERRO: falha ao gerar backend exe.
  exit /b 1
)

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

echo OK: release\\sisRUA.bundle pronto.
endlocal

