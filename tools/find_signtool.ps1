$ErrorActionPreference = 'SilentlyContinue'
$paths = @(
  "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe",
  "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\signtool.exe"
)
foreach ($p in $paths) {
  $f = Get-ChildItem -Path $p -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($f) { Write-Output $f.FullName; exit 0 }
}
$f = Get-ChildItem -Path "${env:ProgramFiles(x86)}\Windows Kits" -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($f) { Write-Output $f.FullName }
