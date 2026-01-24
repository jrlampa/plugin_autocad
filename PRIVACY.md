# Política de Privacidade — sisRUA

Última atualização: 2026-01-24

## 1. Visão geral
O sisRUA é um plugin local para AutoCAD que auxilia a trazer dados de vias/linhas (OSM e GeoJSON) para o desenho.

## 2. Coleta e uso de dados
Por padrão, o sisRUA:
- **não exige conta**;
- **não coleta dados pessoais** deliberadamente;
- processa dados **localmente** no computador do usuário.

## 3. Conexões de rede
Quando o usuário usa a função “Gerar OSM”, o backend local pode acessar serviços externos para obter dados do OpenStreetMap (por exemplo, via Overpass API, conforme utilizado pela biblioteca OSMnx).

Isso significa que o seu IP e metadados de rede podem ser vistos por esses serviços, como acontece em qualquer acesso à Internet.

## 4. Arquivos e dados locais
O sisRUA pode:
- ler arquivos arrastados pelo usuário (ex.: GeoJSON) para importação;
- gravar logs locais para diagnóstico, em `%LOCALAPPDATA%\\sisRUA\\logs` (quando aplicável).

## 5. Compartilhamento
O sisRUA não compartilha dados pessoais com terceiros, exceto pelo tráfego necessário para buscar dados OSM quando solicitado pelo usuário (seção 3).

## 6. Retenção
Logs e arquivos locais permanecem no computador do usuário até serem removidos pelo próprio usuário.

## 7. Contato
Defina aqui um e-mail/canal de contato para questões de privacidade (ex.: `suporte@exemplo.com`).

