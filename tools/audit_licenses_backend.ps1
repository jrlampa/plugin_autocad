# audit_licenses_backend.ps1
# Self-resolving paths to avoid CMD quoting issues and PowerShell 5.1 Join-Path limitations

$ErrorActionPreference = "Stop"

$ToolsDir = $PSScriptRoot
# PowerShell 5.1 Join-Path only takes two arguments. 
$RepoRoot = Resolve-Path (Join-Path $ToolsDir "..")
$BackendSrc = Join-Path (Join-Path $RepoRoot "src") "backend"
$RequirementsPath = Join-Path $BackendSrc "requirements.txt"

# Get Python from environment or build venv
$PythonExe = Get-Item -Path "$env:SystemDrive\sisrua_build\.venv-backend-build\Scripts\python.exe" -ErrorAction SilentlyContinue
if (!$PythonExe) {
  Write-Error "Could not find build Python at $env:SystemDrive\sisrua_build\.venv-backend-build\Scripts\python.exe"
  exit 1
}

Write-Host "--- Backend License Audit ---"
Write-Host "Repo Root: $RepoRoot"
Write-Host "Python: $PythonExe"

# Ensure pip-licenses is installed
& $PythonExe -m pip install pip-licenses --quiet

# Run license check
$OutDir = Join-Path (Join-Path $RepoRoot "qa") "out"
if (!(Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$ReportPath = Join-Path $OutDir "backend_licenses.json"
Write-Host "Generating report: $ReportPath"

& $PythonExe -m piplicenses --format=json --output-file="$ReportPath" --ignore-packages pip-licenses pip setuptools wheel

if ($LASTEXITCODE -ne 0) {
  Write-Error "Failed to generate license report."
  exit 1
}

Write-Host "License audit completed successfully."
exit 0
