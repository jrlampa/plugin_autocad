# Checklist — Autodesk App Store (sisRUA)

Este documento organiza o “pacote” mínimo para submissão com qualidade de ~95%.

## 1) Artefatos

- **Instalador**: `installer/out/sisRUA-Installer-<versão>.exe` (ex.: `sisRUA-Installer-0.2.0.exe`).
- **Bundle**: `sisRUA.bundle` (para auditoria interna).
- **Assinatura digital** (recomendado): DLLs + EXE do backend + instalador.

## 2) Metadados exigidos (típico)

- **Nome do app** e versão.
- **Descrição curta** e **descrição longa** (benefícios + limitações).
- **Compatibilidade**: AutoCAD 2024/2025/2026 (Win64).
- **Categoria** e palavras‑chave.

## 3) Conteúdo legal

- **EULA**: `../EULA.md`
- **Política de Privacidade**: `../PRIVACY.md`
- **Third‑party notices**: `../THIRD_PARTY_NOTICES.md`

## 4) Mídias

- **Ícone** (ex.: 256×256) e/ou conforme exigência da loja.
- **Screenshots**:
  - UI (paleta aberta)
  - Exemplo: gerar OSM e desenhar no ModelSpace
  - Exemplo: importar GeoJSON
  - Tela de instalação/desinstalação

## 5) Requisitos técnicos e UX

- **WebView2 Runtime**: instalador deve detectar e orientar (já implementado no `installer/sisRUA.iss`).
- **Porta dinâmica**: evitar conflitos e facilitar coexistência com outros serviços.
- **Logs**: backend em `%LOCALAPPDATA%\\sisRUA\\logs\\backend.log` (para suporte).

## 6) “Go/No‑Go” (antes de subir)

- Instalar/desinstalar em máquina limpa
- Testar AutoCAD 2024 / 2025 / 2026:
  - `SISRUA` abre UI em poucos segundos
  - `Gerar OSM` desenha polylines
  - `Importar GeoJSON` desenha polylines
- Sem travar AutoCAD ao fechar (processo do backend encerra)

