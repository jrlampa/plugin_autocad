# ADR 0003: Redis-backed Tiered Caching

## Status

Accepted

## Context and Problem Statement

GIS operations (OpenStreetMap queries and SRTM elevation lookups) are computationally expensive and involve high-latency external APIs. We need a way to reuse results across different requests and sessions.

## Decision Drivers

* Speed: Millisecond-level access to previous results.
* Persistence: Cache should survive service restarts.
* Distributed: Ability to share cache between multiple backend instances (Docker environment).

## Considered Options

1. Filesystem only: Simple but slow and IO-bound.
2. In-memory (Dict): Extremely fast but lost on restart.
3. Tiered Caching (Redis L1 + Filesystem L2): Redis for speed/sharing, Filesystem for persistent fallback.

## Decision Outcome

Chosen option: "Tiered Caching (Redis L1 + Filesystem L2)", because it offers high performance for active requests via Redis while ensuring local robustness and long-term persistence via the filesystem.

### Positive Consequences

* Drastic reduction in OpenTopography and OSM API calls.
* Faster AutoCAD plugin response times for repeated areas.

### Negative Consequences

* Adds Redis as a new infrastructure dependency.
