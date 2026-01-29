param (
  [string]$BundlePath = "release/sisRUA.bundle",
  [switch]$CheckNet48Only = $false
)

$ErrorActionPreference = "Stop"

$root = Get-Item "."
$fullBundlePath = Join-Path $root.FullName $BundlePath
$contentsPath = Join-Path $fullBundlePath "Contents"

Write-Host "`n>>> Verifying Bundle Integrity at: $fullBundlePath" -ForegroundColor Cyan

if (-not (Test-Path $fullBundlePath)) {
  Write-Error "Bundle folder not found: $fullBundlePath"
  exit 1
}

# 1. Check PackageContents.xml
$xmlPath = Join-Path $fullBundlePath "PackageContents.xml"
if (-not (Test-Path $xmlPath)) {
  Write-Error "PackageContents.xml missing!"
  exit 1
}
Write-Host " [OK] PackageContents.xml exists." -ForegroundColor Green

# 2. Check DLLs
# 2. Check DLLs
$requiredDlls = @(
  "net8.0-windows/sisRUA.dll", 
  "net48/sisRUA.dll"
)

foreach ($dllRelPath in $requiredDlls) {
  $path = Join-Path $contentsPath $dllRelPath
  if (Test-Path $path) {
    $size = (Get-Item $path).Length / 1KB
    Write-Host (" [OK] {0,-35} ({1:N1} KB)" -f $dllRelPath, $size) -ForegroundColor Green
  }
  else {
    Write-Host " [FAIL] $dllRelPath is MISSING from $contentsPath" -ForegroundColor Red
    $failure = $true
  }
}

# 3. Check Backend
$backendExe = Join-Path $contentsPath "backend/sisrua_backend.exe"
if (Test-Path $backendExe) {
  Write-Host " [OK] Backend EXE exists." -ForegroundColor Green
}
else {
  Write-Host " [FAIL] backend/sisrua_backend.exe is MISSING!" -ForegroundColor Red
  $failure = $true
}

# 4. Check WebView2
$runtime64 = Join-Path $contentsPath "net8.0-windows/runtimes/win-x64/native/WebView2Loader.dll"
if (Test-Path $runtime64) {
  Write-Host " [OK] WebView2 Runtimes exist." -ForegroundColor Green
}
else {
  Write-Host " [FAIL] WebView2 Runtimes are MISSING!" -ForegroundColor Red
  $failure = $true
}

if ($failure) {
  Write-Host "`n>>> VERIFICATION FAILED! One or more critical components are missing." -ForegroundColor DarkRed
  exit 1
}
else {
  Write-Host "`n>>> VERIFICATION SUCCESS! All compatibility artifacts are present." -ForegroundColor Green
  exit 0
}
