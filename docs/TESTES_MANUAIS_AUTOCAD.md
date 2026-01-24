# Testes manuais — AutoCAD (2024/2025/2026)

Use este checklist antes de publicar um release (ou enviar para a Autodesk App Store).

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
