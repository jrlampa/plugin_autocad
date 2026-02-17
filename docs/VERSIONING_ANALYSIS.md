# Análise de versionamento do projeto sisRUA (Tech Lead)

**Data:** 2025-01-27  
**Fonte de verdade declarada:** `VERSION.txt` = `0.1.0`  
**Conclusão:** O versionamento **não está totalmente correto**. Há 1 bug que impede assinatura do instalador, 2 pontos de possível deriva e 1 inconsistência de documentação.

---

## 1. Arquivo a arquivo

### 1.1 `VERSION.txt` (raiz)
- **Conteúdo:** `0.1.0`
- **Papel:** Fonte única de verdade para a versão do **produto** sisRUA.
- **Status:** ✅ OK. Documentação e scripts assumem este arquivo.

---

### 1.2 `bundle-template/sisRUA.bundle/PackageContents.xml`
- **Campo:** `AppVersion="0.1.0"` (linha 6)
- **Papel:** Versão do bundle exibida pelo AutoCAD / Autoloader.
- **Status:** ✅ **Valor correto** (igual ao `VERSION.txt`), mas **editado manualmente**.  
  Se alguém alterar só o `VERSION.txt` e esquecer o XML, os dois divergem.  
  `PRODUCAO.md` recomenda sincronizar automaticamente `VERSION.txt` → `PackageContents.xml` + instalador; isso **ainda não está implementado**.

---

### 1.3 `installer/sisRUA.iss`
- **Uso:** `#define AppVersion` → `GetEnv('SISRUA_VERSION')` ou, se vazio, `"0.0.0"`.  
  Usado em `AppVersion`, `OutputBaseFilename`, `VersionInfoVersion`.
- **Fluxo real:** O `build_installer.cmd` **sempre** lê `VERSION.txt` e passa `/DAppVersion=%APP_VERSION%` ao ISCC. O `GetEnv` e o fallback `0.0.0` só entrariam em jogo se o instalador fosse compilado **sem** rodar o `build_installer.cmd` (ex.: manualmente, sem definir `AppVersion`).
- **Status:** ✅ OK na prática, pois o instalador é sempre gerado via `build_installer.cmd`. O default `0.0.0` é apenas fallback.

---

### 1.4 `installer/build_installer.cmd`
- **Lógica:**  
  - `APP_VERSION=0.0.0` por padrão.  
  - Se existir `..\VERSION.txt`, lê a primeira linha e sobrescreve.  
  - Chama `ISCC` com `/DAppVersion=%APP_VERSION%` e grava em `installer\out`.
- **Saída:** `sisRUA-Installer-<versão>.exe` (ex.: `sisRUA-Installer-0.1.0.exe`).
- **Status:** ✅ OK. Versão do instalador vem do `VERSION.txt`.

---

### 1.5 `tools/sign_artifacts.cmd`
- **Relevante:**  
  `set IEXE=%ROOT%\installer\out\sisRUA-Installer.exe`
- **Problema:** O instalador gerado tem nome **versionado**: `sisRUA-Installer-0.1.0.exe`.  
  O script procura `sisRUA-Installer.exe` (sem sufixo de versão). Esse arquivo **não existe**.
- **Impacto:** A assinatura do instalador **nunca é feita**; apenas DLLs e backend EXE são assinados.
- **Status:** ❌ **Bug.** O caminho do instalador deve usar a versão (ex.: ler `VERSION.txt` ou usar glob `sisRUA-Installer-*.exe`).

---

### 1.6 `tools/validate_installer.ps1`
- **Lógica:** Procura `sisRUA-Installer-*.exe` em `installer\out` ou `installer\Output`.
- **Status:** ✅ OK. Compatível com o nome versionado gerado pelo Inno.

---

### 1.7 `tools/generate_evidence_pack.py`
- **Lógica:** Lê `VERSION.txt` para montar o nome do pack (ex.: `evidence_0.1.0_...`). Se o arquivo não existir, usa `"0.0.0"`.
- **Status:** ✅ OK e alinhado à fonte de verdade.

---

### 1.8 `src/frontend/package.json`
- **Campo:** `"version": "0.0.0"`.
- **Papel:** Versão do pacote npm do frontend (uso interno; não publicamos no npm).
- **Status:** ⚠️ **Inconsistente** em relação ao produto.  
  O produto é `0.1.0`; o frontend permanece `0.0.0`.  
  `PRODUCAO.md` pede sincronismo entre `VERSION.txt`, `PackageContents.xml`, instalador **e frontend**.  
  Não é crítico para build/instalador, mas gera divergência de “número de versão” do produto.

