# Troubleshooting

## A UI não abre (paleta vazia / erro WebView2)

- Verifique se o **WebView2 Runtime** está instalado no Windows.
- Verifique se o backend respondeu `http://127.0.0.1:8000/api/v1/health`.

## “Porta 8000 em uso”

Se o AutoCAD já tiver um backend rodando, o plugin tenta detectar via health.

Se mesmo assim houver conflito:

- encerre processos antigos do backend
- ou altere a porta (precisa ajuste no código/config; hoje é fixo em 8000)

## Backend não inicia

Em produção o plugin tenta primeiro:

- `Contents/backend/sisrua_backend.exe`

Se ele não existir (ou falhar), cai no modo Python (dev/fallback) — que depende de Python e de instalar pacotes.

Cheque:

- se o `sisrua_backend.exe` está presente dentro do bundle
- se antivirus/EDR bloqueou a execução

## “Arquivo em uso” ao gerar bundle em Google Drive

Pastas sincronizadas podem manter locks temporários.

Use o modo release fora do `dist/` padrão:

- `build_release.cmd` (gera em `release\`)
ou
- `set SISRUA_OUT_ROOT=<pasta_local>` antes de rodar `organizar_projeto.cmd`

