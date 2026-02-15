# Manual Installation Script for sisRUA
# Use this if the installer fails with registry/uninstall errors

Write-Host "=== sisRUA Manual Installation ===" -ForegroundColor Cyan

# 1. Stop any running backend
Write-Host "`n[1/5] Stopping backend processes..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -like "*sisrua*" -or $_.ProcessName -like "*python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 2. Define paths
$sourceBundle = "$PSScriptRoot\release\sisRUA.bundle"
$targetDir = "$env:APPDATA\Autodesk\ApplicationPlugins\sisRUA.bundle"

Write-Host "[2/5] Preparing destination..." -ForegroundColor Yellow
# Remove old installation
if (Test-Path $targetDir) {
    Write-Host "  Removing old version..." -ForegroundColor Gray
    Remove-Item -Path $targetDir -Recurse -Force -ErrorAction SilentlyContinue
}

# 3. Copy bundle
Write-Host "[3/5] Copying sisRUA.bundle..." -ForegroundColor Yellow
Copy-Item -Path $sourceBundle -Destination $targetDir -Recurse -Force

# 4. Verify
Write-Host "[4/5] Verifying installation..." -ForegroundColor Yellow
$dllNet8 = Join-Path $targetDir "Contents\net8.0-windows\sisRUA.dll"
$dllNet48 = Join-Path $targetDir "Contents\net48\sisRUA.dll" 
$backend = Join-Path $targetDir "Contents\backend\sisrua_backend.exe"
$frontend = Join-Path $targetDir "Contents\frontend\index.html"

$allOk = $true
if (!(Test-Path $dllNet8)) { Write-Host "  ❌ Missing: sisRUA.dll (net8)" -ForegroundColor Red; $allOk = $false }
if (!(Test-Path $dllNet48)) { Write-Host "  ❌ Missing: sisRUA.dll (net48)" -ForegroundColor Red; $allOk = $false }
if (!(Test-Path $backend)) { Write-Host "  ❌ Missing: backend EXE" -ForegroundColor Red; $allOk = $false }
if (!(Test-Path $frontend)) { Write-Host "  ❌ Missing: frontend" -ForegroundColor Red; $allOk = $false }

if ($allOk) {
    Write-Host "  ✅ All files present!" -ForegroundColor Green
}
else {
    Write-Host "`n❌ Installation incomplete!" -ForegroundColor Red
    exit 1
}

# 5. Success
Write-Host "`n[5/5] Installation complete!" -ForegroundColor Green
Write-Host "  📁 Installed to: $targetDir" -ForegroundColor Cyan
Write-Host "`n✅ sisRUA installed successfully!" -ForegroundColor Green
Write-Host "   Next steps:" -ForegroundColor Yellow
Write-Host "   1. Close and reopen AutoCAD" -ForegroundColor White
Write-Host "   2. Run command: SISRUA" -ForegroundColor White
Write-Host "   3. Test geocode with: 24K 0216330 7528658" -ForegroundColor White
