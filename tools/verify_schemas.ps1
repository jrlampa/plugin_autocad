$schemasDir = Join-Path $PSScriptRoot "..\schema\v1"
$tempDir = Join-Path $env:TEMP "sisrua_schemas_temp_$(Get-Random)"
$exportScript = Join-Path $PSScriptRoot "export_schemas.py"

Write-Host "[verify_schemas] Creating temp directory: $tempDir"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

try {
    # 1. Run export to temp dir (we need to modify export_schemas.py or just copy it and mock the output dir)
    # Actually, export_schemas.py is hardcoded to ..\schema\v1. 
    # Let's make it accept an optional argument for the output directory.
    
    Write-Host "[verify_schemas] Exporting current models to temp..."
    # We'll just run it as is, but we need to verify if the files match.
    # Better: Run it, and if git status shows changes in schema/v1, it's stale.
    
    $before = Get-ChildItem -Path $schemasDir -Filter *.json | ForEach-Object { Get-FileHash $_.FullName }
    
    & python $exportScript
    
    $after = Get-ChildItem -Path $schemasDir -Filter *.json | ForEach-Object { Get-FileHash $_.FullName }
    
    $stale = $false
    if ($before.Count -ne $after.Count) {
        $stale = $true
    } else {
        for ($i = 0; $i -lt $before.Count; $i++) {
            if ($before[$i].Hash -ne $after[$i].Hash) {
                $stale = $true
                Write-Host "Stale schema detected: $($before[$i].Path)"
                break
            }
        }
    }
    
    if ($stale) {
        Write-Error "Schema Registry is STALE! Run 'python tools/export_schemas.py' and commit the changes."
        exit 1
    } else {
        Write-Host "OK: Schema Registry is up to date."
    }
} finally {
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
}
