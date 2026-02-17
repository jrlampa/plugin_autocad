<#
.SYNOPSIS
    Bootstrap script for sisRUA development environment.
    Ensures all dependencies (Python, Node, .NET) are installed and configured.
#>

$ErrorActionPreference = "Stop"

Write-Host "--- sisRUA Environment Bootstrap ---" -ForegroundColor Cyan

# 1. Check for Prerequisites
Write-Host "[1/4] Checking Prerequisites..." -ForegroundColor Yellow

$prereqs = @{
    "python" = "python --version"
    "node"   = "node --version"
    "npm"    = "npm --version"
    "dotnet" = "dotnet --version"
}

foreach ($key in $prereqs.Keys) {
    try {
        Invoke-Expression $prereqs[$key] | Out-Null
        Write-Host "  OK: $key found." -ForegroundColor Green
    }
    catch {
        Write-Error "CRITICAL: $key not found in PATH."
        exit 1
    }
}

# 2. Setup Backend (Python)
Write-Host "[2/4] Setting up Backend..." -ForegroundColor Yellow
$backendDir = Join-Path $PSScriptRoot "..\src\backend"
Push-Location $backendDir

if (-not (Test-Path ".venv")) {
    Write-Host "  Creating venv..."
    python -m venv .venv
}

$pip = if ($IsWindows) { ".\.venv\Scripts\pip.exe" } else { ".\.venv\bin\pip" }
Write-Host "  Installing backend dependencies..."
& $pip install --upgrade pip
& $pip install -r requirements.txt
& $pip install -r requirements-dev.txt
Pop-Location

# 3. Setup Frontend (Node)
Write-Host "[3/4] Setting up Frontend..." -ForegroundColor Yellow
$frontendDir = Join-Path $PSScriptRoot "..\src\frontend"
Push-Location $frontendDir
Write-Host "  Installing frontend dependencies (npm ci)..."
npm ci
Pop-Location

# 4. Setup Plugin (.NET)
Write-Host "[4/4] Setting up Plugin..." -ForegroundColor Yellow
$pluginDir = Join-Path $PSScriptRoot "..\src\plugin"
Push-Location $pluginDir
Write-Host "  Restoring NuGet packages..."
dotnet restore
Pop-Location

Write-Host "--- Bootstrap Complete! ---" -ForegroundColor Cyan
Write-Host "You are ready to develop. Run 'npm run dev' in src/frontend and 'python standalone.py' in src/backend." -ForegroundColor Green
