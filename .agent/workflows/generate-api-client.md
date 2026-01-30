---
description: Generate TypeScript API client
---

# API Client Generator

## Goal

Create a TypeScript frontend service for the selected backend code.

## Steps

1. **Read Backend File**: Read the currently open backend file (e.g., Python FastAPI or Node Express).
2. **Identify Endpoints**: Identify all API routes, methods (GET/POST), and required payload schemas.
3. **Create Client File**: Create a corresponding TypeScript file (e.g., `api.ts`).
4. **Define Interfaces**: Define TypeScript interfaces for all request and response bodies.
5. **Implement Functions**: Write an async function for each endpoint using `fetch` or `axios`.
