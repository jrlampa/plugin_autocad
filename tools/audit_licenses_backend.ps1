Param(
  [Parameter(Mandatory = $true)]
  [string]$PythonExe,

  [Parameter(Mandatory = $true)]
  [string]$RepoRoot,

  [Parameter(Mandatory = $true)]
  [string]$RequirementsPath
)

$ErrorActionPreference = "Stop"

function WriteUtf8NoBom([string]$Path, [string]$Content) {
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

if (-not (Test-Path $PythonExe)) { throw "PythonExe not found: $PythonExe" }
if (-not (Test-Path $RepoRoot)) { throw "RepoRoot not found: $RepoRoot" }
if (-not (Test-Path $RequirementsPath)) { throw "RequirementsPath not found: $RequirementsPath" }

$outFile = Join-Path $RepoRoot "THIRD_PARTY_NOTICES.md"
$tmpDir = Join-Path $env:TEMP ("sisrua_licenses_" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

try {
  Write-Host "[licenses] Instalando pip-licenses no venv de build..."
  & $PythonExe -m pip install --upgrade pip-licenses | Out-Null

  $pipLicensesExe = Join-Path (Split-Path $PythonExe -Parent) "pip-licenses.exe"
  if (-not (Test-Path $pipLicensesExe)) {
    # Fallback: tenta invocar via python -m (pode variar por versão)
    $pipLicensesExe = $null
  }

  $jsonPath = Join-Path $tmpDir "pip_licenses.json"

  $commonArgs = @(
    "--from=mixed",
    "--format=json",
    "--with-authors",
    "--with-urls",
    "--with-license-file",
    "--with-notice-file",
    "--ignore-packages",
    "pip;setuptools;wheel;pyinstaller;pip-licenses;prettytable;wcwidth"
  )

  Write-Host "[licenses] Gerando relatorio JSON (com textos de licencas)..."
  if ($pipLicensesExe) {
    & $pipLicensesExe @commonArgs | Set-Content -Encoding UTF8 $jsonPath
  } else {
    # Alternativa: chama o entrypoint como módulo via python -m pip_licenses (melhor esforço)
    & $PythonExe -m pip_licenses @commonArgs | Set-Content -Encoding UTF8 $jsonPath
  }

  $items = Get-Content -Raw -Encoding UTF8 $jsonPath | ConvertFrom-Json
  if (-not $items) { throw "pip-licenses returned empty output." }

  # Gate simples: falha se aparecer GPL/AGPL/LGPL em qualquer licença.
  $bad = @()
  foreach ($it in $items) {
    $lic = [string]$it.License
    if ($lic -match '(?i)\bA?GPL\b' -or $lic -match '(?i)\bLGPL\b') {
      $bad += "$($it.Name) $($it.Version): $lic"
    }
  }
  if ($bad.Count -gt 0) {
    throw ("Dependencies with possible GPL/LGPL/AGPL detected:`n- " + ($bad -join "`n- "))
  }

  # Monta Markdown (nota: pode ficar grande, mas é intencional para compliance).
  $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
  $sb = New-Object System.Text.StringBuilder
  $fence = '```'
  [void]$sb.AppendLine("# THIRD PARTY NOTICES - sisRUA")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("Last updated: $now")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("This file is **auto-generated** during release build for compliance (Autodesk App Store).")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("## OpenStreetMap (data)")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("- Data: (c) OpenStreetMap contributors")
  [void]$sb.AppendLine("- License: ODbL 1.0")
  [void]$sb.AppendLine("- More info: https://www.openstreetmap.org/copyright")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("## Python backend (pip) - summary")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("|Name|Version|License|URL|")
  [void]$sb.AppendLine("|---|---:|---|---|")

  $sorted = $items | Sort-Object Name
  foreach ($it in $sorted) {
    $name = [string]$it.Name
    $ver = [string]$it.Version
    $lic = ([string]$it.License).Replace("`r","").Replace("`n"," ")
    $url = ([string]$it.URL).Replace("`r","").Replace("`n"," ")
    [void]$sb.AppendLine("|$name|$ver|$lic|$url|")
  }

  [void]$sb.AppendLine()
  [void]$sb.AppendLine("## Python backend (pip) - license texts")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("> Note: some packages may not expose a single license file via metadata. In such cases, the text may be empty.")
  [void]$sb.AppendLine()

  foreach ($it in $sorted) {
    $name = [string]$it.Name
    $ver = [string]$it.Version
    $lic = [string]$it.License
    $licenseText = [string]$it.LicenseFile
    $noticeText = ""
    if ($it.PSObject.Properties.Name -contains "NoticeFile") {
      $noticeText = [string]$it.NoticeFile
    }

    [void]$sb.AppendLine("### $name ($ver)")
    [void]$sb.AppendLine()
    [void]$sb.AppendLine("- Declared license: $lic")
    [void]$sb.AppendLine()
    if (-not [string]::IsNullOrWhiteSpace($licenseText)) {
      [void]$sb.AppendLine($fence)
      [void]$sb.AppendLine($licenseText.TrimEnd())
      [void]$sb.AppendLine($fence)
      [void]$sb.AppendLine()
    } else {
      [void]$sb.AppendLine("_License text not found via package metadata._")
      [void]$sb.AppendLine()
    }
    if (-not [string]::IsNullOrWhiteSpace($noticeText)) {
      [void]$sb.AppendLine("#### NOTICE")
      [void]$sb.AppendLine()
      [void]$sb.AppendLine($fence)
      [void]$sb.AppendLine($noticeText.TrimEnd())
      [void]$sb.AppendLine($fence)
      [void]$sb.AppendLine()
    }
  }

  [void]$sb.AppendLine("## How to regenerate")
  [void]$sb.AppendLine()
  [void]$sb.AppendLine("- This file is generated during build_release.cmd from the backend build venv.")
  [void]$sb.AppendLine("- To force backend rebuild: set SISRUA_REBUILD_BACKEND_EXE=1 then run build_release.cmd.")
  [void]$sb.AppendLine()

  Write-Host "[licenses] Gravando $outFile ..."
  WriteUtf8NoBom -Path $outFile -Content $sb.ToString()

  Write-Host "[licenses] OK."
}
finally {
  try { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $tmpDir } catch { }
}

