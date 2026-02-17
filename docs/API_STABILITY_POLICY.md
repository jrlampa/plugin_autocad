# API Stability Policy - sisRUA

## Version: 0.8.0

**Last Updated:** 2026-02-01

---

## Overview

This document defines the API stability guarantees and versioning policy for the sisRUA API.

---

## Versioning Scheme

sisRUA uses **URL-based versioning** with semantic versioning for the application.

### URL Pattern

```
/api/v{major}/...
```

**Current:** `/api/v1/*`

### Semantic Versioning

Application version: `MAJOR.MINOR.PATCH` (e.g., `0.8.0`)

- **MAJOR** (0 → 1): Breaking changes, new API version (`v2`)
- **MINOR** (0.7 → 0.8): New features, backward compatible
- **PATCH** (0.8.0 → 0.8.1): Bug fixes only

---

## Stability Guarantees

### v0.8.x Promise

> **All `/api/v1/*` endpoints are stable and will not change incompatibly within v0.8.x patch releases.**

This means:

✅ **GUARANTEED STABLE:**

1. Existing endpoints will not be removed
2. Required request fields will not be added
3. Response fields will not be removed
4. Field types will not change
5. Authentication scheme will not change
6. Error codes will remain consistent

✅ **ALLOWED CHANGES:**

1. New endpoints added
2. New optional request fields added
3. New response fields added (clients ignore unknown fields)
4. Bug fixes that don't break contracts
5. Performance improvements

---

## Breaking Changes

### Definition

A **breaking change** is any modification that requires client code updates to continue functioning.

### Examples of Breaking Changes

| Change | Impact | Breaking? |
|--------|--------|-----------|
| Remove endpoint | Clients get 404 | ❌ YES |
| Remove response field | Client parsing fails | ❌ YES |
| Change field type (string → int) | Deserialization fails | ❌ YES |
| Make optional field required | Old requests fail | ❌ YES |
| Change auth header name | All requests fail 401 | ❌ YES |
| Change error response format | Error handling breaks | ❌ YES |

### Prohibited in v0.8.x

The following changes are **prohibited** in v0.8.x patch releases:

1. ❌ Endpoint removal
2. ❌ Required field addition
3. ❌ Response field removal
4. ❌ Type changes
5. ❌ Authentication changes
6. ❌ Error format changes

---

## Non-Breaking Changes

### Allowed Additions

The following changes are **allowed** without version bump:

1. ✅ New endpoint (`POST /api/v1/new-feature`)
2. ✅ New optional request field
3. ✅ New response field (clients ignore unknown)
4. ✅ New error codes (specific to new features)
5. ✅ Performance optimizations
6. ✅ Bug fixes (behavior corrections)

### Example: Adding Optional Field

**Before:**

```json
{
  "latitude": -21.7634,
  "longitude": -41.3235,
  "radius": 500
}
```

**After (backward compatible):**

```json
{
  "latitude": -21.7634,
  "longitude": -41.3235,
  "radius": 500,
  "include_elevation": true  // NEW optional field
}
```

Old clients continue to work - field ignored if not provided.

---

## Deprecation Policy

### Process

When an endpoint needs to be retired:

1. **Deprecation Warning** (v0.8.x)
   - Add `X-Deprecated` header to response
   - Log deprecation warnings
   - Update documentation with deprecation notice
   - Minimum **6 months** notice period

2. **Migration Guide** (v0.8.x → v0.9.0)
   - Provide migration path
   - Offer new alternative endpoint
   - Run both old and new in parallel

3. **Sunset** (v1.0.0 → v2.0.0)
   - Remove deprecated endpoint
   - Return HTTP 410 Gone
   - Provide clear error message with redirect

### Example Deprecation

```http
HTTP/1.1 200 OK
X-Deprecated: This endpoint will be removed in v2.0.0. Use /api/v2/jobs/prepare instead.
X-Sunset: 2026-08-01

{
  "status": "ok"
}
```

---

## API Evolution

### Minor Version Bumps (0.7 → 0.8)

