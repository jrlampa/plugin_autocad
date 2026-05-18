<#
.SYNOPSIS
    Organiza o bundle de deploy do sisRUA (Multi-Targeting).
.DESCRIPTION
    Copia todos os artefatos compilados (C#, Frontend, Backend) para uma estrutura de bundle
    pronta para distribuição, lendo a versão do projeto e atualizando metadados.
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
    # --- Definição de Variáveis ---
    $SrcBundle = Join-Path $Root "bundle-template/sisRUA.bundle"
    $OutRoot = if ($env:SISRUA_OUT_ROOT) { $env:SISRUA_OUT_ROOT } else { Join-Path $Root "dist" }
    $OutBundle = Join-Path $OutRoot "sisRUA.bundle"
    $OutContents = Join-Path $OutBundle "Contents"
    $Config = if ($env:SISRUA_CONFIGURATION) { $env:SISRUA_CONFIGURATION } else { "Debug" }

    $BinNet8 = Join-Path $Root "src/plugin/bin/x64/$Config/net8.0-windows"
    $BinNet48 = Join-Path $Root "src/plugin/bin/x64/$Config/net48"
    $FrontendDist = Join-Path $Root "src/frontend/dist"

    # --- 1. Preparando pasta de saída ---
    Write-Log "[1/6] Preparando pasta de saida (deploy)..."
    if (Test-Path $OutBundle) {
        Write-Log "  - Removendo bundle de saida antigo..."
        Remove-Item -Path $OutBundle -Recurse -Force
    }
    New-Item -Path $OutContents -ItemType Directory -Force | Out-Null

    # --- 1.5. Versionamento ---
    $AppVersion = "0.0.0"
    $VersionFile = Join-Path $Root "VERSION.txt"
    if (Test-Path $VersionFile) {
        $AppVersion = (Get-Content $VersionFile -Raw).Trim()
    }
    Write-Log "INFO: Usando versao do projeto: $AppVersion"

    Write-Log "[1.5/6] Atualizando AppVersion em PackageContents.xml..."
    $PackageContentsTemplate = Join-Path $SrcBundle "PackageContents.xml"
    & (Join-Path $ToolsRoot "update_package_contents_xml.ps1") -PackageContentsPath $PackageContentsTemplate -AppVersion $AppVersion

    # --- 2. Copiando PackageContents.xml ---
    Write-Log "[2/6] Copiando PackageContents.xml..."
    Copy-Item -Path $PackageContentsTemplate -Destination $OutBundle

    # --- 3. Copiando binários .NET (Multi-Targeting) ---
    Write-Log "[3/6] Copiando binarios .NET (Multi-Targeting)..."

    # NET 8.0 (AutoCAD 2025+)
    if (-not (Test-Path $BinNet8)) { throw "Build net8.0-windows nao encontrado em '$BinNet8'" }
    $TargetNet8 = Join-Path $OutContents "net8.0-windows"
    Write-Log "  [net8.0-windows] Copiando..."
    Copy-Item -Path (Join-Path $BinNet8 "*") -Destination $TargetNet8 -Recurse -Force

    # NET 4.8 (AutoCAD 2021-2024)
    if (-not (Test-Path $BinNet48)) { throw "Build net48 nao encontrado em '$BinNet48'" }
    $TargetNet48 = Join-Path $OutContents "net48"
    Write-Log "  [net48] Copiando..."
    Copy-Item -Path (Join-Path $BinNet48 "*") -Destination $TargetNet48 -Recurse -Force

    Write-Log "  [Cleanup] Limpando DLLs conflitantes..."
    & (Join-Path $ToolsRoot "cleanup_bundle.ps1") -TargetDir $TargetNet48
    & (Join-Path $ToolsRoot "cleanup_bundle.ps1") -TargetDir $TargetNet8

    # --- 4. Copiando backend Python ---
    Write-Log "[4/6] Copiando backend Python..."
    $SrcBackend = Join-Path $SrcBundle "Contents/backend"
    if (-not (Test-Path $SrcBackend)) { throw "Backend nao encontrado no template em '$SrcBackend'" }
    Copy-Item -Path $SrcBackend -Destination $OutContents -Recurse -Force

    # --- 5. Copiando frontend (dist) ---
    Write-Log "[5/6] Copiando frontend (dist)..."
    if (Test-Path $FrontendDist) {
        Copy-Item -Path $FrontendDist -Destination (Join-Path $OutContents "frontend") -Recurse -Force
    } else {
        Write-Log "AVISO: Frontend dist nao encontrado. Pulando." "WARN"
    }

    # --- 5.5. Copiando Blocos CAD ---
    Write-Log "[5.5/6] Copiando Blocos CAD..."
    $BlocksDir = Join-Path $Root "Blocks"
    if (Test-Path $BlocksDir) {
        Copy-Item -Path $BlocksDir -Destination $OutContents -Recurse -Force
    }

    # --- 6. Copiando Resources ---
    Write-Log "[6/6] Copiando Resources..."
    $ResourcesDir = Join-Path $SrcBundle "Contents/Resources"
    if (Test-Path $ResourcesDir) {
        Copy-Item -Path $ResourcesDir -Destination $OutContents -Recurse -Force
    }

    # --- 6.5. Copiando Documentação ---
    Write-Log "[6.5/6] Copiando documentação (CHANGELOG.md)..."
    $ChangelogFile = Join-Path $Root "CHANGELOG.md"
    if (Test-Path $ChangelogFile) {
        Copy-Item -Path $ChangelogFile -Destination $OutBundle -Force
    }

    # --- Limpeza Final ---
    if (Test-Path (Join-Path $OutBundle "history")) { Remove-Item (Join-Path $OutBundle "history") -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path (Join-Path $OutContents "history")) { Remove-Item (Join-Path $OutContents "history") -Recurse -Force -ErrorAction SilentlyContinue }

    Write-Log "ESTRUTURA ORGANIZADA COM SUCESSO!" "SUCCESS"
    Write-Log "Local: $OutBundle" "SUCCESS"

} catch {
    Write-Log "ERRO FATAL: Falha ao organizar o projeto." "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}