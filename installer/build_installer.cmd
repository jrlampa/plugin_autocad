@echo off
setlocal

REM ======================================================
REM  Build do instalador EXE (Inno Setup)
REM ======================================================

set ROOT=%~dp0
set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if not exist "%ISCC%" (
  echo ERRO: ISCC.exe nao encontrado. Instale o Inno Setup 6.
  echo Caminhos testados:
  echo - C:\Program Files (x86)\Inno Setup 6\ISCC.exe
  echo - C:\Program Files\Inno Setup 6\ISCC.exe
  exit /b 1
)

REM Gera bundle em ..\release para evitar lock em dist sincronizado
set SISRUA_OUT_ROOT=%ROOT%..\release
call "%ROOT%..\organizar_projeto.cmd" <nul

if not exist "%ROOT%..\release\sisRUA.bundle\PackageContents.xml" (
  echo ERRO: Bundle nao encontrado em ..\release\sisRUA.bundle
  echo Rode primeiro: organizar_projeto.cmd (com SISRUA_OUT_ROOT) e tente novamente.
  exit /b 1
)

if not exist "%ROOT%out" mkdir "%ROOT%out"

echo Compilando instalador...
"%ISCC%" "%ROOT%sisRUA.iss" /O"%ROOT%out"

echo OK: instalador gerado em %ROOT%out
endlocal

