[net.ref].[Assembly]::LoadWithPartialName('Autodesk.AutoCAD.DatabaseServices')
[net.ref].[Assembly]::LoadWithPartialName('Autodesk.AutoCAD.Geometry')

# Test script for accoreconsole
$db = new-object Autodesk.AutoCAD.DatabaseServices.Database($false, $true)
# Verification logic would go here in a real scenario
Write-Host "2.5D Verification Script Loaded"
