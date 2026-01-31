---
description: Roadmap and prompts for the sisRUA v0.5.0 Full Release Cycle (Phases 3-22).
---

This workflow documents the sequence of prompts and technical objectives used to achieve the **v0.5.0 Milestone**. Use this as a template for future major releases.

### 🚀 Release Phases & Objectives

1. **Test Coverage (Phase 3)**
   - **Prompt**: `verifique/implemente: Phase 3: Test Coverage Optimization (v0.4.0) - Reach >90% coverage for Python backend.`
   - **Action**: Create `test_api.py`, `test_services.py`, and implement logic tests with `pytest-cov`.

2. **SoC Refactoring (Phase 4)**
   - **Prompt**: `verifique/implemente: Phase 4: Separation of Concerns (SoC) Refactoring - Extract Pydantic Models and Services.`
   - **Action**: Move logic from `api.py` to `models.py`, `services/osm.py`, `services/geojson.py`, etc.

3. **Linting & CI/CD (Phases 5-6)**
   - **Prompt**: `verifique/implemente: Phase 6: CI/CD Pipeline - Create .github/workflows/ci.yml for Python and Node.`
   - **Action**: Setup GitHub Actions with linting (ESLint/Prettier) and automated tests.

4. **Public API Docs & Integration (Phases 10-11)**
   - **Prompt**: `verifique/implemente: Phase 10: Public API Docs - Add OpenAPI metadata and verify /docs.`
   - **Action**: Enhance FastAPI annotations and setup Playwright for E2E testing.

5. **Optimization & Hardening (Phases 12-14)**
   - **Prompt**: `verifique/implemente: Phase 14: Global Error Boundary + Sentry - Integrate error tracking for Backend and Frontend.`
   - **Action**: Bundle optimization (code splitting), Security Headers (CORS), and Sentry SDK integration.

6. **Database & Migrations (Phases 15-16)**
   - **Prompt**: `verifique/implemente: Phase 16: Schema Migration Safety - Create migrations.py with version tracking.`
   - **Action**: Audit queries (indexes) and implement versioned SQLite migrations.

7. **Performance & Footprint (Phases 17-18)**
   - **Prompt**: `verifique/implemente: Phase 17: Core Path Optimization - Reduce latency to sub-200ms.`
   - **Action**: Defer imports, optimize middleware, and implement background job cleanup.

8. **Compatibility & Persistence (Phases 19-20)**
   - **Prompt**: `verifique/implemente: Phase 20: Backward Compatibility & Persistence Fix - Support color, elevation, and slope.`
   - **Action**: Audit OpenAPI schema, update C# `ProjectRepository.cs`, and verify legacy client compatibility.

9. **Environment Sync & Deployment (Phases 21-22)**
   - **Prompt**: `verifique/implemente: Phase 22: Deployment Scripting - Ensure idempotent migrations and tested sync.`
   - **Action**: Propagate secrets via `docker-compose.yml`, support `OPENTOPOGRAPHY_API_KEY`, and create `test_migrations.py`.

### 🛠 Verification Commands

// turbo

- **Backend Tests**: `pytest --cov=backend`
- **Frontend Build**: `npm run build`
- **Env Audit**: `python tools/verify_env_sync.py`
- **Migration Test**: `python tools/test_migrations.py`
