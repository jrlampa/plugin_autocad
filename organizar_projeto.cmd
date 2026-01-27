@echo off
SETLOCAL EnableDelayedExpansion

REM ======================================================
REM  Organiza um bundle de DEPLOY (sem node_modules)
REM  Saida: .\dist\sisRUA.bundle
REM ======================================================

SET ROOT=%~dp0
SET SRC_BUNDLE=%ROOT%bundle-template\sisRUA.bundle
REM Permite sobrescrever a pasta de saída (ex.: para evitar lock em pastas sincronizadas).
REM Exemplo:
REM   set SISRUA_OUT_ROOT=%CD%\release
REM   organizar_projeto.cmd
if defined SISRUA_OUT_ROOT (
  SET OUT_ROOT=%SISRUA_OUT_ROOT%
) else (
  SET OUT_ROOT=%ROOT%dist
)
SET OUT_BUNDLE=%OUT_ROOT%\sisRUA.bundle
SET OUT_CONTENTS=%OUT_BUNDLE%\Contents
if defined SISRUA_CONFIGURATION (
  SET CONFIG=%SISRUA_CONFIGURATION%
) else (
  SET CONFIG=Debug
)
SET BIN_NET8=%ROOT%src\plugin\bin\x64\%CONFIG%\net8.0-windows
SET BIN_NET48=%ROOT%src\plugin\bin\x64\%CONFIG%\net48
SET FRONTEND_DIST=%ROOT%src\frontend\dist
SET SISRUA_STEP=

echo [1/6] Preparando pasta de saida (deploy)...
if exist "%OUT_BUNDLE%" (
  SET SISRUA_STEP=apagando bundle de saida
  rd /s /q "%OUT_BUNDLE%"
  if exist "%OUT_BUNDLE%" goto :SISRUA_FAIL
)
if not exist "%OUT_CONTENTS%" (
  SET SISRUA_STEP=criando pasta Contents
  mkdir "%OUT_CONTENTS%"
  if not exist "%OUT_CONTENTS%" goto :SISRUA_FAIL
)

echo [2/6] Copiando PackageContents.xml...
if not exist "%SRC_BUNDLE%\PackageContents.xml" (
    echo ERRO: PackageContents.xml nao encontrado em %SRC_BUNDLE%
    pause
    exit /b 1
)
SET SISRUA_STEP=copiando PackageContents.xml
copy /Y "%SRC_BUNDLE%\PackageContents.xml" "%OUT_BUNDLE%\" >nul
if errorlevel 1 goto :SISRUA_FAIL

echo [3/6] Copiando binarios .NET (plugin + dependencias)...
if not exist "%BIN_NET8%" (
    echo ERRO: Pasta de build nao encontrada: %BIN_NET8%
    echo Compile o projeto antes: Debug/x64 net8.0-windows.
    pause
    exit /b 1
)

REM Copia o DLL net8 com nome esperado pelo PackageContents.xml
SET SISRUA_STEP=copiando sisRUA_NET8.dll
copy /Y "%BIN_NET8%\sisRUA_NET8.dll" "%OUT_CONTENTS%\sisRUA_NET8.dll" >nul
if errorlevel 1 goto :SISRUA_FAIL
if exist "%BIN_NET8%\sisRUA_NET8.pdb" (
    SET SISRUA_STEP=copiando sisRUA_NET8.pdb
    copy /Y "%BIN_NET8%\sisRUA_NET8.pdb" "%OUT_CONTENTS%\sisRUA_NET8.pdb" >nul
    if errorlevel 1 goto :SISRUA_FAIL
)