---

### 1.9 `src/plugin/sisRUA.csproj`
- **Campos:** Não define `Version`, `AssemblyVersion`, `FileVersion` nem `InformationalVersion`.
- **Efeito:** O .NET usa valores padrão (tipicamente `1.0.0.0` para assembly).
- **Status:** ⚠️ **Opcional.** Para rastreabilidade (logs, about, diagnóstico), poderia derivar do `VERSION.txt` via MSBuild. Não quebra build nem instalador.

---

### 1.10 `src/backend` (Python)
- Nenhum `__version__` ou endpoint expondo versão do produto.  
- `standalone.py`: `"version": 1` é **versão do esquema de configuração de logging**, não do produto.
- **Status:** ✅ OK para versionamento do **produto**.  
  Se no futuro a API expuser versão (ex.: `/api/v1/health` ou similar), faria sentido usar `VERSION.txt`.

---

### 1.11 Documentação
- **RELEASE.md, installer/README.md, qa/manual, etc.:**  
  Citam `VERSION.txt`, `sisRUA-Installer-<versão>.exe` ou `0.1.0` de forma coerente.
- **INSTALACAO.md, passo-a-passo.md, APP_STORE.md, sign_artifacts:**  
  Em alguns trechos usam apenas `sisRUA-Installer.exe` (sem versão), o que não reflete o nome real do artefato.
- **Status:** ⚠️ **Inconsistência menor.** Ajustar referências para o nome versionado evita confusão.

---

## 2. Resumo

| Artefato | Versão / uso | OK? | Observação |
|----------|----------------|----|------------|
| `VERSION.txt` | `0.1.0` | ✅ | Fonte de verdade |
| `PackageContents.xml` | `0.1.0` | ✅ | Manual; risco de deriva |
| `sisRUA.iss` | via ` build_installer` | ✅ | Fallback `0.0.0` apenas se compilar à mão |
| `build_installer.cmd` | lê `VERSION.txt` | ✅ | |
| `sign_artifacts.cmd` | `sisRUA-Installer.exe` | ❌ | Nome errado; instalador nunca é assinado |
| `validate_installer.ps1` | `sisRUA-Installer-*.exe` | ✅ | |
| `generate_evidence_pack.py` | `VERSION.txt` | ✅ | |
| `package.json` (frontend) | `0.0.0` | ⚠️ | Diverge do produto |
| `sisRUA.csproj` | (nenhum) | ⚠️ | Opcional para rastreabilidade |
| Backend | — | ✅ | Sem versão de produto; OK |

---

## 3. Recomendações (prioridade)

1. **Corrigir `sign_artifacts.cmd`**  
   Fazer o script localizar o instalador versionado (ex.: ler `VERSION.txt` e montar `sisRUA-Installer-<versão>.exe`, ou usar glob e assinar o encontrado). **Bloqueante** para assinatura correta do instalador.

2. **Automatizar sincronismo de versão**  
   Conforme `PRODUCAO.md`: `VERSION.txt` → `PackageContents.xml` e, se desejado, frontend (e eventualmente csproj). Reduz risco de deriva e esqueçamentos.

3. **Alinhar frontend**  
   Decidir se `package.json` deve espelhar o produto (ex.: `0.1.0`) ou seguir como “0.0.0” interno e documentar essa convenção.

4. **Opcional:** definir `Version` / `InformationalVersion` no `sisRUA.csproj` a partir de `VERSION.txt` para logs e diagnósticos.

5. **Docs:** atualizar menções a `sisRUA-Installer.exe` para `sisRUA-Installer-<versão>.exe` (ou `0.1.0`) onde fizer sentido.

---

## 4. Conclusão

O versionamento **não está totalmente correto**: o uso de `VERSION.txt` e do nome versionado do instalador está bem encaixado na maior parte do fluxo, mas o **bug em `sign_artifacts.cmd`** impede que o instalador seja assinado, e há **deriva manual** (`PackageContents.xml`), **inconsistência** (frontend `0.0.0`) e **docs** a ajustar.  

Resolver o `sign_artifacts.cmd` e, na sequência, o sincronismo automático e o alinhamento do frontend/docs deixa o versionamento **correto e sustentável** para o projeto.
