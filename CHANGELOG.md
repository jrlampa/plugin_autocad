# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-02-01

### Added

- **Audit Log API**: 6 new endpoints for cryptographic audit logging (`/api/audit/*`)
  - Create, retrieve, verify, and list audit log entries
  - Batch signature verification
  - Audit statistics endpoint
- **Cryptographic Signatures**: HMAC-SHA256 signatures for tamper-proof audit logs
- **Database Indexes**: Optimized query performance
  - `idx_cadfeatures_project`, `idx_cadfeatures_type` for CadFeatures
  - `idx_auditlog_entity`, `idx_auditlog_timestamp`, `idx_auditlog_event_type` for AuditLog
- **API Documentation**:
  - `docs/API_REFERENCE_v0.8.0.md` - Complete API reference with examples
  - `docs/API_STABILITY_POLICY.md` - Versioning and stability guarantees
- **Contract Tests**: `tests/test_api_contracts.py` for API stability verification
- **Secret Management Audit**: Verified zero secrets in build artifacts
  - `tools/scan_secrets.py` - Comprehensive secret scanner
  - `tools/quick_secret_check.py` - Fast verification tool

### Changed

- **API Version**: Updated from 0.7.0 to 0.8.0
- **OpenAPI Tags**: Added "Projects", "AI", and "Audit" categories

### Security

- Implemented audit logging for Project updates (optimistic locking)
- Audit secret file (`.audit_secret`) with secure permissions (chmod 600)
- Verified GROQ API key not hardcoded (runtime loading only)
- Zero secrets leak verification completed

---

## [0.6.0] - 2026-01-31

### Added

- **Schema Registry**: Centralized data contracts in `schema/v1/` as JSON Schemas, exported directly from Pydantic models.
- **Caching Tier v2**: Redis-backed tiered coaching for heavy read-path operations (OSM and Elevation) with filesystem fallback.
- **Internal Python SDK**: `sisrua-sdk` package for typed programmatic access to the backend API.
- **Architectural Decision Records (ADRs)**: Formal documentation of design choices in `docs/adr/`.
- **Advanced Webhooks**: Asynchronous event broadcasting for job life-cycle and project events (`project_saved`).

### Changed

- **Refactored Core Services**: Applied Ockham's Razor to reduce abstraction overkill, consolidating cache and singleton patterns.
- **Job Management**: Merged cancellation tokens directly into the job store for simpler state tracking.

---

## [0.5.0] - 2026-01-31

### Added

- **CI/CD Pipeline**: GitHub Actions workflow (`.github/workflows/ci.yml`) for automated testing and building.
- **Linting & Formatting**: ESLint + Prettier integrated into frontend build with `lint:fix` and `format` scripts.
- **Separation of Concerns**: Backend refactored into modular services (`services/jobs.py`, `services/osm.py`, `services/geojson.py`) and core utilities (`core/utils.py`).
- **Secret Management**: `.env.example` with documented environment variables; `.gitignore` updated to exclude `.env` files.
- **Environment Parity**: Docker configurations aligned with CI (Python 3.10, Node 20).
- **Elevation Service**: `ElevationService` class with OpenTopography API integration and local caching.
- **Job Cancellation**: Backend now supports cancelling long-running OSM/GeoJSON jobs via `CancellationToken` pattern.
- **Geolocation Sync**: Frontend receives `GEOLOCATION_SYNC` messages from AutoCAD host to update coordinates.

### Changed

- **Backend Tests**: Updated test imports and mocks to reflect new service architecture.
- **Frontend Tests**: Improved test reliability with async waiting and API mocking.
- **Requirements**: `requirements-ci.txt` now includes `rasterio`, `numpy`, and `requests`.

### Fixed

- Resolved multiple ESLint errors in `App.jsx`, `api.js`, and test files.
- Fixed test failures caused by loading screen timing issues.

---

## [0.4.0] - 2026-01-28

### Added

- **Vitest Test Suite**: Frontend testing with Vitest and React Testing Library.
- **Backend Watchdog**: Self-healing mechanism for backend process recovery.
- **Automatic Georeferencing**: Sync CAD and map coordinates automatically.

### Changed

- Upgraded Vite to v7.3.x.
- Improved error handling in API service.

---

## [0.3.0] - 2026-01-25

### Added

- **GeoJSON Import**: Drag-and-drop GeoJSON files onto the plugin palette.
- **OSM Data Fetching**: Fetch roads, buildings, and landuse from OpenStreetMap.
- **Coordinate Projection**: Automatic UTM projection based on location.

### Fixed

- Fixed CORS issues with backend health check.

---

## [0.2.0] - 2026-01-20

### Added

- Initial WebView2 integration with React frontend.
- Basic plugin palette with location input and radius slider.

---

## [0.1.0] - 2026-01-15

### Added

- Initial project structure with C# plugin, Python backend, and React frontend.
- FastAPI backend with health check endpoint.
