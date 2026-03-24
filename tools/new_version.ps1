<#
.SYNOPSIS
    Automatiza o processo de criação de uma nova versão do projeto.
.DESCRIPTION
    Atualiza o arquivo VERSION.txt, cria um commit e uma tag Git para a nova versão,
    e opcionalmente envia para o repositório remoto.
.PARAMETER NewVersion
    A nova versão no formato 'major.minor.patch' (ex: 1.1.0).
.PARAMETER Push
    Se especificado, envia o commit e a tag para o repositório 'origin'.
.EXAMPLE
    # Cria a versão 1.1.0 localmente
    ./tools/new_version.ps1 -NewVersion 1.1.0

.EXAMPLE
    # Cria a versão 1.1.0 e envia para o GitHub
    ./tools/new_version.ps1 -NewVersion 1.1.0 -Push
#>
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$NewVersion,

    [Parameter(Mandatory=$false)]
    [switch]$Push
)

Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"
$ToolsRoot = $PSScriptRoot
$Root = (Resolve-Path (Join-Path $ToolsRoot "..")).Path

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $colors = @{ "INFO" = "Cyan"; "SUCCESS" = "Green"; "WARN" = "Yellow"; "ERROR" = "Red" }
    $color = if ($colors.ContainsKey($Level)) { $colors[$Level] } else { "White" }
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

try {
    # --- 1. Validação ---
    if ($NewVersion -notmatch '^\d+\.\d+\.\d+$') {
        throw "Formato de versão inválido. Use 'major.minor.patch' (ex: 1.1.0)."
    }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Comando 'git' não encontrado. Verifique se o Git está instalado e no PATH."
    }
    git diff --quiet --exit-code
    if ($LASTEXITCODE -ne 0) {
        throw "Repositório com alterações não commitadas. Limpe o workspace antes de criar uma nova versão."
    }

    $VersionFile = Join-Path $Root "VERSION.txt"
    $OldVersion = (Get-Content $VersionFile -Raw).Trim()
    Write-Log "Transição de versão: $OldVersion -> $NewVersion"

    # Validação de versionamento semântico
    if ([System.Version]$NewVersion -le [System.Version]$OldVersion) {
        throw "A nova versão ($NewVersion) deve ser maior que a versão atual ($OldVersion)."
    }

    # --- 2. Atualizar arquivo de versão ---
    Write-Log "Atualizando VERSION.txt..."
    Set-Content -Path $VersionFile -Value $NewVersion

    # --- 3. Operações Git ---
    $TagName = "v$NewVersion"
    $CommitMessage = "chore(release): bump version to $TagName"

    Write-Log "Criando commit para a nova versão..."
    git add $VersionFile
    git commit -m $CommitMessage

    Write-Log "Criando tag '$TagName'..."
    git tag $TagName

    if ($Push) {
        Write-Log "Enviando commit e tag para o repositório 'origin'..."
        git push origin
        git push origin $TagName
        Write-Log "OK: Commit e tag enviados. O workflow de release será acionado." "SUCCESS"
    } else {
        Write-Log "AVISO: O commit e a tag foram criados localmente. Use -Push para enviar ao repositório remoto." "WARN"
    }

} catch {
    Write-Log "ERRO FATAL: Falha ao criar a nova versão." "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}