**Triggers:**

- New features added
- New endpoints added
- Backward-compatible improvements

**Client Impact:** No changes required

---

### Major Version Bumps (v1 → v2)

**Triggers:**

- Breaking changes required
- Architectural redesign
- Security enhancements requiring incompatible changes

**Client Impact:** Migration required

**Migration Path:**

1. Announce v2 in v0.9.x
2. Run v1 and v2 in parallel (grace period)
3. Provide adapter layer for v1 → v2 migration
4. Sunset v1 after 12 months

---

## Current API Surface (v0.8.0)

### Endpoints

**Total:** 20 endpoints across 8 categories

| Category | Endpoints | Stability |
|----------|-----------|-----------|
| Health | 3 | ✅ Stable |
| Jobs | 3 | ✅ Stable |
| Prepare | 2 | ✅ Stable |
| Tools | 2 | ✅ Stable |
| AI | 1 | ✅ Stable |
| Projects | 1 | ✅ Stable |
| Webhooks | 2 | ✅ Stable |
| Audit | 6 | ✅ New in v0.8.0 |

See [API_REFERENCE_v0.8.0.md](API_REFERENCE_v0.8.0.md) for full documentation.

---

## Contract Testing

All API endpoints have contract tests to prevent accidental breaking changes.

**Test Suite:** `tests/test_api_contracts.py`

**Tests verify:**

- Request schema validation
- Response schema validation
- Error response formats
- HTTP status codes
- Header requirements

**CI/CD:** Contract tests run on every commit.

---

## Client Support

### Officially Supported Clients

1. **AutoCAD Plugin (C#)** - v0.8.0+
2. **Frontend (React)** - v0.8.0+
3. **Python SDK** - v0.8.0+ (internal)

### Backward Compatibility

sisRUA API maintains backward compatibility for:

- **1 major version** (v1 supported when v2 released)
- **Minimum 12 months** after major version release

---

## Idempotency

### Job Preparation

Job creation is idempotent using **SHA-256 hash** of request payload.

**Contract:**

- Same payload → same job_id
- Duplicate requests → return existing job
- No side effects on retry

**Implementation:**

```python
payload_json = json.dumps(payload, sort_keys=True)
idempotency_key = hashlib.sha256(payload_json.encode()).hexdigest()
```

**Client Benefit:** Safe to retry on network failures.

---

## Rate Limiting

### Current Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/v1/jobs/prepare` | 5 requests | 60 seconds |
| All other endpoints | No limit | - |

**Response on Exceed:**

```http
HTTP/1.1 429 Too Many Requests
{
  "detail": "Rate limit exceeded"
}
```

**Contract:** Rate limits may be **lowered** but never **raised** within a major version.

---

## Security Guarantees

### Authentication

**Contract:**

- Header: `X-SisRua-Token`
- Fail-closed policy (deny if unconfigured)
- Token validation via constant-time comparison

**Stability Promise:** Header name and validation method will not change in v1.

---

### Audit Logging

**Contract:**

- All sensitive mutations logged
- Cryptographic signatures (HMAC-SHA256)
- Tamper detection guaranteed

**Stability:** Signature algorithm locked for v1.

---

## Monitoring Breaking Changes

### Automated Checks

1. **OpenAPI Spec Diff**
   - Compare v0.7.0 vs v0.8.0 specs
   - Flag breaking changes

2. **Contract Test Regression**
   - Run v0.7.0 tests against v0.8.0 API
   - Ensure all pass

3. **Client Compatibility Matrix**
   - Test old clients against new API
   - Verify forward compatibility

---

## Contact & Support

**Questions about API stability?**

- File an issue: GitHub Issues
- Review this policy before making changes
- Consult team lead for breaking changes

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.8.0 | 2026-02-01 | Added Audit API, stability policy established |
| 0.7.0 | 2026-01-28 | Initial stable API release |

---

**Policy Version:** 1.0  
**Effective Date:** 2026-02-01  
**Next Review:** 2026-08-01
