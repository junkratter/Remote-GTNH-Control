# ADR 004 — World map (Phase 5)

**Status:** accepted  
**Date:** 2026-05-16  

## Context

Operators need a coarse **world block map** fed by OpenComputers geolyzer /
robot telemetry. The browser cannot talk to Minecraft directly; data lands on
the monolith (`world_blocks` table) and the SPA renders markers (Leaflet).

## Decision

1. **HTTP API:** `POST /api/map/scan` accepts `{ observations: [...] }` with
   idempotent upsert on `(dimension, x, y, z)`. `GET /api/map/blocks` filters by
   dimension and optional bbox / block_name / fluid.

2. **OC plugin:** `oc-client/plugins/geolyzer_map.lua` exposes
   `geolyzer_map.push(observations)` (authenticated JSON POST using `env.baseUrl`,
   `env.serverToken`, `env.clientId`, `env.mapScanPath`) and
   `geolyzer_map.analyzeAt(dim, x, y, z, side)` helper wrapping `geolyzer.analyze`.

3. **UI:** `website/src/pages/Map.vue` — Leaflet `CRS.Simple`, dimension control,
   ore/fluid filters.

## Consequences

- Large scans should batch observations and call `os.sleep(0)` between pushes
  (OC watchdog / packet size).
- `setup.lua` in this repo still targets upstream `client/` by default; gtnh
  plugins are copied manually or wget from a published `oc-client/` tree (see
  `kb/02-opencomputers/oc-client-install.md`).

## Links

- `server/app/modules/worldmap/`
- `oc-client/plugins/geolyzer_map.lua`
- `website/src/pages/Map.vue`
