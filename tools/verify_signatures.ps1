<#
.SYNOPSIS
    Verifica a assinatura digital de todos os artefatos de release.
.DESCRIPTION
    Este script varre os artefatos de build (DLLs, EXEs) e valida se eles
    possuem uma assinatura digital válida, garantindo a integridade da release.
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

if (-not $IsWindows) {
    Write-Log "Verificação de assinatura digital é suportada apenas no Windows. Pulando." "WARN"
    exit 0
}

try {
    Write-Log "Verificando assinaturas digitais dos artefatos de release..."
    $hasFailed = $false

    $bundleDir = Join-Path $Root "release" "sisRUA.bundle" "Contents"
    $installerDir = Join-Path $Root "installer" "out"

    $artifactsToCheck = [System.Collections.Generic.List[string]]::new()
    $artifactsToCheck.AddRange((Get-ChildItem -Path $bundleDir -Filter "*.dll" -Recurse).FullName)
    $artifactsToCheck.AddRange((Get-ChildItem -Path $bundleDir -Filter "sisrua_backend.exe" -Recurse).FullName)
    $artifactsToCheck.AddRange((Get-ChildItem -Path $installerDir -Filter "sisRUA-Setup-*.exe").FullName)

    if ($artifactsToCheck.Count -eq 0) {
        Write-Log "Nenhum artefato encontrado para verificação. O build pode ter falhado ou a assinatura não foi configurada." "WARN"
        exit 0
    }

    foreach ($artifactPath in $artifactsToCheck) {
        $relativePath = $artifactPath.Replace($Root, "...")
        Write-Log "  - Verificando: $relativePath"
        $signature = Get-AuthenticodeSignature -FilePath $artifactPath
        
        if ($signature.Status -ne 'Valid') {
            Write-Log "    ERRO: Assinatura inválida ou ausente! Status: $($signature.Status)" "ERROR"
            $hasFailed = $true
        }
    }

    if ($hasFailed) { throw "Um ou mais artefatos falharam na verificação de assinatura digital." }

    Write-Log "Todos os artefatos verificados possuem uma assinatura digital válida." "SUCCESS"

} catch {
    Write-Log "ERRO FATAL: Falha na verificação de assinaturas." "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}