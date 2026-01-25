Param(
  [switch]$SkipFrontend,
  [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"

Write-Host "[qa] Iniciando suíte de QA (audit-ready)..."

if (-not $SkipBackend) {
  & (Join-Path $PSScriptRoot "test_backend.ps1")
}

if (-not $SkipFrontend) {
  & (Join-Path $PSScriptRoot "test_frontend.ps1")
}

Write-Host "[qa] OK: suíte de QA concluída."

