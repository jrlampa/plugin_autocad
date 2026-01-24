@echo off
setlocal

REM ======================================================
REM  Assinatura digital (signtool) - sisRUA
REM  Requer Windows SDK (signtool.exe) e certificado válido.
REM
REM  Opções:
REM    1) Certificado via PFX:
REM       set SISRUA_CERT_PFX=C:\caminho\cert.pfx
REM       set SISRUA_CERT_PASS=senha
REM
REM    2) Certificado no store (recomendado para CI):
REM       set SISRUA_CERT_THUMBPRINT=ABCDEF...
REM ======================================================

set ROOT=%~dp0..
set SIGNTOOL="C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"
if not exist %SIGNTOOL% set SIGNTOOL="C:\Program Files\Windows Kits\10\bin\x64\signtool.exe"

if not exist %SIGNTOOL% (
  echo ERRO: signtool.exe nao encontrado. Instale o Windows SDK.
  exit /b 1
)

set TS=http://timestamp.digicert.com

set SIGN_ARGS=/fd sha256 /tr %TS% /td sha256

if defined SISRUA_CERT_PFX (
  if not exist "%SISRUA_CERT_PFX%" (
    echo ERRO: PFX nao encontrado em %SISRUA_CERT_PFX%
    exit /b 1
  )
  set CERT_ARGS=/f "%SISRUA_CERT_PFX%"
  if defined SISRUA_CERT_PASS (
    set CERT_ARGS=%CERT_ARGS% /p "%SISRUA_CERT_PASS%"
  )
) else (
  if not defined SISRUA_CERT_THUMBPRINT (
    echo ERRO: Defina SISRUA_CERT_PFX ou SISRUA_CERT_THUMBPRINT.
    exit /b 1
  )
  set CERT_ARGS=/sha1 %SISRUA_CERT_THUMBPRINT%
)

set DLL8=%ROOT%\release\sisRUA.bundle\Contents\sisRUA_NET8.dll
set DLL48=%ROOT%\release\sisRUA.bundle\Contents\sisRUA_NET48.dll
set BEXE=%ROOT%\release\sisRUA.bundle\Contents\backend\sisrua_backend.exe
set IEXE=%ROOT%\installer\out\sisRUA-Installer.exe

echo Assinando artefatos...

if exist "%DLL8%" %SIGNTOOL% sign %SIGN_ARGS% %CERT_ARGS% "%DLL8%"
if exist "%DLL48%" %SIGNTOOL% sign %SIGN_ARGS% %CERT_ARGS% "%DLL48%"
if exist "%BEXE%" %SIGNTOOL% sign %SIGN_ARGS% %CERT_ARGS% "%BEXE%"
if exist "%IEXE%" %SIGNTOOL% sign %SIGN_ARGS% %CERT_ARGS% "%IEXE%"

echo OK: assinatura concluida (arquivos existentes foram assinados).
endlocal

