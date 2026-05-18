# ADR 006 — Craft domain redesign (planner, aliases, plans, CPU affinity)

**Status:** implemented
**Date:** 2026-05-18
**Completed:** 2026-05-18

## Context

The current autocraft module (`server/app/modules/autocraft/`, ADR 003) is
intentionally thin:

- `AutocraftPattern` describes a physical ME interface slot.
- `AutocraftRequest` is a flat FIFO of `ae.requestItem(...)` calls.
- The web UI resolves recipes on the client side via multiple
  `/api/nesql/*` round-trips.

This works for one-shot crafts but does not behave like classic ME
autocraft: when an ingredient is missing the UI shows no alternatives,
items with different IDs that are functionally interchangeable are
treated as distinct, and there is no concept of a multi-step plan owned
by the backend.

Additional constraints captured from the deployment:

- **OC client count** is expected to grow above 5 simultaneous clients
  (controller + miners + crop farms + power robots). The task store must
  hand out work atomically to whichever OC polls first.
- **Single party per instance** — no multi-tenant auth required. No
  `owner_id` on craft jobs.
- **CPU affinity** matters: certain recipes should be pinned to a
  specific AE crafting CPU (capacity / coprocessor balance, dedicated
  EBF/PA lines).
- **OreDict** in NESQL is exported via the `forge` plugin
  (see `kb/04-nesql/export-howto.md:70`). GregTech adds partial
  `GT_OreDictUnificator` mapping on top, so OreDict gives a good
  baseline of aliases but does not cover everything — manual overrides
  are expected for cases like fluid-drop labels and NBT-tagged items.

OC robots only talk outgoing HTTP (long-poll on `/api/task/*`,
`kb/01-architecture/oc-polling.md`); the new domain must not change that
contract.

## Decision

### 1. Storage migration: SQLite → PostgreSQL for the main DB

The new domain needs `SELECT … FOR UPDATE SKIP LOCKED`, `JSONB`
operators, and `LISTEN/NOTIFY` for SSE fan-out. SQLite cannot provide
these.

- Main DB (`settings.database_url`) migrates to PostgreSQL 16+ via
  Alembic. The async URL becomes `postgresql+asyncpg://…`.
- NESQL stays a read-only SQLite file (`settings.nesql_database_url`).
  Import pipeline in `tools/nesql-import/` is unchanged.
- `server/app/db/session.py` removes the SQLite-only
  `check_same_thread=False` branch when the target dialect is not
  `sqlite`.

### 2. Alias model

New tables on the main DB:

```
craft_aliases               (id, key, source, priority, created_at)
craft_alias_members         (alias_id, nesql_item_id, damage, nbt_hash,
                             weight, preferred)
```

- `source` ∈ `{'oredict', 'manual', 'nbt'}`. OreDict groups
  (`nesql_oredict` / `nesql_oredict_items`) seed `source='oredict'` on
  every NESQL import.
- `priority` orders members **inside** a group. The planner prefers
  members with higher `priority` and higher current AE stock.
- `weight` lets `1 plate ≡ 1 plate` even across mods with different
  stack semantics; default `1`.

### 3. Resolved recipe model

```
craft_recipes_resolved     (id, nesql_recipe_id, machine, duration_ticks,
                            eu_per_tick, hash_inputs, preferred_cpu)
craft_recipe_inputs        (recipe_id, slot, alias_id, fluid_id, amount,
                            required)
craft_recipe_outputs       (recipe_id, slot, alias_id, fluid_id, amount,
                            chance_ppm)
```

- Each row is a denormalised mirror of one NESQL recipe with inputs and
  outputs pointing at **alias groups**, not item IDs.
- `preferred_cpu` is **per recipe**, nullable. When set, the planner
  always routes that recipe to the named AE CPU. Used for EBF lines and
  heavy single-CPU patterns.
- `chance_ppm` keeps probabilistic outputs (GT ore processing, IC2
  centrifuge) in integer parts-per-million.

