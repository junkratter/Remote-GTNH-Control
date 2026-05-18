# ADR 003 — Autocraft (AE2 patterns + queue)

**Status:** accepted  
**Date:** 2026-05-16  

## Context

GTNH Cyber extends RemoteOC with **programmable ME Interface slots** and a
**craft request queue** driven from the web UI. OC still only polls
`/api/task/get`; there is no push to Minecraft.

## Decision

1. **Persistence:** `autocraft_patterns` (unique per `interface_address` + `slot`)
   and `autocraft_requests` in SQLite via SQLAlchemy.

2. **Pattern push:** `POST /api/autocraft/patterns/{id}/program` enqueues two Lua
   snippets: `ae.setMeInterfaceAddress(...)` then `ae.programPattern(...)` (see
   `server/app/modules/autocraft/service.py` and `oc-client/plugins/ae.lua`).
   GTNH exposes `setInterfacePatternInput` / `setInterfacePatternOutput` on the
   interface component.

3. **Craft queue:** `POST /api/autocraft/request` stores a row and enqueues
   `ae.requestItem(...)`. When OC posts `/api/task/report` for a `craft_*`
   task id, the backend updates the row to `done` or `failed` and stores a
   JSON summary in `result` (`sync_craft_request_after_report` in
   `app/modules/autocraft/service.py`, invoked from `app/api/task.py`).

4. **Cancel:** `POST .../cancel` schedules `ae.cancelCraftingByCpuName` and sets
   state `cancelling`. Late craft reports are ignored while in that state.

5. **UI:** Vue page `website/src/pages/Autocraft.vue` — tabs *Patterns* and
   *Craft queue*; optional **NESQL** picker fills inputs/outputs from imported
   recipe data (`/api/nesql/*`).

## Consequences

- Operators must use an ME **Interface** (not only ME Chest) with the GTNH
  programming API; otherwise `ae.programPattern` returns a clear error message.
- NESQL import is optional but improves pattern authoring.

## Links

- `server/app/modules/autocraft/`
- `oc-client/plugins/ae.lua`
- `website/src/pages/Autocraft.vue`
