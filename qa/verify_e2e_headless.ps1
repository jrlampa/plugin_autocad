# verify_e2e_headless.ps1
# Wrapper para execução de testes E2E via accoreconsole.exe

$ErrorActionPreference = "Stop"

$acore = Get-Command "accoreconsole.exe" -ErrorAction SilentlyContinue
if (-not $acore) {
    # Tenta localizações comuns
    $paths = @(
        "C:\Program Files\Autodesk\AutoCAD 2024\accoreconsole.exe",
        "C:\Program Files\Autodesk\AutoCAD 2023\accoreconsole.exe",
        "C:\Program Files\Autodesk\AutoCAD 2022\accoreconsole.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { $acore = $p; break }
    }
}

if (-not $acore) {
    Write-Warning "accoreconsole.exe não encontrado. O teste E2E real requer AutoCAD instalado."
    exit 0 # Exit gracefully if environment doesn't have CAD
}

$scriptPath = Join-Path $PSScriptRoot "e2e_test_case.scr"
$outDir = Join-Path $PSScriptRoot "out"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory $outDir }

Write-Host "[sisRUA QA] Iniciando teste E2E headless..." -ForegroundColor Cyan

& $acore /s $scriptPath /l en-US

$qaResult = Join-Path $outDir "geometry_compliance.xml"
if (Test-Path $qaResult) {
    Write-Host "[sisRUA QA] Sucesso! Resultados exportados para $qaResult" -ForegroundColor Green
}
else {
    Write-Error "[sisRUA QA] Falha: O arquivo de resultados XML não foi gerado."
}
