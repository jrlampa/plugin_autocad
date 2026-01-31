# ADR 0001: Async Webhook Broadcasting

## Status

Accepted

## Context and Problem Statement

The sisRUA system needs to notify external subscribers (like CI/CD pipelines or monitoring tools) about job status changes and project events. These notifications must not block the main API execution or the heavy worker threads performing GIS computations.

## Decision Drivers

* Performance: Webhook delivery latency should not impact user experience.
* Reliability: Transient network failures during delivery should be logged but not crash the system.
* Simplicity: Implementation should be lightweight without requiring a full message broker (like RabbitMQ) for now.

## Considered Options

1. Synchronous requests: Block the caller until the webhook responds.
2. Background thread pool: Fire-and-forget using a `ThreadPoolExecutor`.
3. Full Message Queue (Redis/Celery): Use a formal task queue for delivery.

## Decision Outcome

Chosen option: "Background thread pool (ThreadPoolExecutor)", because it provides the best balance between implementation speed and non-blocking behavior for current scale.

### Positive Consequences

* API response times are decoupled from webhook latency.
* Isolated failures: A slow or offline webhook target doesn't block the backend.

### Negative Consequences

* No persistence: If the backend crashes, pending webhook deliveries in the pool are lost.
