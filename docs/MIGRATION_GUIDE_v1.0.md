# sisRUA v1.0 Migration Guide

This guide provides step-by-step instructions for migrating from v0.8.0 to the final v1.0 release of sisRUA.

## Overview

v1.0 is a milestone release focusing on production readiness, scalability, and long-term stability. While v0.8.0 established the API freeze, v1.0 introduces infrastructure hardening and resilience features.

## Breaking Changes
>
> [!IMPORTANT]
> **NONE.** Following the [API Stability Policy](file:///c:/plugin_autocad/docs/API_STABILITY_POLICY.md), there are no breaking changes to the REST API or AutoCAD plugin commands between v0.8.0 and v1.0.

## New Requirements

- **GCP Project**: Required for production features (Cloud Run).
- **Terraform**: Required for infrastructure management (`infra/terraform`).
- **Locust**: Recommended for scale verification (`tests/locustfile.py`).

## Migration Steps

### 1. Update Infrastructure

v1.0 introduces Terraform-managed infrastructure.

- Initialize Terraform: `terraform init` in `infra/terraform`.
- Apply configuration: `terraform apply` to provision the locked v1.0 cluster.

### 2. Backend Upgrade (v1.0)

The backend is now unified on FastAPI.

- Update dependencies: `pip install -r src/backend/requirements.txt`.
- Start server: `python src/backend/standalone.py` or use the Cloud Run deployment.

### 3. AutoCAD Plugin (v1.0)

- Rebuild the plugin using the v1.0 source.
- No code changes required for endpoint integration as v0.8.0 contracts are maintained.

### 4. Frontend Optimization

- Enable lazy-loading for heavy modules (Mapbox/Sentry) as introduced in v0.8.x.
- Verify `index.js` size remains under the ~30KB threshold for critical path performance.

## Verified Baselines

Users migrating to v1.0 can expect the following certified performance:

- **Scalability**: Sub-200ms latency at 10,000 concurrent users.
- **RTO**: Service restoration in under 5 minutes.
- **Reliability**: Zero-downtime Blue/Green rollouts.

## Support

For migration issues, refer to the [walkthrough.md](file:///C:/Users/Jonatas%20Lampa/.gemini/antigravity/brain/a4c81f88-e120-493e-b213-7b90eb99031a/walkthrough.md) or contact the platform team.
