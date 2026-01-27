Param(
  [string]$FrontendDir = (Join-Path $PSScriptRoot "..\\src\\frontend")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
  Write-Host "AVISO: package.json do frontend nao encontrado em $FrontendDir"
  exit 0
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Write-Error "ERRO: npm nao encontrado no PATH. Instale Node.js (LTS) e tente novamente."
  exit 1
}

# --- Le a versao de VERSION.txt ---
$AppVersionPath = Join-Path $PSScriptRoot "..\\VERSION.txt"
$AppVersion = "0.0.0"
if (Test-Path $AppVersionPath) {
  $AppVersion = (Get-Content $AppVersionPath).Trim()
}
Write-Host "INFO: Usando versao do projeto: $AppVersion"
# --- Fim Leitura Versao ---

function Copy-FrontendToTemp([string]$srcDir, [string]$dstDir, [string]$version) {
  New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

  $items = @(
    "package.json",
    "package-lock.json",
    "vite.config.js",
    "index.html",
    "postcss.config.js",
    "tailwind.config.js",
    "eslint.config.js",
    "public",
    "src"
  )

  foreach ($it in $items) {
    $p = Join-Path $srcDir $it
    if (Test-Path $p) {
      Copy-Item -Path $p -Destination (Join-Path $dstDir $it) -Recurse -Force
    }
  }

  # Atualiza a versao no package.json copiado
  $packageJsonPath = Join-Path $dstDir "package.json"
  if (Test-Path $packageJsonPath) {
    $packageJson = Get-Content $packageJsonPath | ConvertFrom-Json
    $packageJson.version = $version
    $packageJson | ConvertTo-Json -Depth 99 | Set-Content $packageJsonPath
    Write-Host "INFO: package.json em $packageJsonPath atualizado para versao $version."
  }
}

$tempRoot = Join-Path $env:TEMP ("sisrua_frontend_build_" + [Guid]::NewGuid().ToString("N"))
$tempDir = $tempRoot

try {
  Write-Host "[frontend] Preparando build em pasta temporaria (evita travas em pastas sincronizadas)..."
  Copy-FrontendToTemp -srcDir $FrontendDir -dstDir $tempDir -version $AppVersion

  Push-Location $tempDir
  try {
    Write-Host "[frontend] Instalando dependencias (npm install)..."
    npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias do frontend." }

    Write-Host "[frontend] Gerando build (vite)..."
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Falha no build do frontend." }

    if (-not (Test-Path "dist\\index.html")) {
      throw "Build concluido, mas dist\\index.html nao foi encontrado."
    }

    # Copia dist para o repo (é isso que o organizar_projeto.cmd empacota)
    $outDist = Join-Path $FrontendDir "dist"
    if (Test-Path $outDist) {
      Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $outDist
    }
    Copy-Item -Recurse -Force "dist" $outDist

    # Mantém package-lock do repo sincronizado (npm ci/CI dependem disso).
    $srcLock = Join-Path $tempDir "package-lock.json"
    $dstLock = Join-Path $FrontendDir "package-lock.json"
    if (Test-Path $srcLock) {
      Copy-Item -Force $srcLock $dstLock
    }

    Write-Host "OK: frontend gerado em $outDist"
  }
  finally {
    Pop-Location
  }

  exit 0
}
finally {
  try { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $tempRoot } catch { }
}

