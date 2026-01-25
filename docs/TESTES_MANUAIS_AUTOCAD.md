# Testes manuais — AutoCAD (2024/2025/2026)

Use este checklist antes de publicar um release (ou enviar para a Autodesk App Store).

## 0) Coleta de evidências (audit-ready)

Para auditoria/revisão, cada execução manual deve ser **auto-contida** (o que foi testado + com quais binários + provas).

- **Crie um RUN** em `qa/out/manual/<RUN_ID>/` (não versionar).
- **Copie e preencha** o template:
  - de: `qa/manual/execution-record-template.md`
  - para: `qa/out/manual/<RUN_ID>/execution-record.md`
- **Gere hashes SHA-256** dos artefatos sob teste e salve em:
  - `qa/out/manual/<RUN_ID>/artifacts-under-test.sha256.txt`

Comandos úteis (PowerShell):

```powershell
# Hash de um arquivo
Get-FileHash -Algorithm SHA256 "C:\caminho\para\arquivo.ext" | Format-List

# Hash de todos os arquivos de um bundle (útil em auditoria)
Get-ChildItem -Recurse -File "C:\ProgramData\Autodesk\ApplicationPlugins\sisRUA.bundle" |
  Get-FileHash -Algorithm SHA256 |
  Sort-Object Path |
  Format-Table -Auto
```

Padrão de nomes (recomendado) para evidências:

- `qa/out/manual/<RUN_ID>/evidence/<TC-ID>_<o-que-e>_<YYYYMMDD-HHMM>.png`
- `qa/out/manual/<RUN_ID>/logs/`
- `qa/out/manual/<RUN_ID>/artifacts/` (ex.: DWGs de saída)

## 1) Instalação / desinstalação

- Instalar via `installer\out\sisRUA-Installer-<versão>.exe`
- Abrir e fechar o AutoCAD
- Desinstalar pelo Windows (“Apps e recursos”) e confirmar remoção do bundle em:
  - `C:\ProgramData\Autodesk\ApplicationPlugins\sisRUA.bundle`

## 2) Smoke do plugin

Em cada versão do AutoCAD suportada (2024, 2025, 2026):

- Rodar comando `SISRUA`
  - UI abre (WebView2 ok)
- Gerar OSM (internet ligada)
  - Desenha polylines no ModelSpace
  - Layers criados e organizados por `highway` (cores)
- Importar GeoJSON
  - Desenha polylines no ModelSpace
- Durante processamento:
  - UI mostra progresso (job status)

## 3) Robustez

- Reabrir o AutoCAD e rodar `SISRUA` novamente
  - Backend sobe e responde (health/auth)
- Rodar `build_release.cmd` em máquina “limpa”
  - Smoke test do backend passa
