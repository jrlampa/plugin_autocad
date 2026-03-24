@{
    # Exclui regras específicas do PSScriptAnalyzer.
    #
    # PSUseSingularNouns: Permite o uso de substantivos no plural para nomes de funções,
    # o que pode ser útil em scripts de build.
    #
    # PSAvoidUsingWriteHost: Permite o uso de Write-Host. Nossos scripts usam uma função
    # 'Write-Log' que depende de Write-Host para fornecer feedback colorido e legível no console.
    ExcludeRules = @(
        'PSUseSingularNouns',
        'PSAvoidUsingWriteHost'
    )

    # Habilita e configura regras específicas.
    Rules = @{
        # Garante que todos os scripts usem 'Set-StrictMode -Version Latest'.
        # Isso ajuda a capturar erros comuns e promove boas práticas de codificação.
        PSUseStrict = @{
            Enable = $true
        }
        
        # Regras de Segurança
        # Evita execuções arbitrárias que podem causar injeção de comandos
        PSAvoidUsingInvokeExpression = @{
            Enable = $true
        }
        PSAvoidUsingPlainTextForPassword = @{
            Enable = $true
        }
    }
}