---
description: Seed the database with dummy data
---

# Database Seeding Workflow

## Goal

Create a script to populate the database with dummy data.

## Steps

1. **Analyze Schema**: Analyze the database schema or ORM models (e.g., SQLAlchemy models, Prisma schema).
2. **Identify Relationships**: Identify relationships between tables (foreign keys).
3. **Create Script**: Create a script (e.g., `seed.py` or `seed.ts`) that uses a faker library to generate 50 realistic records for each table.
4. **Order**: Ensure records are inserted in the correct order to satisfy foreign key constraints.
