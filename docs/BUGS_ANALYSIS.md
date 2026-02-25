# Análise de Bugs e Erros - sisRUA

**Data:** 2026-01-27  
**Escopo:** Análise completa do projeto em busca de bugs, erros e inconsistências

---

## Bugs Críticos

### 1. ❌ Bug: Assinatura do Instalador Nunca Executada

**Arquivo:** `tools/sign_artifacts.cmd` (linha 50)

**Problema:**
```batch
for %%F in (%ROOT%\installer\out\sisRUA-Installer-*.exe) do set IEXE=%%F
```

O instalador gerado tem nome versionado: `sisRUA-Installer-<versão>.exe` (ou a versão atual do `VERSION.txt`), e o script agora busca corretamente usando glob pattern.

**Impacto:** A assinatura digital do instalador **nunca é executada**, apenas DLLs e backend EXE são assinados.

**Solução:** Ler `VERSION.txt` e montar o caminho correto, ou usar glob pattern `sisRUA-Installer-*.exe`.

**Prioridade:** 🔴 **ALTA** - Bloqueante para distribuição controlada

---

## Inconsistências de Versionamento

### 2. ⚠️ Inconsistência: Versão do Produto vs PackageContents.xml

**Arquivos:**
- `VERSION.txt`: `0.2.0`
- `bundle-template/sisRUA.bundle/PackageContents.xml`: `AppVersion="0.1.0"` (linha 6)

**Problema:** O `PackageContents.xml` está desatualizado e é editado manualmente. Se alguém alterar só o `VERSION.txt` e esquecer o XML, os dois divergem.

**Impacto:** Versão incorreta exibida pelo AutoCAD/Autoloader.

**Solução:** Automatizar sincronismo `VERSION.txt` → `PackageContents.xml` (conforme recomendado em `PRODUCAO.md`).

**Prioridade:** 🟡 **MÉDIA**

---

### 3. ⚠️ Inconsistência: Versão do Frontend

**Arquivo:** `src/frontend/package.json` (linha 4)

**Problema:**
```json
"version": "0.0.0"
```

O produto é `0.2.0` (conforme `VERSION.txt`), mas o frontend permanece `0.0.0`.

**Impacto:** Divergência de "número de versão" do produto. Não é crítico para build/instalador, mas gera inconsistência.

**Solução:** Decidir se `package.json` deve espelhar o produto (ex.: `0.2.0`) ou seguir como "0.0.0" interno e documentar essa convenção.

**Prioridade:** 🟢 **BAIXA**

---

## Erros de Código

### 4. ❌ Erro: Import Duplicado

**Arquivo:** `src/plugin/SisRuaCommands.cs` (linhas 9 e 19)

**Problema:**
```csharp
using System.Globalization;  // linha 9
// ... outras linhas ...
using System.Globalization; // linha 19 (duplicado)
```

**Impacto:** Código desnecessário, pode causar confusão. Não quebra compilação, mas é má prática.

**Solução:** Remover uma das declarações `using`.

**Prioridade:** 🟢 **BAIXA**

---

### 5. ❌ Erro: Atribuição de Campo Inexistente

**Arquivo:** `src/backend/backend/api.py` (linhas 428 e 584)

**Problema:**
```python
payload.cache_hit = False  # linha 428
payload.cache_hit = False  # linha 584
```

O objeto `PrepareResponse` (Pydantic BaseModel) não possui o campo `cache_hit`. Isso causará `AttributeError` em runtime.

**Impacto:** Erro em runtime quando o cache não é usado (primeira execução ou cache miss).

**Solução:** 
- Opção 1: Adicionar `cache_hit: Optional[bool] = None` ao modelo `PrepareResponse`.
- Opção 2: Remover essas atribuições e usar um dicionário separado para metadados de cache.

**Prioridade:** 🔴 **ALTA** - Causa falha em runtime

---

### 6. ⚠️ Possível Null Reference: ProjectRepository.LoadProject

**Arquivo:** `src/plugin/ProjectRepository.cs` (linha 209)

**Problema:**
```csharp
feature.FeatureType = Enum.Parse<SisRuaCommands.CadFeatureType>(reader.GetString(reader.GetOrdinal("feature_type")));
```

Se `reader.GetString()` retornar `null` ou um valor inválido para o enum, `Enum.Parse` lançará exceção.

**Impacto:** Falha ao carregar projetos se houver dados corrompidos no banco.

