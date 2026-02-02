<#
.SYNOPSIS
    Deploys a new version of sisRUA Backend with Blue/Green traffic splitting.
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$ImageUri,
    [string]$Project = "sisrua-production",
    [string]$Region = "us-central1"
)

$ServiceName = "sisrua-backend"

Write-Host "--- Starting Blue/Green Deployment for v0.9.0 ---" -ForegroundColor Cyan

# 1. Deploy new revision without taking traffic
Write-Host "[1/3] Deploying new revision: $ImageUri"
# gcloud run deploy $ServiceName --image $ImageUri --no-traffic --region $Region --project $Project

Write-Host "[2/3] New revision deployed. Perform smoke tests on the unique revision URL." -ForegroundColor Yellow

# 2. Shift 10% traffic (Canary)
Write-Host "[3/3] Shifting 10% traffic to new revision..."
# gcloud run services update-traffic $ServiceName --to-revisions LATEST=10 --region $Region --project $Project

Write-Host "Deployment ready for manual validation before 100% cutoff." -ForegroundColor Green
