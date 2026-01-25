# Política de Privacidade — sisRUA

Última atualização: 2026-01-24

## 1. Visão geral
O sisRUA é um plugin local para AutoCAD que auxilia a trazer dados de vias/linhas (OSM e GeoJSON) para o desenho.

## 2. LGPD (Lei 13.709/2018) — como o sisRUA se enquadra
O sisRUA é um software que pode tratar dados que **podem** ser considerados pessoais, dependendo do contexto de uso.

- **Lat/Lon e raio**: coordenadas e localização podem ser dados pessoais **se** estiverem associadas a uma pessoa identificada ou identificável (ex.: endereço do cliente, imóvel com proprietário identificável).
- **GeoJSON importado**: pode conter dados pessoais nos atributos (ex.: nome, IDs, endereço).

O sisRUA **não exige conta**, **não faz cadastro** e não tem telemetria por padrão. O tratamento principal é **local**.

## 3. Conexões de rede
Quando o usuário usa a função “Gerar OSM”, o backend local pode acessar serviços externos para obter dados do OpenStreetMap (por exemplo, via Overpass API, conforme utilizado pela biblioteca OSMnx).

Isso significa que o seu IP e metadados de rede podem ser vistos por esses serviços, como acontece em qualquer acesso à Internet.

## 4. Arquivos e dados locais
O sisRUA pode gravar dados localmente para funcionamento e desempenho:

- **Cache de respostas OSM/GeoJSON** (quando aplicável): `%LOCALAPPDATA%\\sisRUA\\cache`
- **Configurações do plugin** (ex.: escala, aceite do aviso): `%LOCALAPPDATA%\\sisRUA\\settings.json`
- **Dados locais da WebView2** (cache/cookies do componente do navegador embutido): `%LOCALAPPDATA%\\sisRUA\\webview2\\...`

Importante: **cache ≠ cookies**.
- **Cache do sisRUA**: arquivos JSON locais usados para acelerar reprocessamentos (ex.: OSM).
- **Cookies/WebView2**: dados do componente do navegador embutido (WebView2), armazenados localmente, como qualquer browser.

## 5. Compartilhamento
O sisRUA não compartilha dados pessoais com terceiros, exceto pelo tráfego necessário para buscar dados OSM quando solicitado pelo usuário (seção 3).

## 6. Retenção
Dados locais permanecem no computador do usuário até serem removidos pelo próprio usuário.

Para remover dados:
- Apague `%LOCALAPPDATA%\\sisRUA\\cache` para limpar cache de processamento.
- Apague `%LOCALAPPDATA%\\sisRUA\\webview2` para limpar dados locais da WebView2.
- Apague `%LOCALAPPDATA%\\sisRUA\\settings.json` para resetar configurações e o aviso de privacidade (ele aparecerá novamente).

## 7. Boas práticas recomendadas (para conformidade)
- **Minimização**: use somente a área necessária (raio) e evite incluir dados pessoais em atributos de GeoJSON quando não for necessário.
- **Transparência**: informe aos usuários finais que o “Gerar OSM” faz requisições a serviços do OpenStreetMap.
- **Controle**: defina políticas internas de retenção (quando limpar cache) e acesso ao computador.

## 8. Contato
Defina aqui um e-mail/canal de contato para questões de privacidade (ex.: `suporte@exemplo.com`).

