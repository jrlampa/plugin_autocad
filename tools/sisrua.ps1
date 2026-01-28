<#
.SYNOPSIS
  sisRUA – script único "faz-tudo": build, testes, validação, smoke, etc.

.DESCRIPTION
  Orquestra os vários .cmd e .ps1 do projeto em um único ponto de entrada.
  Pode ser chamado diretamente ou via build.cmd (apenas ações de build).

  Ações de build (também via build.cmd):
    clean, release, installer, sign, validate, all

  Ações adicionais (apenas via sisrua.ps1):
    qa, smoke, build-frontend, audit-licenses

.PARAMETER Action
  clean          - Limpar bin, obj, __pycache__, dist, temp
  release        - Plugin + frontend + backend EXE + bundle em release\
  installer      - Release + Inno Setup -> installer\out\*.exe
  sign           - Assinar DLLs, EXE e instalador (certificado obrigatório)
  validate       - Instalar, verificar e desinstalar o instalador (ambiente limpo)
  all            - release + installer + validate (default para build.cmd)
  qa             - Testes backend (pytest) + frontend (vitest)
  smoke          - Smoke do backend EXE (health, auth, prepare/geojson)
  build-frontend - Apenas build Vite do frontend
  audit-licenses - Auditoria de licenças do backend -> THIRD_PARTY_NOTICES.md
#>

[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateSet(
    'clean', 'release', 'installer', 'sign', 'validate', 'all',
    'qa', 'smoke', 'build-frontend', 'audit-licenses'
  )]
  [string]$Action = 'all'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Tools = $PSScriptRoot

function Invoke-Cmd {
  param([string]$Path, [string]$Description)
  Write-Host "[sisrua] $Description" -ForegroundColor Cyan
  & $Path
  if ($LASTEXITCODE -ne 0) { throw "Falha: $Description" }
}

function Invoke-Ps1 {
  param([string]$Path, [string]$Description)
  Write-Host "[sisrua] $Description" -ForegroundColor Cyan
  & $Path
  if ($LASTEXITCODE -ne 0) { throw "Falha: $Description" }
}

try {
  switch ($Action) {
    'clean' {
      $env:SISRUA_NOPAUSE = '1'
      Invoke-Cmd -Path "$Root\limpar_projeto.cmd" -Description "limpar_projeto.cmd"
    }
    'release' {
      Invoke-Cmd -Path "$Root\build_release.cmd" -Description "build_release.cmd"
    }
    'installer' {
      Invoke-Cmd -Path "$Root\installer\build_installer.cmd" -Description "build_installer.cmd"
    }
    'sign' {
      Invoke-Cmd -Path "$Root\tools\sign_artifacts.cmd" -Description "sign_artifacts.cmd"
    }
    'validate' {
      Invoke-Ps1 -Path "$Tools\validate_installer.ps1" -Description "validate_installer.ps1"
    }
    'all' {
      Invoke-Cmd -Path "$Root\installer\build_installer.cmd" -Description "build_installer.cmd (release + Inno)"
      Invoke-Ps1 "$Tools\validate_installer.ps1" "validate_installer.ps1"
    }
    'qa' {
      Invoke-Ps1 -Path "$Tools\run_qa.ps1" -Description "run_qa.ps1 (testes backend + frontend)"
    }
    'smoke' {
      Invoke-Ps1 -Path "$Tools\smoke_backend.ps1" -Description "smoke_backend.ps1"
    }
    'build-frontend' {
      Invoke-Ps1 -Path "$Tools\build_frontend.ps1" -Description "build_frontend.ps1"
    }
    'audit-licenses' {
      $py = (Get-Command python -ErrorAction SilentlyContinue).Source
      if (-not $py) { throw "python nao encontrado no PATH. Instale Python e as deps do backend." }
      $req = Join-Path $Root "src\backend\requirements.txt"
      if (-not (Test-Path $req)) { throw "requirements.txt nao encontrado: $req" }
      & $Tools\audit_licenses_backend.ps1 -PythonExe $py -RepoRoot $Root -RequirementsPath $req
      if ($LASTEXITCODE -ne 0) { throw "Falha: audit_licenses_backend.ps1" }
    }
  }
  Write-Host "[sisrua] OK: $Action concluido." -ForegroundColor Green
  exit 0
} catch {
  Write-Host "[sisrua] ERRO: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
