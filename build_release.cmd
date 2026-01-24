@echo off
setlocal

REM ======================================================
REM  Build completo para distribuicao
REM  - (opcional) build do backend EXE
REM  - bundle em release\
REM ======================================================

set ROOT=%~dp0

echo [1/2] Gerando backend EXE (opcional, mas recomendado)...
call "%ROOT%tools\\build_backend_exe.cmd"
if errorlevel 1 (
  echo ERRO: falha ao gerar backend exe.
  exit /b 1
)

echo [2/2] Gerando bundle em release\\sisRUA.bundle...
set SISRUA_OUT_ROOT=%ROOT%release
set SISRUA_NOPAUSE=1
call "%ROOT%organizar_projeto.cmd" <nul

echo OK: release\\sisRUA.bundle pronto.
endlocal

