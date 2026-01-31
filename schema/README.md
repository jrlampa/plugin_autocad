# sisRUA Schema Registry (v1)

This directory contains versioned JSON Schema definitions for all shared data models used in the sisRUA ecosystem.

## Structure

- `/v1/`: Active production schemas.

## Source of Truth

The **Backend** (Pydantic models in `src/backend/backend/models.py`) is the primary source of truth.

## How to Update

If you change models in the backend, run the following command to update the registry:

```powershell
python tools/export_schemas.py
```

## How to Verify

The QA suite automatically verifies if the schemas match the current code:

```powershell
.\tools\verify_schemas.ps1
```

## Components Usage

- **Backend**: Uses Pydantic to enforce these schemas at runtime.
- **Frontend**: Can use these schemas for form validation (e.g., using `ajv` or similar).
- **AutoCAD Plugin**: Mirrored C# classes should align with these definitions.
