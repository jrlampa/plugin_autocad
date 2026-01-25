# Landing page — sisRUA

Esta é uma landing page **estática** (sem build) para ser a porta de entrada do sisRUA.

## Hospedagem grátis (GitHub Pages)

O repositório já inclui o workflow:

- `.github/workflows/deploy_landing_pages.yml`

### Como ativar

1) No GitHub, vá em **Settings → Pages**  
2) Em **Build and deployment**, selecione **GitHub Actions**  
3) Faça um push em `main` com alterações em `landing/` (ou rode manualmente o workflow).

URL esperada (padrão do GitHub Pages):

- `https://jrlampa.github.io/plugin_autocad/`

## Download do plugin

O botão “Baixar” tenta buscar o **último release** e apontar direto para o instalador `.exe`.
Se não conseguir (rate limit/CORS), ele cai no link:

- `https://github.com/jrlampa/plugin_autocad/releases/latest`

