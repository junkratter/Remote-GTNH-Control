# ADR 002 — Robots module (Phase 4)

**Status:** accepted  
**Date:** 2026-05-16  

## Context

GTNH Cyber needs remote control of **OpenComputers robots** for crop farming
and GT miner deployment. OC only does **outgoing** HTTP; state is stored on
the monolith backend (`robots`, `mining_jobs` tables). Knowledge base:
`kb/02-opencomputers/component-robot.md`, `kb/03-gtnh/ic2-crops.md`,
`kb/03-gtnh/gt-miner.md`.

## Decision

1. **Lua plugins** `oc-client/plugins/robot_crop.lua` and
   `robot_miner.lua` live in `_G`, return `{ message, data }`, use `pcall`
   and `os.sleep(0)` in loops per `AGENTS.md` / `.cursor/rules/oc-lua.mdc`.

2. **Backend** exposes `/api/robots/*` for registry, state updates, and
   mining job CRUD. **Static routes** (`/mining-jobs`, `/mining-jobs/next`,
   `/mining-jobs/{id}`) are registered **before** `/{client_id}/state` so
   `mining-jobs` is never parsed as a client id.

3. **Execution on OC**: the UI (and operators) enqueue work via existing
   **`POST /api/task/add`** with `client_id` = robot’s `X-Client-ID` and
   commands such as `return robot_crop.harvestBelow()`. No change to the
   `/api/task/*` contract.

4. **Mining jobs** MVP: queue coordinates + metadata; `PATCH` advances
   state and sets `started_at` / `finished_at`. Full navigation/placement
   is deferred (documented in Lua `acceptJob` response).

## Consequences

- Operators must install new plugin files on OC robots and align `env.clientId`
  with registered `client_id`.
- OpenAPI may lag behind `PATCH` / `GET .../next` until `make openapi` is run;
  the web client uses `fetch` for those paths.

## Links

- `server/app/modules/robots/`
- `oc-client/plugins/robot_crop.lua`, `robot_miner.lua`
- `website/src/pages/Robots.vue`