REM Copia dependências (WebView2 etc) do build net8
SET SISRUA_STEP=copiando dependencias dll do net8
xcopy /Y /I "%BIN_NET8%\*.dll" "%OUT_CONTENTS%\\" >nul
if errorlevel 1 goto :SISRUA_COPY_DLL_FAIL
SET SISRUA_STEP=copiando dependencias json do net8
xcopy /Y /I "%BIN_NET8%\*.json" "%OUT_CONTENTS%\\" >nul
if errorlevel 1 goto :SISRUA_FAIL
if exist "%BIN_NET8%\runtimes" (
    SET SISRUA_STEP=copiando runtimes WebView2
    xcopy /E /I /Y "%BIN_NET8%\runtimes" "%OUT_CONTENTS%\runtimes" >nul
    if errorlevel 1 goto :SISRUA_FAIL
)


REM Copia os DLLs net48 versionados (AutoCAD 2021, 2024, etc.), se existirem
for %%f in ("%BIN_NET48%\sisRUA_NET48_ACAD*.dll") do (
    if exist "%%f" (
        SET SISRUA_STEP=copiando %%~nxf
        copy /Y "%%f" "%OUT_CONTENTS%\" >nul
        if errorlevel 1 goto :SISRUA_FAIL
        if exist "%BIN_NET48%\%%~nf.pdb" (
            SET SISRUA_STEP=copiando %%~nf.pdb
            copy /Y "%BIN_NET48%\%%~nf.pdb" "%OUT_CONTENTS%\" >nul
            if errorlevel 1 goto :SISRUA_FAIL
        )
        echo OK: %%~nxf copiado.
    )
)

echo [4/6] Copiando backend Python...
if not exist "%SRC_BUNDLE%\Contents\backend" (
    echo ERRO: Backend nao encontrado em %SRC_BUNDLE%\Contents\backend
    pause
    exit /b 1
)
SET SISRUA_STEP=copiando backend
xcopy /E /I /Y "%SRC_BUNDLE%\Contents\backend" "%OUT_CONTENTS%\backend" >nul
if errorlevel 1 goto :SISRUA_FAIL

echo [5/6] Copiando frontend (somente dist)...
if exist "%FRONTEND_DIST%" (
    SET SISRUA_STEP=copiando frontend dist
    xcopy /E /I /Y "%FRONTEND_DIST%" "%OUT_CONTENTS%\frontend\dist" >nul
    if errorlevel 1 goto :SISRUA_FAIL
) else (
    echo AVISO: Frontend build dist nao encontrado em %FRONTEND_DIST%
    echo Gere o build do Vite e tente novamente.
)

echo [5.5/6] Copiando Blocos CAD (.dxf/.dwg)...
if exist "%ROOT%Blocks" (
    SET SISRUA_STEP=copiando Blocos CAD
    xcopy /E /I /Y "%ROOT%Blocks" "%OUT_CONTENTS%\Blocks" >nul
    if errorlevel 1 goto :SISRUA_FAIL
) else (
    echo AVISO: Pasta 'Blocks' nao encontrada em %ROOT%. Nenhuma definicao de bloco sera incluida.
)

echo [6/6] Copiando Resources (mapeamento, prancha, etc)...
if exist "%SRC_BUNDLE%\Contents\Resources" (
    SET SISRUA_STEP=copiando Resources
    xcopy /E /I /Y "%SRC_BUNDLE%\Contents\Resources" "%OUT_CONTENTS%\Resources" >nul
    if errorlevel 1 goto :SISRUA_FAIL
) else (
    echo AVISO: Resources nao encontrado em %SRC_BUNDLE%\Contents\Resources
)

echo.
echo ======================================================
echo ESTRUTURA ORGANIZADA COM SUCESSO!
echo Local: %OUT_BUNDLE%
echo ======================================================
if not defined SISRUA_NOPAUSE pause
exit /b 0

:SISRUA_COPY_DLL_FAIL
echo Detalhe do erro no xcopy dll:
xcopy /Y /I "%BIN_NET8%\*.dll" "%OUT_CONTENTS%\\"
goto :SISRUA_FAIL

:SISRUA_FAIL
echo ERRO: falha durante %SISRUA_STEP%
echo Verifique espaco em disco e permissoes de escrita.
exit /b 1
