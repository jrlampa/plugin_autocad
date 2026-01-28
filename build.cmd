@echo off
setlocal

REM ======================================================
REM  sisRUA - Build unificado (faz-tudo)
REM  Substitui chamadas a vários .cmd separados.
REM
REM  Uso: build.cmd [acao]
REM  Acoes: clean | release | installer | sign | validate | all
REM
REM  clean     - Limpa bin, obj, __pycache__, dist, temp
REM  release   - Plugin + frontend + backend EXE + bundle em release\
REM  installer - Release + Inno Setup -> installer\out\sisRUA-Installer-*.exe
REM  sign      - Assina DLLs, EXE e instalador (requer certificado)
REM  validate  - Instala, verifica e desinstala o instalador (ambiente limpo)
REM  all       - release + installer + validate (default)
REM ======================================================

set ROOT=%~dp0
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=all"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\sisrua.ps1" -Action "%ACTION%"
set EXIT=%ERRORLEVEL%
endlocal
exit /b %EXIT%
