param(
  [string]$BackendExe = "$(Join-Path $PSScriptRoot '..\bundle-template\sisRUA.bundle\Contents\backend\sisrua_backend.exe')",
  [switch]$SkipOsm
)

$ErrorActionPreference = 'Stop'

function Get-FreePort {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  try { return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port }
  finally { $listener.Stop() }
}

function Wait-Health([string]$BaseUrl, [int]$Seconds = 20) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/v1/health" -TimeoutSec 3
      if ($r.status -eq 'ok') { return $true }
    } catch { }
    Start-Sleep -Milliseconds 250
  }
  return $false
}

if (-not (Test-Path -LiteralPath $BackendExe)) {
  throw "Backend EXE não encontrado em: $BackendExe"
}

$tempRoot = $env:TEMP
if (-not $tempRoot) { $tempRoot = (Join-Path $env:USERPROFILE "AppData\\Local\\Temp") }
$runDir = Join-Path $tempRoot ("sisrua_smoke_run_" + [Guid]::NewGuid().ToString("N"))
$backendOriginal = $BackendExe
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$runExe = Join-Path $runDir "sisrua_backend.exe"
try {
  # Copia para TEMP para evitar bloqueios/locks em pastas sincronizadas.
  [System.IO.File]::Copy($backendOriginal, $runExe, $true)
  try { Unblock-File -LiteralPath $runExe -ErrorAction SilentlyContinue } catch { }
  $BackendExe = $runExe
} catch {
  Write-Host "[smoke] AVISO: falha ao copiar EXE para TEMP. Tentando executar do local original. Erro: $($_.Exception.Message)"
  $BackendExe = $backendOriginal
}

$port = Get-FreePort
$baseUrl = "http://127.0.0.1:$port"

$token = [Guid]::NewGuid().ToString("N")
$headers = @{ 'X-SisRua-Token' = $token }

Write-Host "[smoke] Iniciando backend: $BackendExe --port $port"
$env:SISRUA_AUTH_TOKEN = $token
$p = Start-Process -FilePath $BackendExe -ArgumentList "--host 127.0.0.1 --port $port --log-level warning" -PassThru -WindowStyle Hidden

try {
  if (-not (Wait-Health -BaseUrl $baseUrl -Seconds 25)) {
    throw "Backend não respondeu /api/v1/health em $baseUrl"
  }
  Write-Host "[smoke] Health OK: $baseUrl"

  # Auth check (token)
  $auth = Invoke-RestMethod -Method Get -Uri "$baseUrl/api/v1/auth/check" -Headers $headers -TimeoutSec 10
  if ($auth.status -ne 'ok') { throw "auth/check não retornou status=ok" }

  # GeoJSON mínimo
  $geo = @{
    type = "FeatureCollection"
    features = @(
      @{
        type = "Feature"
        properties = @{ layer = "SISRUA_SMOKE" }
        geometry = @{
          type = "LineString"
          coordinates = @(
            @(-41.3235, -21.7634),
            @(-41.3234, -21.7633)
          )
        }
      }
    )
  }

  $geoReq = @{ geojson = $geo } | ConvertTo-Json -Depth 30
  $geoResp = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/prepare/geojson" -Headers $headers -ContentType "application/json" -Body $geoReq -TimeoutSec 30
  if (-not $geoResp.features -or $geoResp.features.Count -lt 1) {
    throw "prepare/geojson retornou 0 features"
  }
  Write-Host "[smoke] prepare/geojson OK: $($geoResp.features.Count) feature(s)"

  if (-not $SkipOsm) {
    $osmReq = @{
      latitude = -21.7634
      longitude = -41.3235
      radius = 150
    } | ConvertTo-Json

    try {
      $osmResp = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/prepare/osm" -Headers $headers -ContentType "application/json" -Body $osmReq -TimeoutSec 120
      if (-not $osmResp.features) {
        throw "prepare/osm retornou resposta sem 'features'"
      }
      Write-Host "[smoke] prepare/osm OK: $($osmResp.features.Count) feature(s)"
    } catch {
      throw "prepare/osm falhou (pode exigir Internet/Overpass). Erro: $($_.Exception.Message)`nUse -SkipOsm para ignorar."
    }
  }

  Write-Host "[smoke] OK"
} finally {
  try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch { }
}

