@echo off
setlocal
set ROOT=%~dp0..

REM Busca o instalador versionado
for %%F in (%ROOT%\installer\out\sisRUA-Installer-*.exe) do set IEXE=%%F

if not exist "%IEXE%" (
  echo ERRO: Instalador versionado não encontrado em %ROOT%\installer\out
  exit /b 1
)

REM Assina o instalador
REM Exemplo: signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a "%IEXE%"
echo Assinando instalador: %IEXE%
REM signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a "%IEXE%"

endlocal
