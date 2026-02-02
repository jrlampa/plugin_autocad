# sisRUA API Reference - v0.8.0

**Base URL:** `http://localhost:5050`  
**Authentication:** Header `X-SisRua-Token` required for most endpoints

---

## Table of Contents

- [Authentication](#authentication)
- [Health & Status](#health--status)
- [Jobs](#jobs)
- [Data Preparation](#data-preparation)
- [Tools](#tools)
- [AI](#ai)
- [Projects](#projects)
- [Webhooks](#webhooks)
- [Audit Logs](#audit-logs)
- [Error Responses](#error-responses)

---

## Authentication

All protected endpoints require the `X-SisRua-Token` header.

**Header:**

```http
X-SisRua-Token: your-secret-token-here
```

**Failure Policy:** Fail-closed

- No token configured → HTTP 500
- Invalid/missing token → HTTP 401

**Example:**

```bash
curl -H "X-SisRua-Token: my-token" http://localhost:5050/api/v1/auth/check
```

---

## Health & Status

### GET `/api/v1/health`

Simple health check (no auth required).

**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

---

### GET `/api/v1/auth/check`

Validate authentication token.

**Auth:** Required  
**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

**Errors:**

- `401` - Invalid token
- `500` - Server not configured

---

### GET `/api/v1/health/detailed`

Deep health check (DB, cache, config).

**Auth:** Required  
**Response:** `200 OK`

```json
{
  "status": "healthy",
  "timestamp": 1738454400.0,
  "services": {
    "database": "ok",
    "cache": "ok"
  }
}
```

---

## Jobs

Asynchronous job management for long-running operations.

### POST `/api/v1/jobs/prepare`

Create a new data preparation job (OSM or GeoJSON).

**Auth:** Required  
**Rate Limit:** 5 requests/60s per IP

**Request Body:**

```json
{
  "kind": "osm",
  "latitude": -21.7634,
  "longitude": -41.3235,
  "radius": 500
}
```

**Or for GeoJSON:**

```json
{
  "kind": "geojson",
  "geojson": { ... }
}
```

**Response:** `200 OK`

```json
{
  "job_id": "abc123",
  "status": "pending",
  "progress": 0.0,
  "message": "Job initialized",
  "result": null
}
```

**Idempotency:** Same request payload → same job_id

---

### GET `/api/v1/jobs/{job_id}`

Get job status and result.

**Auth:** Required  
**Response:** `200 OK`

```json
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 1.0,
  "message": "Processing complete",
  "result": {
    "features": [...]
  }
}
```

**Job Status Values:**

- `pending` - Initialized
- `running` - In progress
- `completed` - Success
- `failed` - Error occurred
- `cancelled` - User cancelled

**Errors:**

- `404` - Job not found

---

### DELETE `/api/v1/jobs/{job_id}`

Cancel a running job.

**Auth:** Required  
**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

**Behavior:**

- If job already done → no-op, returns `ok`
- If job running → cancellation requested

---

## Data Preparation

Synchronous OSM and GeoJSON processing.

### POST `/api/v1/prepare/osm`

Synchronous OSM data preparation.

**Auth:** Required

**Request:**

```json
{
  "latitude": -21.7634,
  "longitude": -41.3235,
  "radius": 500
}
```

**Response:** `200 OK`

```json
{
  "features": [
    {
      "type": "LineString",
      "coordinates": [[x1, y1], [x2, y2]],
      "properties": {
        "name": "Rua Principal",
        "highway": "residential"
      }
    }
  ],
  "metadata": {
    "projection": "SIRGAS 2000 UTM",
    "feature_count": 42
  }
}
```

---

### POST `/api/v1/prepare/geojson`

Synchronous GeoJSON preparation.

**Auth:** Required

**Request:**

```json
{
  "geojson": {
    "type": "FeatureCollection",
    "features": [...]
  }
}
```

**Response:** Same as OSM prepare

---

## Tools

### POST `/api/v1/tools/elevation/query`

Query elevation at a single point.

**Auth:** Required

**Request:**

```json
{
  "latitude": -21.7634,
  "longitude": -41.3235
}
```

**Response:** `200 OK`

```json
{
  "latitude": -21.7634,
  "longitude": -41.3235,
  "elevation": 542.3
}
```

**Elevation Units:** Meters above sea level

---

### POST `/api/v1/tools/elevation/profile`

Get elevation profile along a path.

**Auth:** Required

**Request:**

```json
{
  "path": [
    [-21.7634, -41.3235],
    [-21.7640, -41.3240],
    [-21.7645, -41.3245]
  ]
}
```

**Response:** `200 OK`

```json
{
  "elevations": [542.3, 545.1, 548.7]
}
```

---

## AI

### POST `/api/v1/ai/chat`

Interact with sisRUA AI assistant (Groq-powered).

**Auth:** Required

**Request:**

```json
{
  "message": "Como faço para importar GeoJSON?",
  "context": {
    "current_project": "projeto123"
  },
  "job_id": "abc123"
}
```

**Response:** `200 OK`

```json
{
  "response": "Para importar GeoJSON, use o endpoint /api/v1/prepare/geojson..."
}
```

**Graceful Degradation:** If AI unavailable, returns generic message.

---

## Projects

### PUT `/api/v1/projects/{project_id}`

Update project metadata with optimistic locking.

**Auth:** Required

**Request:**

```json
{
  "version": 42,
  "name": "Novo Nome",
  "description": "Descrição atualizada"
}
```

**Response:** `200 OK`

```json
{
  "project_id": "proj123",
  "version": 43,
  "name": "Novo Nome",
  "description": "Descrição atualizada",
  "updated_at": "2026-02-01T21:00:00Z"
}
```

**Errors:**

- `404` - Project not found
- `409` - Version conflict (concurrent update)

**Optimistic Locking:** `version` must match DB version

---

## Webhooks

### POST `/api/v1/webhooks/register`

Register a webhook URL for system events.

**Auth:** Required

**Request:**

```json
{
  "url": "http://localhost:8080/webhook"
}
```

**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

---

### POST `/api/v1/events/emit`

Emit event for webhook broadcasting (internal use).

**Auth:** Required

**Request:**

```json
{
  "event_type": "project_saved",
  "payload": {
    "project_id": "proj123"
  }
}
```

**Response:** `200 OK`

```json
{
  "status": "ok"
}
```

**Event Types:**

- `job_started`
- `job_completed`
- `job_failed`
- `project_saved`
- `project_updated`

---

## Audit Logs

Cryptographically signed audit logging for sensitive mutations.

### POST `/api/audit`

Create audit log entry.

**Auth:** Required

**Request:**

```json
{
  "event_type": "UPDATE",
  "entity_type": "Project",
  "entity_id": "proj123",
  "user_id": "user456",
  "data": {
    "field": "name",
    "old_value": "Old",
    "new_value": "New"
  }
}
```

**Response:** `201 Created`

```json
{
  "audit_id": 1,
  "signature": "a1b2c3d4...",
  "timestamp": 1738454400.0
}
```

---

### GET `/api/audit/{audit_id}`

Get specific audit log entry.

**Auth:** Required  
**Response:** `200 OK`

```json
{
  "audit_id": 1,
  "event_type": "UPDATE",
  "entity_type": "Project",
  "entity_id": "proj123",
  "user_id": "user456",
  "timestamp": 1738454400.0,
  "data_json": "{...}",
  "signature": "a1b2c3d4...",
  "created_at": "2026-02-01T21:00:00Z"
}
```

---

### GET `/api/audit/{audit_id}/verify`

Verify audit log signature.

**Auth:** Required  
**Response:** `200 OK`

```json
{
  "audit_id": 1,
  "is_valid": true
}
```

**Verification:** HMAC-SHA256 signature check

---

### POST `/api/audit/verify-all`

Batch verify multiple audit logs.

**Auth:** Required

**Request:**

```json
{
  "audit_ids": [1, 2, 3, 4, 5]
}
```

**Response:** `200 OK`

```json
{
  "total": 5,
  "valid": 5,
  "invalid": 0,
  "results": [
    {"audit_id": 1, "is_valid": true},
    {"audit_id": 2, "is_valid": true},
    ...
  ]
}
```

---

### GET `/api/audit`

List audit logs with filters.

**Auth:** Required

**Query Parameters:**

- `entity_type` - Filter by entity type (e.g., "Project")
- `entity_id` - Filter by entity ID
- `event_type` - Filter by event (e.g., "UPDATE")
- `limit` - Max results (default: 100)
- `offset` - Pagination offset (default: 0)

**Example:**

```bash
GET /api/audit?entity_type=Project&limit=50
```

**Response:** `200 OK`

```json
{
  "logs": [...],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

### GET `/api/audit/stats`

Get audit log statistics.

**Auth:** Required  
**Response:** `200 OK`

```json
{
  "total_logs": 1250,
  "total_entities": 42,
  "event_types": {
    "UPDATE": 800,
    "INSERT": 350,
    "DELETE": 100
  }
}
```

---

## Error Responses

All errors return JSON with `detail` field.

### Common HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 400 | Bad Request | Invalid request body |
| 401 | Unauthorized | Missing/invalid token |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Optimistic lock failure |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Graceful degradation |

**Error Format:**

```json
{
  "detail": "Human-readable error message"
}
```

**Examples:**

**401 Unauthorized:**

```json
{
  "detail": "Unauthorized"
}
```

**404 Not Found:**

```json
{
  "detail": "Job not found"
}
```

**409 Conflict:**

```json
{
  "detail": "Version conflict - expected 42, got 41"
}
```

**429 Rate Limited:**

```json
{
  "detail": "Rate limit exceeded"
}
```

---

## API Stability Guarantee

**v0.8.x Stability Promise:**

> All `/api/v1/*` endpoints are stable and will not change incompatibly within v0.8.x patch releases.

**Guarantees:**

- ✅ No endpoint removals
- ✅ No required field additions to requests
- ✅ No response field removals
- ✅ No type changes

**Allowed:**

- ✅ New optional request fields
- ✅ New response fields
- ✅ New endpoints
- ✅ Bug fixes

---

## Interactive Documentation

**Swagger UI:** [http://localhost:5050/docs](http://localhost:5050/docs)  
**ReDoc:** [http://localhost:5050/redoc](http://localhost:5050/redoc)  
**OpenAPI JSON:** [http://localhost:5050/openapi.json](http://localhost:5050/openapi.json)

---

## CHANGELOG

### v0.8.0 (2026-02-01)

**Added:**

- Audit Log API (`/api/audit/*`) - 6 new endpoints
- Cryptographic signatures for audit logs (HMAC-SHA256)
- Database indexes for query optimization
- Secret management audit tooling

**Changed:**

- None (backward compatible)

**Security:**

- Added audit logging for sensitive mutations
- Verified zero secrets in build artifacts