**Solução:** Adicionar validação e tratamento de erro:
```csharp
string featureTypeStr = reader.IsDBNull(reader.GetOrdinal("feature_type")) 
    ? null 
    : reader.GetString(reader.GetOrdinal("feature_type"));
if (string.IsNullOrWhiteSpace(featureTypeStr) || 
    !Enum.TryParse<SisRuaCommands.CadFeatureType>(featureTypeStr, out var featureType))
{
    SisRuaCommands.Log($"WARN: Invalid feature_type '{featureTypeStr}' in database. Skipping feature.");
    continue;
}
feature.FeatureType = featureType;
```

**Prioridade:** 🟡 **MÉDIA**

---

### 7. ⚠️ Possível Null Reference: GeometryCleaner.GetPolylineHash

**Arquivo:** `src/plugin/GeometryCleaner.cs` (linha 31)

**Problema:**
```csharp
var uniqueString = $"{polylineFeature.Layer}|{polylineFeature.Name}|{polylineFeature.Highway}|{polylineFeature.WidthMeters}|{JsonSerializer.Serialize(orderedPoints)}";
```

Se `orderedPoints` for `null` ou vazio, `JsonSerializer.Serialize` pode retornar `null` ou string vazia, mas o código já verifica `CoordsXy` antes. No entanto, se `orderedPoints` for uma lista vazia após `SelectMany`, o hash será baseado em string vazia, o que pode causar colisões.

**Impacto:** Possível colisão de hash para polylines diferentes que resultem em `orderedPoints` vazio.

**Solução:** Adicionar verificação:
```csharp
if (!orderedPoints.Any())
{
    return null; // ou um hash baseado em outros atributos
}
```

**Prioridade:** 🟢 **BAIXA**

---

### 8. ⚠️ Possível Race Condition: job_store

**Arquivo:** `src/backend/backend/api.py` (linha 41)

**Problema:**
```python
job_store: Dict[str, Dict[str, Any]] = {}
```

O `job_store` é um dicionário Python compartilhado entre threads (jobs são executados em threads separadas via `threading.Thread`). Acesso concorrente pode causar race conditions.

**Impacto:** Possível corrupção de dados ou exceções em cenários de alta concorrência.

**Solução:** Usar `threading.Lock` para proteger acesso ao `job_store`:
```python
import threading
_job_store_lock = threading.Lock()
job_store: Dict[str, Dict[str, Any]] = {}

def _update_job(job_id: str, ...):
    with _job_store_lock:
        # código existente
```

**Prioridade:** 🟡 **MÉDIA** - Pode causar problemas em produção com múltiplos jobs simultâneos

---

## Problemas de Configuração

### 9. ⚠️ Inconsistência: Nome do Instalador na Documentação

**Arquivos:** Vários arquivos de documentação

**Problema:** Alguns trechos da documentação mencionam `sisRUA-Installer.exe` (sem versão), mas o artefato real gerado é `sisRUA-Installer-<versão>.exe`.

**Impacto:** Confusão ao seguir instruções de documentação.

**Solução:** Atualizar referências para usar o nome versionado ou padrão `sisRUA-Installer-*.exe`.

**Prioridade:** 🟢 **BAIXA**

---

## Resumo de Prioridades

| ID | Problema | Prioridade | Status |
|----|----------|------------|--------|
| 1 | Assinatura do instalador não executa | 🔴 ALTA | ❌ Não corrigido |
| 5 | `cache_hit` em PrepareResponse | 🔴 ALTA | ❌ Não corrigido |
| 2 | Versão PackageContents.xml desatualizada | 🟡 MÉDIA | ❌ Não corrigido |
| 6 | Null reference em LoadProject | 🟡 MÉDIA | ❌ Não corrigido |
| 8 | Race condition em job_store | 🟡 MÉDIA | ❌ Não corrigido |
| 3 | Versão frontend inconsistente | 🟢 BAIXA | ❌ Não corrigido |
| 4 | Import duplicado | 🟢 BAIXA | ❌ Não corrigido |
| 7 | Hash collision em GeometryCleaner | 🟢 BAIXA | ❌ Não corrigido |
| 9 | Documentação inconsistente | 🟢 BAIXA | ❌ Não corrigido |

---

## Recomendações Imediatas

1. **Corrigir bug #1 (sign_artifacts.cmd)** - Bloqueante para assinatura
2. **Corrigir bug #5 (cache_hit)** - Causa falha em runtime
3. **Implementar sincronismo automático de versão** - Previne deriva futura
4. **Adicionar locks para job_store** - Previne race conditions
5. **Adicionar validações em LoadProject** - Previne falhas com dados corrompidos

---

## Notas

- Esta análise foi realizada em 2026-01-27
- Alguns problemas podem ter sido corrigidos após a data de análise
- Recomenda-se executar testes após correções para validar
- Bugs críticos devem ser corrigidos antes da próxima release
