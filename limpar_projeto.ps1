<#
.SYNOPSIS
    Script de Limpeza Completa do Projeto sisRUA.
.DESCRIPTION
    Remove todos os artefatos de build, caches e prepara o repositório
    para um build limpo (clean slate). Versão em PowerShell Core.
#>
Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

# --- Funções Auxiliares ---
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $colors = @{ "INFO" = "Cyan"; "SUCCESS" = "Green"; "WARN" = "Yellow"; "ERROR" = "Red" }
    $color = if ($colors.ContainsKey($Level)) { $colors[$Level] } else { "White" }
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

function Remove-Directory {
    param([string]$Path, [string]$Step)
    
    if (Test-Path $Path) {
        Write-Log "[$Step] Removendo '$((Get-Item $Path).Name)'..."
        Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $Path) {
            Write-Log "AVISO: Não foi possível remover completamente '$Path'" "WARN"
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   sisRUA - Limpeza Completa" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

try {
    # 1. Limpar builds do C# (.NET)
    Write-Log "[1/8] Limpando builds do plugin C#..."
    Remove-Directory -Path (Join-Path $Root "src/plugin/bin") -Step "1/8"
    Remove-Directory -Path (Join-Path $Root "src/plugin/obj") -Step "1/8"
    Remove-Directory -Path (Join-Path $Root "build/bin") -Step "1/8"
    Remove-Directory -Path (Join-Path $Root "build/obj") -Step "1/8"

    # 2. Limpar frontend (Node.js/Vite)
    Write-Log "[2/8] Limpando builds do frontend..."
    Remove-Directory -Path (Join-Path $Root "src/frontend/dist") -Step "2/8"
    Remove-Directory -Path (Join-Path $Root "src/frontend/node_modules/.vite") -Step "2/8"

    # 3. Limpar backend Python
    Write-Log "[3/8] Limpando builds do backend Python..."
    Remove-Directory -Path (Join-Path $Root "src/backend/dist") -Step "3/8"
    Remove-Directory -Path (Join-Path $Root "src/backend/build") -Step "3/8"
    Get-ChildItem -Path (Join-Path $Root "src/backend") -Recurse -Include "__pycache__", "*.pyc" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    # 4. Limpar bundles de saída
    Write-Log "[4/8] Limpando bundles e releases..."
    Remove-Directory -Path (Join-Path $Root "dist") -Step "4/8"
    Remove-Directory -Path (Join-Path $Root "release") -Step "4/8"
    Remove-Directory -Path (Join-Path $Root "release_new") -Step "4/8"

    # 5. Limpar instaladores
    Write-Log "[5/8] Limpando instaladores..."
    Remove-Directory -Path (Join-Path $Root "installer/out") -Step "5/8"
    Remove-Directory -Path (Join-Path $Root "tools/out") -Step "5/8"

    # 6. Limpar caches locais do sisRUA
    Write-Log "[6/8] Limpando caches locais..."
    Remove-Directory -Path (Join-Path $Root "cache") -Step "6/8"
    Remove-Directory -Path (Join-Path $Root "logs") -Step "6/8"

    # 7. Limpar arquivos temporários
    Write-Log "[7/8] Limpando arquivos temporários..."
    Get-ChildItem -Path $Root -Filter "*_output.txt" | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $Root -Filter "build_*.txt" | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $Root -Filter "test_out.txt" | Remove-Item -Force -ErrorAction SilentlyContinue
    Remove-Directory -Path (Join-Path $Root ".pytest_cache") -Step "7/8"

    # 8. Limpar estado do NuGet (opcional)
    Write-Log "[8/8] Limpando cache do NuGet (opcional)..."
    Write-Log "   - Pulando limpeza de cache global (descomente no script se necessário)"
    # dotnet nuget locals all --clear

    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "  Limpeza concluída com sucesso!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "`nO repositório está pronto para um build limpo."

} catch {
    Write-Log "Ocorreu um erro inesperado durante a limpeza." "ERROR"
    Write-Log $_.Exception.Message "ERROR"
    exit 1
}