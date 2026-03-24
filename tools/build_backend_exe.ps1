<#
.SYNOPSIS
    Gera o executável do backend (sisrua_backend.exe) usando PyInstaller.
.DESCRIPTION
    Este script orquestra a criação de um ambiente virtual, instalação de dependências,
    geração de metadados de versão e a compilação do backend Python em um único .exe.
    Versão em PowerShell Core para robustez e manutenibilidade.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ToolsRoot = $PSScriptRoot
$Root = (Resolve-Path (Join-Path $ToolsRoot "..")).Path

# --- Funções Auxiliares ---
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $colors = @{ "INFO" = "Cyan"; "SUCCESS" = "Green"; "WARN" = "Yellow"; "ERROR" = "Red" }
    $color = if ($colors.ContainsKey($Level)) { $colors[$Level] } else { "White" }
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

try {
    # --- 1. Definição de Variáveis e Ambiente ---
    $BackendSrc = Join-Path $Root "src" "backend"
    $BackendOut = Join-Path $Root "bundle-template" "sisRUA.bundle" "Contents" "backend"
    $BuildRoot = if ($env:SISRUA_BUILD_ROOT) { $env:SISRUA_BUILD_ROOT } else { "$($env:SystemDrive)\sisrua_build" }

    $BuildVenv = Join-Path $BuildRoot ".venv-backend-build"
    $Py = Join-Path $BuildVenv "Scripts" "python.exe"
    $BuildTmp = Join-Path $BuildRoot "tmp"
    $DistTmp = Join-Path $BuildRoot "pyinstaller-dist"

    # Força diretórios temporários em um caminho sem espaços
    New-Item -Path $BuildTmp -ItemType Directory -Force | Out-Null
    $env:TEMP = $BuildTmp
    $env:TMP = $BuildTmp

    # --- 2. Lógica de Rebuild ---
    if ((Test-Path (Join-Path $BackendOut "sisrua_backend.exe")) -and ($env:SISRUA_REBUILD_BACKEND_EXE -ne "1")) {
        Write-Log "AVISO: sisrua_backend.exe já existe. Pulando rebuild. Use SISRUA_REBUILD_BACKEND_EXE=1 para forçar." "WARN"
        exit 0
    }

    # --- 3. Versionamento (Geração do .rc) ---
    $AppVersion = (Get-Content (Join-Path $Root "VERSION.txt") -Raw).Trim()
    $VersionParts = $AppVersion.Split('.')
    $VersionRcFile = Join-Path $BuildTmp "version.rc"

    Write-Log "Gerando arquivo de recurso de versão ($VersionRcFile) para a versão $AppVersion..."

    $rcContent = @"
#include "winver.h"
1 VERSIONINFO
FILEVERSION $($VersionParts[0]),$($VersionParts[1]),$($VersionParts[2]),0
PRODUCTVERSION $($VersionParts[0]),$($VersionParts[1]),$($VersionParts[2]),0
FILEFLAGSMASK 0x17
BEGIN
  BLOCK "StringFileInfo"
  BEGIN
    BLOCK "040904b0"
    BEGIN
      VALUE "CompanyName", "sisRUA"
      VALUE "FileDescription", "sisRUA Backend"
      VALUE "FileVersion", "$AppVersion"
      VALUE "InternalName", "sisrua_backend"
      VALUE "LegalCopyright", "Copyright (C) sisRUA"
      VALUE "OriginalFilename", "sisrua_backend.exe"
      VALUE "ProductName", "sisRUA Backend"
      VALUE "ProductVersion", "$AppVersion"
    END
  END
  BLOCK "VarFileInfo"
  BEGIN
    VALUE "Translation", 0x0409, 0x04B0
  END
END
"@
    Set-Content -Path $VersionRcFile -Value $rcContent -Encoding UTF8

    # --- 4. Preparação do Ambiente Python ---
    Write-Log "Preparando ambiente virtual em '$BuildVenv'..."
    if (-not (Test-Path $Py)) {
        Write-Log "Criando ambiente virtual de build em '$BuildVenv'..."
        try {
            python -m venv $BuildVenv
            if ($LASTEXITCODE -ne 0) { throw "Falha inicial ao criar venv." }
        }
        catch {
            Write-Log "AVISO: Falha ao criar venv com pip. Tentando fallback com 'ensurepip'..." "WARN"
            Remove-Item -Path $BuildVenv -Recurse -Force -ErrorAction SilentlyContinue

            python -m venv --without-pip $BuildVenv
            if ($LASTEXITCODE -ne 0) { throw "Falha crítica ao criar venv base (sem pip)." }

            & $Py -m ensurepip --upgrade
            if ($LASTEXITCODE -ne 0) { throw "Falha crítica ao executar 'ensurepip' no venv." }
        }
    }
    else {
        Write-Log "Ambiente virtual já existe. Pulando criação."
    }

    Write-Log "Instalando dependências do build (pode demorar)..."
    & $Py -m pip install --upgrade pip
    & $Py -m pip install -r (Join-Path $BackendSrc "requirements.txt")
    & $Py -m pip install pyinstaller

    # --- 5. Ofuscação e Auditoria ---
    Write-Log "Executando auditoria de licenças do backend (pip-licenses)..."
    & (Join-Path $Root "tools" "audit_licenses_backend.ps1")

    Write-Log "Executando ofuscação do código fonte do backend..."
    $env:SISRUA_BUILD_ROOT = $BuildRoot
    & $Py (Join-Path $Root "tools" "obfuscate_backend.py")
    if ($LASTEXITCODE -ne 0) { throw "Falha na ofuscação do código. Abortando build para proteger IP." }

    # --- 6. Geração do Executável com PyInstaller (Usando Splatting) ---
    Write-Log "Gerando sisrua_backend.exe com PyInstaller..."

    # Limpeza de builds anteriores do PyInstaller
    Remove-Item -Path (Join-Path $BuildRoot "pyinstaller-work") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $BuildRoot "pyinstaller-spec") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $DistTmp -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -Path $DistTmp -ItemType Directory -Force | Out-Null

    # Define todos os argumentos do PyInstaller em um array para "splatting".
    # Isso torna o comando muito mais legível e fácil de manter.
    $pyinstallerArgs = @(
        "--name", "sisrua_backend",
        "--paths", (Join-Path $BuildRoot "obfuscated_backend"),
        "--onefile",
        "--noconfirm",
        "--clean",
        "--distpath", $DistTmp,
        "--workpath", (Join-Path $BuildRoot "pyinstaller-work"),
        "--specpath", (Join-Path $BuildRoot "pyinstaller-spec"),
        "--version-file", $VersionRcFile,
        "--collect-all", "rasterio",
        "--collect-all", "matplotlib",
        "--collect-all", "fiona",
        "--copy-metadata", "osmnx",
        "--copy-metadata", "pyproj",
        "--collect-data", "pyproj",
        "--add-data", "$((Join-Path $Root 'src' 'frontend' 'dist'));frontend/dist",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide2",
        "--exclude-module", "tkinter",
        "--exclude-module", "IPython",
        "--exclude-module", "notebook",
        (Join-Path $BackendSrc "standalone.py")
    )

    # Executa o PyInstaller "splatting" o array de argumentos.
    & $Py -m PyInstaller @pyinstallerArgs
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou ao gerar o executável." }

    # --- 7. Smoke Test ---
    Write-Log "Executando smoke test no executável gerado..."
    $GeneratedExePath = Join-Path $DistTmp "sisrua_backend.exe"

    if (-not (Test-Path $GeneratedExePath)) {
        throw "Smoke test falhou: sisrua_backend.exe não foi gerado em '$DistTmp'."
    }

    $process = $null
    try {
        Write-Log "  - Iniciando sisrua_backend.exe em background..."
        $process = Start-Process -FilePath $GeneratedExePath -NoNewWindow -PassThru
        
        # Aguarda um tempo para o servidor (que é lento para iniciar via PyInstaller) ficar pronto
        Write-Log "  - Aguardando 10 segundos para o servidor iniciar..."
        Start-Sleep -Seconds 10
        
        if ($process.HasExited) {
            throw "Smoke test falhou: O processo sisrua_backend.exe terminou inesperadamente. Verifique os logs de build do PyInstaller."
        }

        Write-Log "  - Realizando requisição de health check para http://localhost:8000/api/v1/health"
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -TimeoutSec 15
        
        if ($response.StatusCode -ne 200) {
            throw "Smoke test falhou. Status code: $($response.StatusCode)"
        }
        
        Write-Log "  - Health check OK (Status: $($response.StatusCode))" "SUCCESS"
    }
    finally {
        if ($process -and -not $process.HasExited) {
            Write-Log "  - Parando processo sisrua_backend.exe (PID: $($process.Id))..."
            Stop-Process -Id $process.Id -Force
        }
    }

    # --- 8. Finalização ---
    $FinalExePath = Join-Path $BackendOut "sisrua_backend.exe"
    Copy-Item -Path $GeneratedExePath -Destination $FinalExePath -Force
    Write-Log "OK: sisrua_backend.exe gerado com sucesso em '$BackendOut'" "SUCCESS"

} catch {
    Write-Log "ERRO FATAL: Falha ao gerar o executável do backend." "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}