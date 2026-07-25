# ADR 0003 — SQLite + filesystem for Lean persistence

## Status

Accepted

## Context

Lean MVP needs durable storage for metadata, structured JSON, and original PDFs without operational complexity.

## Decision

- **SQLite** for record metadata and JSON
- **Filesystem** for PDF binaries under `data/uploads/`

## Consequences

- Trivial local/Docker setup
- Adequate for single-user demo
- Easy migration path to Postgres + object storage later
