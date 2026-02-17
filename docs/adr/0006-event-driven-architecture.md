# 6. Event-Driven Architecture (Pub/Sub)

Date: 2026-02-01

## Status

Accepted

## Context

The backend needed to perform side-effects based on state changes (e.g., notifying a webhook when a Job finishes), but direct invocation led to:

1. **Blocking Operations**: The Job Service would wait for HTTP requests to finish.
2. **Coupling**: The Job Service had to import and know about the Webhook Service.
3. **Reliability Risks**: If the Webhook Service crashed or hung, the Job update could fail.
4. **Duplicate Events**: Retries or race conditions could cause the same event (e.g., "Job Completed") to be processed multiple times.

## Decision

We adopted an **Event-Driven Architecture** using an internal **Pub/Sub Event Bus** with **Idempotency Gates**.

1. **Event Bus**: An `InMemoryEventBus` (implementing `IEventBus`) acts as a mediator. Services publish events (`job_completed`) without knowing who is listening.
2. **Subscribers**: The `WebhookService` subscribes to relevant events at startup (`api.py`).
3. **Idempotency**: The `EventBus` uses the caching layer (`CacheService`) to track processed event keys. It suppresses duplicate events within a short TTL window, ensuring exactly-once (or at-most-once) processing for side-effects.

## Consequences

### Positive

- **Non-blocking**: Events are dispatched to handlers which can run asynchronously (though currently they run synchronously in the thread pool, the pattern allows for easy async offloading).
- **Robustness**: Failures in subscribers (Webhooks) do not crash the publisher (Job Service).
- **Extensibility**: Adding new listeners (e.g., Audit Logging, Analytics) requires zero changes to the Job logic.
- **Data Integrity**: Idempotency gates prevent double-notification bugs.

### Negative

- **Indirection**: It is harder to trace the flow of execution statically (you can't just "Go to Definition" to see who handles an event).
- **State Visibility**: Debugging requires following logs to see event emission and consumption.
