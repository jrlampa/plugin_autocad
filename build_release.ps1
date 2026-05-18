<#
.SYNOPSIS
    Build completo para distribuição (Multi-Targeting).
.DESCRIPTION
    Compila o plugin C#, o frontend, prepara o backend, gera o bundle e o instalador.
    Versão em PowerShell Core para robustez e manutenibilidade.
#>
Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Config = "Release"

# --- Funções Auxiliares ---
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $colors = @{
        "INFO"    = "Cyan"
        "SUCCESS" = "Green"
        "WARN"    = "Yellow"
        "ERROR"   = "Red"
    }
    $color = if ($colors.ContainsKey($Level)) { $colors[$Level] } else { "White" }
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

function Sign-File {
    param([string]$FilePath)

    if (-not $IsWindows) { return } # Assinatura é uma operação apenas para Windows

    $thumbprint = $env:CODE_SIGN_THUMBPRINT
    $signToolPath = $env:SIGNSERVER_PATH # signtool.exe é esperado aqui

    if ([string]::IsNullOrEmpty($thumbprint) -or [string]::IsNullOrEmpty($signToolPath)) {
        return # Pula silenciosamente se não estiver configurado
    }

    if (-not (Test-Path $FilePath)) {
        Write-Log "Arquivo para assinar não encontrado: $FilePath" "WARN"
        return
    }

    Write-Log "Assinando digitalmente '$FilePath'..." "INFO"
    # O signtool é sensível, então garantimos que os argumentos estão corretos.
    & $signToolPath sign /fd SHA256 /sha1 $thumbprint /tr http://timestamp.digicert.com /td SHA256 "`"$FilePath`""
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao assinar '$FilePath'. Verifique o thumbprint e o certificado."
    }
}

try {
    # --- Verificação de Assinatura de Código ---
    if ([string]::IsNullOrEmpty($env:CODE_SIGN_THUMBPRINT)) {
        Write-Log "Variável CODE_SIGN_THUMBPRINT não definida. Nenhuma assinatura de código será realizada." "WARN"
    } elseif ([string]::IsNullOrEmpty($env:SIGNSERVER_PATH)) {
        Write-Log "CODE_SIGN_THUMBPRINT definido, mas SIGNSERVER_PATH não configurado. Nenhuma assinatura será realizada." "WARN"
    } elseif ($IsWindows) {
        Write-Log "Assinatura de código habilitada com signtool em '$($env:SIGNSERVER_PATH)'." "INFO"
    }

    # --- Build do Plugin C# ---
    Write-Log "[0.1/3] Compilando Multi-Target (net48 + net8.0-windows)..." "INFO"
    $pluginCsproj = Join-Path $Root "src" "plugin" "sisRUA.csproj"
    dotnet build $pluginCsproj -c $Config -p:Platform=x64
    
    # --- Assinatura dos Binários ---
    Sign-File (Join-Path $Root "src" "plugin" "bin" "x64" $Config "net48" "sisRUA.dll")
    Sign-File (Join-Path $Root "src" "plugin" "bin" "x64" $Config "net8.0-windows" "sisRUA.dll")

    # --- Build do Frontend ---
    Write-Log "[0.5/3] Build do frontend (Release)..." "INFO"
    & (Join-Path $Root "tools" "build_frontend.ps1")

    # --- Preparação do Backend ---
    Write-Log "[1/3] Preparando backend (Fonte ofuscado)..." "INFO"
    $env:SISRUA_REBUILD_BACKEND_EXE = "1"
    & (Join-Path $Root "tools" "build_backend_exe.ps1")

    # --- Geração do Changelog ---
    Write-Log "[1.8/3] Gerando CHANGELOG.md a partir dos commits..." "INFO"
    if (-not (Get-Command "git-cliff" -ErrorAction SilentlyContinue)) {
        Write-Log "AVISO: 'git-cliff' não encontrado. Pulando geração do changelog. Instale com 'cargo install git-cliff'." "WARN"
    }
    else {
        # Gera o changelog para a versão mais recente (desde a última tag)
        git-cliff --output (Join-Path $Root "CHANGELOG.md") --latest
        if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o changelog com git-cliff." }
        Write-Log "OK: CHANGELOG.md gerado." "SUCCESS"
    }

    # --- Geração do Bundle ---
    Write-Log "[2/3] Gerando bundle em release\sisRUA.bundle..." "INFO"
    $env:SISRUA_OUT_ROOT = (Join-Path $Root "release")
    $env:SISRUA_CONFIGURATION = $Config
    $env:SISRUA_NOPAUSE = "1"
    & (Join-Path $Root "tools" "organizar_projeto.ps1")

    # --- Verificação dos Artefatos ---
    Write-Log "[2.5/3] Verificando integridade dos artefatos..." "INFO"
    & (Join-Path $Root "tools" "verify_release_artifacts.ps1")

    # --- Geração do Instalador ---
    Write-Log "[3/3] Gerando instalador..." "INFO"
    & (Join-Path $Root "tools" "build_installer.ps1")
    Write-Log "OK: Instalador gerado em $(Join-Path $Root 'installer' 'out')" "SUCCESS"

    # --- Assinatura do Instalador ---
    $installer = Get-ChildItem -Path (Join-Path $Root "installer" "out") -Filter "sisRUA-Setup-*.exe" | Select-Object -First 1
    if ($installer) {
        Sign-File $installer.FullName
    } else {
        Write-Log "Instalador não encontrado para assinatura." "WARN"
    }

    Write-Log "OK: release\sisRUA.bundle pronto." "SUCCESS"

} catch {
    Write-Log "ERRO FATAL: falha no build de release." "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}