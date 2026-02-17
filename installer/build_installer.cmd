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
  echo - C:\Program Files x86\Inno Setup 6\ISCC.exe
  echo - C:\Program Files\Inno Setup 6\ISCC.exe
  exit /b 1
)

echo INFO: Ativando builds de compatibilidade para AutoCAD 2021 e 2024...
if "%SISRUA_BUILD_NET48_ACAD2021%"=="" set SISRUA_BUILD_NET48_ACAD2021=1
if "%SISRUA_BUILD_NET48_ACAD2024%"=="" set SISRUA_BUILD_NET48_ACAD2024=1

REM Gera release completo (backend EXE + bundle) em ..\release
call "%ROOT%..\build_release.cmd"
if errorlevel 1 (
  echo ERRO: falha ao gerar release.
  exit /b 1
)

if not exist "%ROOT%..\release\sisRUA.bundle\PackageContents.xml" (
  echo ERRO: Bundle nao encontrado em ..\release\sisRUA.bundle
  echo Rode primeiro: organizar_projeto.cmd com SISRUA_OUT_ROOT e tente novamente.
  exit /b 1
)

if not exist "%ROOT%out" mkdir "%ROOT%out"

set APP_VERSION=0.0.0
if exist "%ROOT%..\VERSION.txt" (
  for /f "usebackq delims=" %%v in ("%ROOT%..\VERSION.txt") do set APP_VERSION=%%v
)
echo Versao: %APP_VERSION%

echo Compilando instalador...
"%ISCC%" "%ROOT%sisRUA.iss" /DAppVersion=%APP_VERSION% /O"%ROOT%out"
if errorlevel 1 (
  echo ERRO: falha ao compilar o instalador via ISCC.
  exit /b 1
)

echo OK: instalador gerado em %ROOT%out
endlocal

