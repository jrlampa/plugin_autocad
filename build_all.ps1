<#
.SYNOPSIS
    sisRUA - Master Build Pipeline
.DESCRIPTION
    Orquestra todo o processo de build: clean -> compile -> package -> installer.
    Versão multiplataforma e otimizada (PowerShell Core).
#>
Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$StartTime = Get-Date

# --- Funções Auxiliares ---
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $colors = @{
        "INFO"    = "Cyan"
        "SUCCESS" = "Green"
        "WARN"    = "Yellow"
        "ERROR"   = "Red"
    }
    $color = if ($colors.ContainsKey($Level)) { $colors[$Level] } else { "White" }
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   sisRUA - Master Build Pipeline" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ======================================
# PRE-FLIGHT CHECKS
# ======================================
Write-Log "Verificando dependências..." "INFO"

# Inno Setup (Apenas Windows)
if ($IsWindows) {
    $ISCCPaths = @("C:\Program Files (x86)\Inno Setup 6\ISCC.exe", "C:\Program Files\Inno Setup 6\ISCC.exe")
    $ISCC = $ISCCPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $ISCC) {
        Write-Log "Inno Setup 6 não encontrado! Instale de: https://jrsoftware.org/isdl.php" "ERROR"
        exit 1
    }
    Write-Log "Inno Setup encontrado." "SUCCESS"
} else {
    Write-Log "Ambiente não-Windows detectado. Pulando verificação do Inno Setup." "WARN"
}

# Ferramentas CLI
@("dotnet", "node", "python") | ForEach-Object {
    if (Get-Command $_ -ErrorAction SilentlyContinue) {
        Write-Log "$_ CLI disponível." "SUCCESS"
    } else {
        Write-Log "$_ não encontrado! O build das respectivas camadas pode falhar." "WARN"
    }
}

try {
    # ======================================
    # STEPS 1 & 2: CLEAN E BUILD
    # ======================================
    Write-Log "`n[1/4] CLEAN - Limpando projeto..." "INFO"
    # Chama o novo script de limpeza PowerShell diretamente.
    & (Join-Path $Root "limpar_projeto.ps1")

    Write-Log "`n[2/4] BUILD - Compilando projeto completo..." "INFO"
    # Chama o novo script PowerShell diretamente. Erros serão propagados.
    & (Join-Path $Root "build_release.ps1")

    # ======================================
    # STEP 3: VERIFY
    # ======================================
    Write-Log "`n[3/4] VERIFY - Verificando artefatos..." "INFO"
    
    $BundlePath = Join-Path $Root "release/sisRUA.bundle"
    if (-not (Test-Path (Join-Path $BundlePath "PackageContents.xml"))) {
        throw "Bundle não estruturado em release/sisRUA.bundle/"
    }
    Write-Log "Bundle estruturado em release/sisRUA.bundle/" "SUCCESS"

    # ======================================
    # STEP 4: PACKAGE
    # ======================================
    Write-Log "`n[4/4] PACKAGE - Localizando instalador..." "INFO"
    
    $InstallerDirs = @(Join-Path $Root "installer/out", Join-Path $Root "tools/out")
    $Installers = $InstallerDirs | Get-ChildItem -Filter "sisRUA-Setup-*.exe" -ErrorAction SilentlyContinue

    if ($Installers) {
        Write-Log "Instalador gerado com sucesso!" "SUCCESS"
        $Installers | ForEach-Object { Write-Log "Arquivo: $($_.Name) ($([math]::Round($_.Length / 1MB, 2)) MB)" "INFO" }
    } else {
        Write-Log "Instalador não encontrado nos locais padrão." "WARN"
    }

    $Duration = (Get-Date) - $StartTime
    Write-Log "Build finalizado com sucesso em $($Duration.ToString('mm\:ss'))!" "SUCCESS"

} catch {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host "   ERRO FATAL NO BUILD" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}