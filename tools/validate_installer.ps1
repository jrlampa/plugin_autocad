<#
.SYNOPSIS
  Valida o instalador sisRUA em ambiente limpo: instala, verifica arquivos e desinstala.

.DESCRIPTION
  - Verifica presença do WebView2 Runtime (registry).
  - Se já houver instalação prévia, desinstala primeiro (ambiente limpo).
  - Executa o instalador em modo silencioso (/VERYSILENT /SUPPRESSMSGBOXES).
  - Valida pastas e arquivos esperados (PackageContents.xml, backend, frontend, etc.).
  - Opcionalmente executa smoke do backend no EXE instalado.
  - Desinstala e confirma remoção.

  Requer: PowerShell em modo Administrador, WebView2 instalado, instalador pré-gerado.

.PARAMETER InstallerExe
  Caminho para o EXE do instalador. Se omitido, procura em installer\out ou installer\Output.

.PARAMETER SkipSmoke
  Não rodar smoke do backend após instalação.

.PARAMETER SkipUninstall
  Não desinstalar ao final (útil para inspeção manual).
#>

param(
  [string]$InstallerExe = '',
  [switch]$SkipSmoke,
  [switch]$SkipUninstall
)

$ErrorActionPreference = 'Stop'
$script:Failed = $false

function Write-Step { param([string]$Msg) Write-Host "[validate-installer] $Msg" }
function Write-Ok    { param([string]$Msg) Write-Host "[validate-installer] OK: $Msg" -ForegroundColor Green }
function Write-Fail  { param([string]$Msg) Write-Host "[validate-installer] FALHA: $Msg" -ForegroundColor Red; $script:Failed = $true }
function Write-Warn  { param([string]$Msg) Write-Host "[validate-installer] AVISO: $Msg" -ForegroundColor Yellow }

# --- Caminhos padrão do instalador ---
$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root 'installer\out'
$outputDir = Join-Path $root 'installer\Output'
$bundleMachine = Join-Path $env:ProgramData 'Autodesk\ApplicationPlugins\sisRUA.bundle'
$bundleUser = Join-Path $env:APPDATA 'Autodesk\ApplicationPlugins\sisRUA.bundle'
$uninstallerExe = Join-Path $bundleMachine 'unins000.exe'

# --- Resolve instalador ---
if ([string]::IsNullOrWhiteSpace($InstallerExe)) {
  foreach ($d in @($outDir, $outputDir)) {
    if (Test-Path -LiteralPath $d) {
      $f = Get-ChildItem -Path $d -Filter 'sisRUA-Installer-*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($f) { $InstallerExe = $f.FullName; break }
    }
  }
}
if (-not $InstallerExe -or -not (Test-Path -LiteralPath $InstallerExe)) {
  Write-Fail "Instalador nao encontrado. Gere com: installer\build_installer.cmd (ou informe -InstallerExe)"
  exit 1
}
Write-Step "Instalador: $InstallerExe"

# --- Exige Admin (auto-elevação) ---
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
  Write-Step "Reiniciando como Administrador (aprove UAC)..."
  $argList = @('-ExecutionPolicy', 'Bypass', '-NoProfile', '-File', "`"$PSCommandPath`"")
  if ($InstallerExe) { $argList += '-InstallerExe', "`"$InstallerExe`"" }
  if ($SkipSmoke) { $argList += '-SkipSmoke' }
  if ($SkipUninstall) { $argList += '-SkipUninstall' }
  $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList -Verb RunAs -Wait -PassThru
  exit $p.ExitCode
}

# --- WebView2 ---
$wv2Guid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
$hasWv2 = $false
$regPaths = @(
  "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$wv2Guid",
  "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$wv2Guid",
  "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$wv2Guid"
)
foreach ($rp in $regPaths) {
  try {
    $pv = (Get-ItemProperty -LiteralPath $rp -Name 'pv' -ErrorAction SilentlyContinue).pv
    if ($pv -and $pv -ne '0.0.0.0') { $hasWv2 = $true; break }
  } catch { }
}
if (-not $hasWv2) {
  Write-Fail "WebView2 Runtime nao detectado. O instalador aborta sem ele. Instale: https://go.microsoft.com/fwlink/?LinkId=2124703"
  exit 1
}
Write-Ok "WebView2 detectado"

