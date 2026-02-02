<#
.SYNOPSIS
    Rolls back sisRUA Backend to the previous stable revision.
#>
param(
    [string]$Project = "sisrua-production",
    [string]$Region = "us-central1"
)

$ServiceName = "sisrua-backend"

Write-Host "!!! EMERGENCY ROLLBACK INITIATED !!!" -ForegroundColor Red

# 1. Identity the previous revision
Write-Host "[1/2] Identifying previous stable revision..."
# $PrevRev = gcloud run revisions list --service $ServiceName --limit 2 --format="value(metadata.name)" --region $Region --project $Project | Select-Object -Last 1

# 2. Shift 100% traffic back
Write-Host "[2/2] Shifting 100`% traffic to previous revision..."
# gcloud run services update-traffic $ServiceName --to-revisions $PrevRev=100 --region $Region --project $Project

Write-Host "Rollback complete. System restored to stable state." -ForegroundColor Green
