# ADR 0002: Centralized Schema Registry

## Status

Accepted

## Context and Problem Statement

sisRUA spans Python (Backend), C# (Plugin), and TypeScript (Frontend). Keeping data contracts (like `CadFeature`) consistent across these three environments manually is error-prone and leads to runtime failures.

## Decision Drivers

* Sync: Changes in Python models must be reflected in other layers.
* Validation: Ability to verify contract integrity in the QA suite.
* Portability: Use a language-agnostic format (JSON Schema).

## Considered Options

1. Manual synchronization: Define classes in all 3 languages manually.
2. Pydantic-to-JSON-Schema: Use Pydantic as the "Source of Truth" and export schemas.
3. Protobuf: Use a neutral IDL for all layers.

## Decision Outcome

Chosen option: "Pydantic-to-JSON-Schema", because it leverages the existing rich models in Python while providing standard JSON Schemas that C# and TypeScript can consume or validate against.

### Positive Consequences

* Automated schema verification in CI.
* Clear versioning of contracts in the `schema/` directory.

### Negative Consequences

* Requires an extra build/export step.