# --- Ambiente limpo: desinstalar se já existir ---
if (Test-Path -LiteralPath $uninstallerExe) {
  Write-Step "Instalacao previa encontrada. Desinstalando para ambiente limpo..."
  $p = Start-Process -FilePath $uninstallerExe -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES' -Wait -PassThru
  if ($p.ExitCode -ne 0) {
    Write-Fail "Desinstalacao anterior falhou (exit $($p.ExitCode))."
    exit 1
  }
  Start-Sleep -Seconds 2
  if (Test-Path -LiteralPath $bundleMachine) {
    Write-Fail "Pasta ainda existe apos desinstalar: $bundleMachine"
    exit 1
  }
  Write-Ok "Ambiente limpo (desinstalacao previa concluida)"
}

# --- Instalar ---
Write-Step "Executando instalador (VERYSILENT)..."
$p = Start-Process -FilePath $InstallerExe -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES' -Wait -PassThru
if ($p.ExitCode -ne 0) {
  Write-Fail "Instalador retornou exit $($p.ExitCode)."
  exit 1
}
Start-Sleep -Seconds 2
Write-Ok "Instalador concluido"

# --- Verificar pastas e arquivos ---
$required = @(
  @{ Path = $bundleMachine; Desc = 'Bundle (ProgramData)' }
  @{ Path = $bundleUser;    Desc = 'Bundle (AppData)' }
  @{ Path = (Join-Path $bundleMachine 'PackageContents.xml'); Desc = 'PackageContents.xml' }
  @{ Path = (Join-Path $bundleMachine 'Contents\sisRUA_NET8.dll'); Desc = 'Contents\sisRUA_NET8.dll' }
  @{ Path = (Join-Path $bundleMachine 'Contents\backend\sisrua_backend.exe'); Desc = 'Contents\backend\sisrua_backend.exe' }
  @{ Path = (Join-Path $bundleMachine 'Contents\frontend\dist\index.html'); Desc = 'Contents\frontend\dist\index.html' }
  @{ Path = (Join-Path $bundleMachine 'Contents\Resources\mapeamento.json'); Desc = 'Contents\Resources\mapeamento.json' }
  @{ Path = $uninstallerExe; Desc = 'unins000.exe' }
)
foreach ($r in $required) {
  if (Test-Path -LiteralPath $r.Path) {
    Write-Ok $r.Desc
  } else {
    Write-Fail "Ausente: $($r.Desc) -> $($r.Path)"
  }
}

# --- Smoke do backend (opcional) ---
if (-not $SkipSmoke -and -not $script:Failed) {
  $backendExe = Join-Path $bundleMachine 'Contents\backend\sisrua_backend.exe'
  if (Test-Path -LiteralPath $backendExe) {
    Write-Step "Executando smoke do backend (instalado)..."
    try {
      & (Join-Path $PSScriptRoot 'smoke_backend.ps1') -BackendExe $backendExe -SkipOsm
      Write-Ok "Smoke do backend passou"
    } catch {
      Write-Fail "Smoke do backend: $($_.Exception.Message)"
    }
  } else {
    Write-Warn "Backend EXE nao encontrado; smoke ignorado"
  }
}

if ($script:Failed) {
  Write-Host ""
  Write-Fail "Validacao falhou. Corrija os itens acima."
  exit 1
}

# --- Desinstalar ---
if (-not $SkipUninstall) {
  Write-Step "Desinstalando..."
  $p = Start-Process -FilePath $uninstallerExe -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES' -Wait -PassThru
  if ($p.ExitCode -ne 0) {
    Write-Fail "Desinstalador retornou exit $($p.ExitCode)."
    exit 1
  }
  Start-Sleep -Seconds 2
  foreach ($dir in @($bundleMachine, $bundleUser)) {
    if (Test-Path -LiteralPath $dir) {
      Write-Fail "Pasta ainda existe apos desinstalar: $dir"
    } else {
      Write-Ok "Removido: $dir"
    }
  }
} else {
  Write-Warn "SkipUninstall: instalacao mantida para inspecao manual"
}

Write-Host ""
Write-Host "[validate-installer] Validacao concluida com sucesso." -ForegroundColor Green
