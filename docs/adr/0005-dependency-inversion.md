# 5. Protocol-based Dependency Inversion

Date: 2026-02-01

## Status

Accepted

## Context

The backend codebase suffered from tight coupling between high-level business logic (e.g., `OSM` preparation, `Job` management) and low-level infrastructure services (`Redis` caching, `Webhook` broadcasting). This created several issues:

1. **Testing Difficulty**: Unit tests required mocking global singletons or patching imports, which is brittle.
2. **Refactoring rigidity**: Changing the caching provider or webhook mechanism required modifying core business logic files.
3. **Circular Imports**: Inter-dependencies between modules (e.g., jobs -> webhooks -> api) were becoming complex.

## Decision

We decided to implement the **Dependency Inversion Principle (DIP)** using Python **Protocols** (interfaces).

1. **Interfaces**: Defined `ICache`, `INotificationService`, and `IEventBus` in `backend/core/interfaces.py`. These define *what* is needed, not *how* it is implemented.
2. **Explicit Injection**: Services (`ElevationService`, `JobService`) and functions (`prepare_osm_compute`) now explicitly declare their dependencies in their `__init__` or function signatures.
3. **Composition Root**: The `api.py` module acts as the "Composition Root", responsible for instantiating concrete implementations (`CacheService`, `InMemoryEventBus`) and injecting them into the logic layers at runtime.

## Consequences

### Positive

- **Testability**: We can now easily pass mock objects (e.g., `MockCache`, `MockEventBus`) into services during tests without monkey-patching.
- **Decoupling**: Core domain logic is now pure and unaware of external infrastructure (Redis, HTTP).
- **Flexibility**: We can swap implementations (e.g., switch from In-Memory Bus to RabbitMQ) by changing only the Composition Root.

### Negative

- **Boilerplate**: Function signatures are slightly more verbose due to dependency arguments.
- **Complexity**: Developers must be aware of where dependencies come from (the root) rather than just importing them.
