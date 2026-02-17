# ADR 0004: Internal Python SDK Architecture

## Status

Accepted

## Context and Problem Statement

As sisRUA grows, other internal python scripts and services need to interact with the API. Writing raw `requests.post` calls with manual payload construction is repetitive and lacks type safety.

## Decision Drivers

* DX (Developer Experience): Clear, typed API for scripters.
* Maintainability: Centralize API logic (base URLs, headers, polling).
* Robustness: Built-in handling for job status polling.

## Considered Options

1. Raw HTTP calls: High flexibility, low overhead, no maintenance.
2. Auto-generated client (OpenAPI): Generates a lot of boilerplate.
3. Hand-crafted Typed Wrapper (SDK): Tailored for sisRUA specific flows (like Jobs).

## Decision Outcome

Chosen option: "Hand-crafted Typed Wrapper (SDK)", because it allows us to include high-level logic like `wait_for_job` which is much more useful than simple auto-generated endpoints.

### Positive Consequences

* Strong typing in IDEs via backend Pydantic models.
* Simplified integration for external automation scripts.

### Negative Consequences

* Requires manual maintenance when API endpoints change.