Rebuild is non-destructive: a Python job
(`tools/nesql-import/build_resolved.py` or a backend command) walks
NESQL after each import and replaces `craft_recipes_resolved` /
`craft_recipe_*` in a single transaction.

### 4. Plan model

```
craft_plans                (id, root_job_id, plan_json, status,
                            created_at, finished_at)
craft_jobs                 (id, parent_id, root_id, plan_id,
                            goal_alias_id, goal_amount,
                            chosen_recipe_id, preferred_cpu,
                            state, missing, alternatives,
                            client_id, task_id, error,
                            created_at, updated_at)
```

`craft_jobs.state` is a small enum:

```
planning → awaiting_choice → awaiting_input
        ↘ ready → programmed → crafting → done
                                       ↘ failed
                                       ↘ cancelled
```

- `parent_id` builds the dependency tree; `root_id` lets a single index
  scope an entire plan.
- `missing` and `alternatives` are JSONB blobs frozen at planning time
  for fast UI rendering of the popup.
- `client_id` and `task_id` connect to the existing `task_store` so
  every OC-bound job still flows through `/api/task/get` and
  `/api/task/report` without contract changes.

### 5. Planner / resolver service

New module `server/app/modules/craft/`:

- `solver.py` — pure async function `plan(goal_alias_id, amount, ctx)`
  returning a `CraftPlan` DTO.
- Inputs to the solver:
  - AE snapshot (Redis-cached, see §7),
  - `craft_recipes_resolved` graph,
  - `craft_aliases` membership.
- Algorithm (classic ME semantics):
  1. Try to satisfy `goal_alias_id` from AE snapshot.
  2. Otherwise enumerate recipes whose `craft_recipe_outputs.alias_id`
     equals the goal.
  3. Rank by `(available_inputs_ratio, member_priority,
     eu_per_tick × duration, depth)`.
  4. If ≥2 candidates differ materially, mark the job
     `awaiting_choice` and surface `alternatives`.
  5. Otherwise pick the best candidate, recurse into each input.
  6. Guard against cycles (`(alias_id, depth)` seen-set) and limit
     depth (default 12) and intermediate amounts
     (`min(goal_amount × 64, 1_000_000)`).
- CPU affinity: if the chosen recipe has `preferred_cpu`, the resulting
  `craft_jobs.preferred_cpu` is set; otherwise the planner picks an
  idle CPU via `ae.getCpuList` snapshot.

### 6. Atomic task dispatch

`task_store.claim_next` (`server/app/core/tasks.py`) gains a
PostgreSQL-only fast path:

