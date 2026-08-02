# ADR 0003 — SQLite + filesystem for Lean persistence

## Status

Accepted

## Context

Lean MVP needs durable storage for metadata, structured JSON, and original uploaded files (PDF and .docx) without operational complexity.

## Decision

- **SQLite** for record metadata and JSON
- **Filesystem** for original file binaries under `data/uploads/` as `{id}.pdf` or `{id}.docx`

## Consequences

- Trivial local/Docker setup
- Adequate for single-user demo
- Easy migration path to Postgres + object storage later
