$ErrorActionPreference = "Stop"

Write-Host "[frontend] Iniciando testes unitários (Vitest)..."
Set-Location "$PSScriptRoot/../src/frontend"

if (-not (Test-Path "node_modules")) {
  Write-Host "[frontend] Instalando dependencias..."
  npm install
}

# --run garante que o Vitest rode uma vez e saia (não-watch)
npm run test -- --run --reporter=verbose

if ($LASTEXITCODE -ne 0) {
  Write-Error "Falha nos testes de frontend."
  exit 1
}

Write-Host "[frontend] Testes concluídos com sucesso."