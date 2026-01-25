Param(
  [string]$BackendDir = (Join-Path $PSScriptRoot "..\\src\\backend"),
  [string]$OutDir = (Join-Path $PSScriptRoot "..\\qa\\out\\backend")
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Push-Location $BackendDir
try {
  Write-Host "[backend-tests] Instalando deps (CI + dev)..."
  python -m pip install -r "requirements-ci.txt" -r "requirements-dev.txt"
  if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias do backend." }

  $env:LOCALAPPDATA = (Join-Path $env:TEMP "sisrua_test_localappdata")
  New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA | Out-Null

  Write-Host "[backend-tests] Rodando pytest..."
  $junitPath = (Join-Path $OutDir "junit.xml")
  $htmlPath = (Join-Path $OutDir "report.html")
  python -m pytest -q --junitxml "$junitPath" --html "$htmlPath" --self-contained-html
  if ($LASTEXITCODE -ne 0) { throw "Falha nos testes do backend." }

  Write-Host "OK: testes do backend passaram."
}
finally {
  Pop-Location
}

