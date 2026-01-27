Param(
  [string]$PackageContentsPath,
  [string]$AppVersion
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PackageContentsPath)) {
  Write-Error "ERRO: O arquivo PackageContents.xml nao foi encontrado em '$PackageContentsPath'."
  exit 1
}

try {
  $xml = [xml](Get-Content $PackageContentsPath)
  $root = $xml.ApplicationPackage

  if (-not $root) {
    Write-Error "ERRO: Root 'ApplicationPackage' nao encontrado em '$PackageContentsPath'."
    exit 1
  }

  $root.AppVersion = $AppVersion
  $xml.Save($PackageContentsPath)

  Write-Host "INFO: AppVersion em '$PackageContentsPath' atualizado para '$AppVersion'."
  exit 0
}
catch {
  Write-Error "ERRO: Falha ao atualizar AppVersion em '$PackageContentsPath'. Detalhes: $($_.Exception.Message)"
  exit 1
}