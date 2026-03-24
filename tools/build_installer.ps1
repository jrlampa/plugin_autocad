<#
.SYNOPSIS
    Gera o instalador do sisRUA usando o Inno Setup.
.DESCRIPTION
    Compila o script Inno Setup (sisRUA.iss) para criar o executável de instalação,
    passando a versão atual do projeto lida a partir do arquivo VERSION.txt.
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
    Write-Log "Gerando instalador (Inno Setup)..."

    # --- 1. Localizar o compilador do Inno Setup (ISCC.exe) ---
    if (-not $IsWindows) {
        throw "A geração do instalador com Inno Setup só é suportada no Windows."
    }

    $ISCC = $env:ISCC_PATH
    if ([string]::IsNullOrEmpty($ISCC) -or -not (Test-Path $ISCC)) {
        $ISCCPaths = @(
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            "C:\Program Files\Inno Setup 6\ISCC.exe"
        )
        $ISCC = $ISCCPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    }

    if (-not $ISCC) {
        throw "Compilador do Inno Setup (ISCC.exe) não encontrado. Defina a variável de ambiente ISCC_PATH ou instale o Inno Setup 6."
    }
    Write-Log "  - Compilador encontrado em: $ISCC"

    # --- 2. Obter a versão do projeto ---
    $AppVersion = "0.0.0"
    $VersionFile = Join-Path $Root "VERSION.txt"
    if (Test-Path $VersionFile) {
        $AppVersion = (Get-Content $VersionFile -Raw).Trim()
    }
    Write-Log "  - Versão do App: $AppVersion"

    # --- 3. Compilar o instalador ---
    $InstallerOutDir = Join-Path $Root "installer" "out"
    New-Item -Path $InstallerOutDir -ItemType Directory -Force | Out-Null
    $IssFile = Join-Path $Root "installer" "sisRUA.iss"
    
    & $ISCC "`"$IssFile`"" "/DAppVersion=$AppVersion" "/O`"$InstallerOutDir`""
    if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar o instalador com Inno Setup." }

    Write-Log "OK: Instalador gerado em '$InstallerOutDir'" "SUCCESS"

} catch {
    Write-Log "ERRO FATAL: Falha ao gerar o instalador." "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}