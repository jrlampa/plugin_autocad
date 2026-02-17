[CmdletBinding()]
Param(
    [string]$TargetDir
)

if (-not (Test-Path $TargetDir)) {
    Write-Warning "Target directory not found: $TargetDir"
    return
}

$ExcludedFiles = @(
    "AcCoreMgd.dll",
    "AcDbMgd.dll",
    "AcMgd.dll",
    "AdWindows.dll",
    "AcCui.dll",
    "AcDx.dll",
    "AcTcMgd.dll",
    "AcWindows.dll",
    "Autodesk.AutoCAD.Interop.dll",
    "Autodesk.AutoCAD.Interop.Common.dll"
)

Write-Host "Cleaning up AutoCAD assemblies in $TargetDir..."

foreach ($file in $ExcludedFiles) {
    try {
        $path = Join-Path $TargetDir $file
        if (Test-Path $path) {
            Remove-Item $path -Force
            Write-Host "  Removed: $file"
        }
    }
    catch {
        Write-Warning "  Failed to remove $file: $_"
    }
}

Write-Host "Cleanup complete."
