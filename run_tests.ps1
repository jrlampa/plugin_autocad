<#
.SYNOPSIS
    Executa a suíte de testes completa do projeto sisRUA.
.DESCRIPTION
    Orquestra a execução dos testes automatizados para o backend (Python),
    frontend (Vitest) e o plugin C# (.NET).
#>
Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

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

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   sisRUA - Suíte de Testes Automatizados" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

try {
    # ======================================
    # 1. Testes do Backend (Python)
    # ======================================
    Write-Log "[1/3] Executando testes do Backend (pytest)..." "INFO"
    $backendDir = Join-Path $Root "src/backend"
    if (-not (Test-Path $backendDir)) {
        throw "Diretório do backend não encontrado em '$backendDir'"
    }

    Push-Location $backendDir
    try {
        # Verificar se o pytest está instalado
        if (-not (Get-Command "pytest" -ErrorAction SilentlyContinue)) {
            Write-Log "Comando 'pytest' não encontrado. Tentando instalar dependências de teste..." "WARN"
            python -m pip install -r "requirements-ci.txt"
        }
        
        python -m pytest --cov=backend --cov-report=term-missing
        if ($LASTEXITCODE -ne 0) { throw "Testes do backend falharam." }
    } finally {
        Pop-Location
    }
    Write-Log "OK: Testes do backend passaram." "SUCCESS"

    # ======================================
    # 2. Testes do Frontend (Vitest)
    # ======================================
    Write-Log "`n[2/3] Executando testes do Frontend (Vitest)..." "INFO"
    $frontendDir = Join-Path $Root "src/frontend"
    if (-not (Test-Path $frontendDir)) {
        throw "Diretório do frontend não encontrado em '$frontendDir'"
    }

    Push-Location $frontendDir
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Log "Diretório 'node_modules' não encontrado. Executando 'npm install'..." "WARN"
            npm install
            if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências do frontend." }
        }
        npm test
        if ($LASTEXITCODE -ne 0) { throw "Testes do frontend falharam." }
    } finally {
        Pop-Location
    }
    Write-Log "OK: Testes do frontend passaram." "SUCCESS"

    # ======================================
    # 3. Testes do Plugin (C#)
    # ======================================
    Write-Log "`n[3/3] Verificando testes do Plugin C# (.NET)..." "INFO"
    if ($IsWindows) {
        $pluginTestProjects = Get-ChildItem -Path (Join-Path $Root "src") -Recurse -Filter "*Tests.csproj"

        if ($pluginTestProjects) {
            foreach ($proj in $pluginTestProjects) {
                Write-Log "Executando testes do Plugin C#: $($proj.FullName)"
                dotnet test $proj.FullName
                if ($LASTEXITCODE -ne 0) { throw "Testes do plugin C# falharam em '$($proj.Name)'." }
            }
        } else {
            Write-Log "Nenhum projeto de teste C# (*Tests.csproj) encontrado." "WARN"
            Write-Log "A validação do plugin pode depender de testes manuais no AutoCAD, conforme a documentação." "WARN"
        }
        Write-Log "OK: Verificação de testes C# concluída." "SUCCESS"
    } else {
        Write-Log "Pulando testes do Plugin C# (ambiente não-Windows)." "WARN"
    }

    Write-Log "`nTodos os testes automatizados foram executados com sucesso!" "SUCCESS"

} catch {
    Write-Log "`nERRO FATAL: A suíte de testes falhou." "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}