```sql
SELECT id FROM tasks
WHERE client_id = $1 AND status = 'ready'
ORDER BY created_time
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

This is required because >5 OC clients are expected. On SQLite (legacy
dev environment) the existing serialised path is kept behind a feature
flag.

### 7. Redis as L1 cache + event bus

Behind `OPTIONAL_REDIS_URL`. None of the persistent state lives in
Redis.

| Key                                            | TTL    | Producer                                     |
|------------------------------------------------|--------|----------------------------------------------|
| `ae:{client_id}:items`                         | 30 s   | `/api/task/report` for AE snapshot tasks     |
| `ae:{client_id}:cpus`                          | 30 s   | `/api/task/report` for `ae.getCpuList`       |
| `nesql:item:{unlocal}:{dmg}`                   | 24 h   | NESQL handlers                               |
| `nesql:recipes_by_output:{alias_id}`           | 24 h   | NESQL / resolver                             |
| `solver:{sha256(goal,amount,ae_state_hash)}`   | 15 s   | resolver                                     |
| `cpu:{client_id}:{cpu_name}` (NX, EX 1800)     | 30 min | dispatcher                                   |
| Channel `evt:craft`, `evt:robots`, `evt:cpus`  | —      | resolver / task handlers                     |

Resolver and `/api/task/report` publish events; SSE handler subscribes
and pushes to the SPA.

### 8. Push to SPA: SSE over PG `LISTEN/NOTIFY` (Redis Pub/Sub fallback)

Trade-off summary:

- **SSE wins over polling** because the UI updates many short-lived
  states (job state transitions, CPU busy flips, robot heartbeat) and
  polling at 1 s × N tabs × M topics quickly saturates uvicorn workers.
- **SSE over WebSocket** because the channel is server → client only;
  WebSocket adds bidirectional plumbing we do not use, and SSE behaves
  well behind the existing nginx (`proxy_buffering off;
  proxy_http_version 1.1;`).
- **SSE over PG `LISTEN/NOTIFY` is preferred** to keep the event bus
  inside Postgres (a service we already need). When `OPTIONAL_REDIS_URL`
  is set, the SSE handler additionally subscribes to Redis Pub/Sub for
  events that originate outside Postgres (e.g. raw AE snapshot
  refresh).

Endpoint: `GET /api/events?topics=craft,robots,cpus`. Heartbeats every
15 s, automatic reconnect on the client.

### 9. OC plugin: bulk pattern programmer + snapshot helper

New plugin `oc-client/plugins/ae_patterns.lua` (registered via
`oc-client/src/executor.lua` like other plugins):

- `ae.bulkProgramPatterns(plan)` — iterates `plan` array
  `[{iface, slot, kind, inputs, outputs}, …]` and programs all slots
  inside a single OC task. Saves N polling cycles compared to the
  current per-slot two-command pair in
  `server/app/modules/autocraft/service.py:48-64`.
- `ae.snapshotForSolver()` — light snapshot (`name`, `damage`, `size`,
  `label`) without NBT body, plus `os.time()` server-side timestamp.
- `ae.cpuLockedTry(cpuName, fn)` — guard helper that calls `fn` only if
  the CPU is named, exists, and idle.

`/api/task/*` JSON shape stays untouched; only new Lua entry points.

### 10. Adapter for legacy `AutocraftRequest`

`AutocraftRequest` is **not** deleted in this ADR. The existing
`service.enqueue_craft()` (`server/app/modules/autocraft/service.py:86`)
is rewritten to create a `craft_jobs` root and a `craft_plan` via the
new planner, then map the result back into the legacy row. SPA pages
keep working while the new `/api/craft/*` endpoints are rolled out and
the new pages are written.

Removal of `AutocraftRequest` will happen in a follow-up ADR once
`website/src/pages/Autocraft.vue` and friends migrate fully.

## Consequences

- PostgreSQL becomes a required dependency for production. The dev
  experience can keep SQLite for unit tests but loses parallel dispatch.
- The OreDict bootstrap relies on `forge` plugin being enabled during
  NESQL export (see `kb/04-nesql/export-howto.md:70`). The import job
  refuses to seed `craft_aliases` from a NESQL dump that lacks
  `nesql_oredict` and falls back to manual aliases only, with a
  clear error in `/api/nesql/meta`.
- The planner is bounded but not optimal — it minimises a heuristic
  cost, not actual EU/sec or real ME storage churn. Operators can
  override choices via the popup and the chosen recipe persists in
  `craft_jobs.chosen_recipe_id` for replays.
- Redis is optional; the system must function (slower) without it.
- The OC contract `/api/task/*` is **frozen** as per
  `kb/01-architecture/api-contract.md` and is **not** modified by this
  ADR.

## Links

- ADR 003 — Autocraft (Phase 3): `kb/01-architecture/decisions/003-autocraft-phase3.md`
- ADR 005 — Performance baseline: `kb/01-architecture/decisions/005-perf-baseline.md`
- API contract: `kb/01-architecture/api-contract.md`
- OC polling model: `kb/01-architecture/oc-polling.md`
- NESQL schema: `kb/04-nesql/schema.md`
- AE2 patterns: `kb/03-gtnh/ae2-patterns.md`
- Existing modules: `server/app/modules/autocraft/`, `oc-client/plugins/ae.lua`
