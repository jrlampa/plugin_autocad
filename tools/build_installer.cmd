@echo off
setlocal
set ROOT=%~dp0..

echo [Info] Gerando instalador (Inno Setup)...

REM Caminho padrao do ISCC. Pode ser sobrescrito por variavel de ambiente ISCC_PATH
if "%ISCC_PATH%"=="" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else (
    set "ISCC=%ISCC_PATH%"
)

if not exist "%ISCC%" (
    echo ERRO: Inno Setup compilador nao encontrado em "%ISCC%".
    echo Defina a variavel ISCC_PATH se estiver em outro local.
    exit /b 1
)

set APP_VERSION=0.0.0
if exist "%ROOT%\VERSION.txt" (
    for /f "usebackq delims=" %%v in ("%ROOT%\VERSION.txt") do set APP_VERSION=%%v
)
echo [Info] Versao do App: %APP_VERSION%

if not exist "%ROOT%\installer\out" mkdir "%ROOT%\installer\out"

"%ISCC%" "%ROOT%\installer\sisRUA.iss" /DAppVersion=%APP_VERSION% /O"%ROOT%\installer\out"
if errorlevel 1 (
    echo ERRO: falha ao compilar o instalador.
    exit /b 1
)

echo OK: Instalador gerado em %ROOT%\installer\out
endlocal
