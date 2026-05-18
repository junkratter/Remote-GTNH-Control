# ADR 007 — Retire legacy AutocraftRequest

**Status:** accepted  
**Date:** 2026-05-18

## Context

The SPA and OC clients are migrating to the craft domain (`/api/craft/*`, ADR-006).
`AutocraftRequest` and `/api/autocraft/request` remain during the transition.

## Decision

1. Mark `/api/autocraft/request` as **deprecated** in OpenAPI (one release).
2. After consumers move to `/api/craft/plan` + task mirroring, drop `autocraft_requests`
   and related tables via Alembic.

## Consequences

- No change to `/api/task/*` contract.
- Legacy queue rows may be recreated from mirrored `craft_jobs` if needed before drop.
