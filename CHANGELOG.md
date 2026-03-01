# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Corrigidos 10 erros críticos de compilação C# que bloqueavam o build
- Removido using duplicado em GeometryCleaner.cs
- Implementado método ausente TestSimplifyPolylines_ReductionRatio em GeometryComplianceTests.cs
- Corrigida ambiguidade de Exception usando System.Exception
- Corrigido callback ExecuteInApplicationContext em PaletteController.cs
- Removido campo não utilizado _lastCrs em SisRuaCommands.cs
- Configurado ambiente de testes automatizados (pytest, vitest)
- Validado build de release com geração de instalador

### Security

- Verificadas dependências por vulnerabilidades críticas
- Validada conformidade com controles de acesso ISO 27001
- Confirmada implementação de princípios LGPD/GDPR

## [0.1.0] - 2026-02-28

### Added

- Estrutura inicial do projeto sisRUA: plugin AutoCAD (C#), backend Python (FastAPI) e frontend React/Vite.
- Pipeline GIS completo: Campo → OSM/GeoJSON → SIRGAS 2000 UTM → CAD (AutoCAD/Civil 3D).
- Projeção automática de zona UTM via pyproj (EPSG:4326 → SIRGAS 2000 UTM zona 23).
- Geração de DXF headless (2.5D) via ezdxf com elevação armazenada em XDATA.
- Integração com Overpass API (OpenStreetMap) para busca de vias e infraestrutura urbana.
- Elevação SRTM offline-first via OpenTopography + cache local de tiles GeoTIFF.
- Importação de GeoJSON via drag-and-drop com conversão automática de CRS.
- Catálogo de blocos CAD (DWG) para ativos urbanos (postes, hidrantes, bueiros, etc.).
- Persistência de projetos em SQLite local com optimistic locking.
- Limpeza e simplificação de geometria (deduplicação, Douglas-Peucker).
- API REST FastAPI com autenticação por token (X-SisRua-Token), rate limiting e audit log criptográfico.
- Interface WebView2 (React/Vite, pt-BR) integrada à palette do AutoCAD.
- Assistente IA via Groq free tier com RAG contextual.
- Docker Compose com healthchecks de produção (backend, Redis, frontend).
- Conformidade ISO 27001: session tokens, origin validation, rate limiting, audit log HMAC-SHA256.
- Conformidade LGPD: housekeeper service com limpeza automática de dados temporários.
- SDKs gerados: Python (`sisrua-sdk`) e TypeScript (OpenAPI).
- 101 testes pytest passando (unit + integração + DXF headless).
