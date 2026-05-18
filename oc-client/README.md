# OpenComputers Lua client

Polls the monolith backend (`/api/task/get`), executes Lua snippets, reports to
`/api/task/report`. Plugins in `plugins/*.lua` load automatically (see
`src/executor.lua`).

## Quick links

- Install layout (RU/EN): `kb/02-opencomputers/oc-client-install.md`
- AE2 + pattern programming: `plugins/ae.lua`
- Robots: `plugins/robot_crop.lua`, `plugins/robot_miner.lua`
- Map: `plugins/geolyzer_map.lua` (`geolyzer_map.push` → `/api/map/scan`)

## Configure

Copy `env.lua.example` → `env.lua` (не коммитить `env.lua` в git).  
Set `baseUrl`, `serverToken`, `clientId`, `aeAddress`.

## Run

```text
lua run.lua
lua run.lua --debug
```
