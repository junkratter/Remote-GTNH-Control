# gtnh-cyber

**GTNH Cyber Supervisor** — remote monitoring and control for **Applied Energistics 2** in **GregTech: New Horizons** via **OpenComputers** and a web UI.

**English** · [Русский](README.ru.md)

Fork and extension of [RemoteOC-GTNH-AE2](https://github.com/z5882852/RemoteOC-GTNH-AE2) (upstream [RemoteOC](https://github.com/z5882852/RemoteOC)). You need a host reachable from the game network (LAN or public) for the API/UI, and one or more OC computers as clients.

---

## Architecture

```text
Browser (Vue 3 SPA) ──HTTP──▶ FastAPI monolith ◀── long-poll ── OpenComputers (Lua)
                                      │
                                      └── SQLite (tasks, robots, map, autocraft, …)
                                      └── nesql.sqlite (Wiki / quests / recipe lookup)
```

OpenComputers can only make **outgoing** HTTP requests → the backend is a **single monolith** with one task queue for all modules. There is no server push to OC.

---

## Features

### From upstream RemoteOC

| Area | Description |
|------|-------------|
| **AE2 network** | View items, fluids, essentia; CPU list and status |
| **Remote craft** | Order crafts from the web UI (`ae.requestItem`) |
| **Automation** | Triggers and timers (`/api/automate/*`, `config.py` tasks) |
| **Multi-client** | Several OC `clientId` values on one backend |
| **UI** | Dark theme, mobile layout, configurable backend URL and token |

### Added in gtnh-cyber

| Area | Description |
|------|-------------|
| **Autocraft** | ME Interface pattern programming (`setInterfacePattern*`), craft queue, status sync after OC reports — [`/api/autocraft/*`](server/app/modules/autocraft/), UI **Autocraft** |
| **Robots** | Registry (`/api/robots/*`), mining jobs with OC enqueue, power-generator deploy — plugins `robot_crop`, `robot_miner`, `robot_power` |
| **World map** | `POST /api/map/scan`, Leaflet page — plugin `geolyzer_map` |
| **Quests** | Better Questing board from NESQL — `/api/quests/*` |
| **Wiki** | Read-only item/recipe browser — `/api/nesql/*` |
| **i18n** | Web UI: **en / ru / zh** (vue-i18n + Element Plus) |
| **Persistence** | Docker volume `gtnh_cyber_data` for SQLite; deploy/backup scripts |
| **Tests** | pytest integration + `/api/task/*` contract tests |

---

## Repository layout

```text
gtnh-cyber/
├── server/              FastAPI, SQLAlchemy 2, Alembic, SQLite
├── website/             Vue 3, Element Plus, Vite, vue-i18n
├── oc-client/           Lua client + plugins (see oc-client/README.md)
├── tools/
│   ├── kb-fetch/        Refresh kb/ excerpts from wikis
│   ├── nesql-import/    HSQLDB (in-game export) → nesql.sqlite
│   └── deploy/          Docker bootstrap, backup, robot seed
├── kb/                  Knowledge base, ADR, OC/GTNH guides
├── docker-compose.yml
└── Makefile
```

---

## Requirements

| Component | Version |
|-----------|---------|
| Backend | Python **3.11** (`server/Dockerfile`) |
| Frontend | Node **18+**, npm |
| Docker (optional) | Docker Compose v2 |
| OC client (in-game) | OpenComputers **1.11.x** (GTNH), Internet Card, ME adapter |
| NESQL (optional) | Java JDK for `tools/nesql-import`, [nesql-exporter](https://github.com/GTNewHorizons/nesql-exporter) mod in the client |

---

## Quick start (Docker)

```bash
git clone <your-fork-url> gtnh-cyber
cd gtnh-cyber
git submodule update --init --recursive   # optional: kb/05-vendored

cp .env.example .env
# Edit SERVER_TOKEN (random secret, same everywhere below)

docker compose up -d --build
```

| Service | Default host port | In-container |
|---------|-------------------|--------------|
| Web UI | **8855** | nginx :80 (proxies `/api/` → backend) |
| API | **8856** | uvicorn :1030 |

- UI: `http://<host>:8855`
- API docs: `http://<host>:8856/docs`

Override ports in `.env`: `FRONTEND_PORT_HOST`, `BACKEND_PORT_HOST`.

**Persistent data:** SQLite files live in Docker volume **`gtnh_cyber_data`** (survives image rebuilds). Mirror to the host for backups:

```bash
chmod +x tools/deploy/*.sh
./tools/deploy/backup-data.sh    # → ./data/backend/
```

See [`tools/deploy/README.md`](tools/deploy/README.md) for seed/restore and robot bootstrap.

---

## Configuration

### Backend (`.env`)

Copy [`.env.example`](.env.example) → `.env`:

| Variable | Purpose |
|----------|---------|
| `SERVER_TOKEN` | Shared secret; header `X-Server-Token` on API and SPA |
| `LOG_LEVEL` | e.g. `INFO` |
| `BACKEND_PORT_HOST` / `FRONTEND_PORT_HOST` | Host port mapping (optional) |

Do **not** commit `.env` or `server/.env`.

### Web UI (browser)

Open **Settings** in the SPA:

| Field | Typical value |
|-------|----------------|
| Backend URL | Leave **empty** when using the built-in nginx proxy on the same host (`:8855`); or `http://<host>:8856` |
| Server token | Same as `SERVER_TOKEN` |

### OpenComputers (`oc-client/env.lua`)

```bash
cp oc-client/env.lua.example oc-client/env.lua
```

| Field | Purpose |
|-------|---------|
| `baseUrl` | Backend root, e.g. `http://127.0.0.1:8856` on the MC host |
| `clientId` | OC client id (e.g. `client_01` for AE) |
| `serverToken` | Same as `SERVER_TOKEN` |
| `aeAddress` | ME controller/interface UUID (AE clients only) |

Do **not** commit `oc-client/env.lua`.

**OC hardware (AE client):** T3 CPU/APU, enough RAM for your item count (see upstream README), Internet Card, adapter next to ME. Memory tips: upstream suggests scaling RAM when AE exceeds ~1000 item types.

**Filtering rules:** private IPs are blocked by default in GTNH OC — allow your backend subnet in `OpenComputers.cfg`. See [`kb/02-opencomputers/filtering-rules.md`](kb/02-opencomputers/filtering-rules.md).

---

## Local development

```bash
make install                 # server venv + website npm + kb-fetch deps
cp .env.example .env

make backend                 # API on :1030 (foreground)
make frontend                # Vite dev server (see website/package.json)
```

```bash
make test                    # pytest + contract tests
make openapi                 # regenerate website OpenAPI types after API changes
make kb-update               # refresh kb/ wiki slices (tools/kb-fetch)
```

---

## OpenComputers client

### Install

| Method | Doc |
|--------|-----|
| Copy `oc-client/` to OC disk | [`kb/02-opencomputers/oc-client-install.md`](kb/02-opencomputers/oc-client-install.md) |
| Crop / miner / power robots | [`kb/02-opencomputers/robots-setup.ru.md`](kb/02-opencomputers/robots-setup.ru.md) (RU, detailed) |
| Power generators (GT) | [`kb/03-gtnh/gt-power-deploy.md`](kb/03-gtnh/gt-power-deploy.md) |

### Run

```text
cd /home/<your-oc-folder>
lua run.lua
lua run.lua --debug
```

Plugins under `plugins/*.lua` load automatically (`ae`, `robot_crop`, `robot_miner`, `robot_power`, `geolyzer_map`, …).

### Register robots (web)

**Robots** → **Registry**: set `client_id`, role (`ae`, `crop`, `miner`, `power`, …), label.  
Or seed from JSON:

```bash
cp tools/deploy/robots.seed.example.json tools/deploy/robots.seed.json
# edit, then:
export SERVER_TOKEN=...
./tools/deploy/bootstrap-robots.sh
```

### Task API contract

Do **not** change `/api/task/get`, `/api/task/report`, `/api/task/chunked_report`, or the `{ code, message, data }` envelope without:

1. Updating `oc-client/src/executor.lua`
2. Updating [`kb/01-architecture/api-contract.md`](kb/01-architecture/api-contract.md)
3. Extending [`server/tests/contract/test_task_contract.py`](server/tests/contract/test_task_contract.py)

---

## Web application (pages)

| Route / area | Function |
|--------------|----------|
| **Items** | AE storage browser, remote craft dialog |
| **CPUs** | Crafting CPU status |
| **Tasks** | Named tasks (`getAllItems`, …) via `/api/task/task` |
| **Automate** | Triggers and timers |
| **Autocraft** | ME patterns + craft queue |
| **Robots** | Registry, mining jobs, power jobs |
| **Map** | Scanned blocks (geolyzer) |
| **Quests** | Quest tree / board from NESQL |
| **Wiki** | Items and recipes (NESQL) |
| **Settings** | Backend URL, token, map origin, i18n |

Named AE tasks default to `client_id: client_01` in [`server/app/automation/config.py`](server/app/automation/config.py) — change to match your `env.lua`.

---

## NESQL (Wiki, quests, autocraft picker)

### 1. Export in Minecraft (client)

Official mod: **[GTNewHorizons/nesql-exporter](https://github.com/GTNewHorizons/nesql-exporter)**.

- Build **`NESQL-Exporter-<version>.jar`** + **`-deps.jar`** (`./gradlew build` → `build/libs/`, version in `gradle.properties`, e.g. **0.5.2**).
- Install **only that pair** into the instance **`mods/`** (client; not dedicated server `mods/`).
- In world: **`/nesql`** (optional subfolder name).
- Output: `.minecraft/nesql/` (HSQLDB dump).

Details: [`kb/04-nesql/export-howto.md`](kb/04-nesql/export-howto.md).

### 2. Import into backend

```bash
cd tools/nesql-import
pip install -r requirements.txt

python import.py \
  --src /path/to/nesql-db \
  --dst /path/to/data/backend/nesql.sqlite \
  --hsqldb-jar ./vendor/hsqldb-2.7.4.jar
```

After Docker import, copy into the volume or run [`tools/deploy/restore-data-volume.sh`](tools/deploy/restore-data-volume.sh) and `docker compose restart backend`.

Without import, Wiki/quests/recipe search return empty or 404.

**Wiki icons:** `website/public/items_GTNH280.json` + `website/public/img/items/` — [`kb/04-nesql/wiki-icons.ru.md`](kb/04-nesql/wiki-icons.ru.md).

---

## Documentation index

### Architecture & API

| Document | Description |
|----------|-------------|
| [`kb/01-architecture/overview.md`](kb/01-architecture/overview.md) | Deployment template, troubleshooting |
| [`kb/01-architecture/api-contract.md`](kb/01-architecture/api-contract.md) | `/api/task/*` contract |
| [`kb/01-architecture/oc-polling.md`](kb/01-architecture/oc-polling.md) | Long-poll flow |
| [`kb/01-architecture/implementation-status.md`](kb/01-architecture/implementation-status.md) | Feature checklist |
| [`kb/01-architecture/decisions/`](kb/01-architecture/decisions/) | ADRs (monorepo, robots, autocraft, map, …) |

### OpenComputers & GTNH

| Document | Description |
|----------|-------------|
| [`kb/02-opencomputers/oc-client-install.md`](kb/02-opencomputers/oc-client-install.md) | File layout, wget |
| [`kb/02-opencomputers/robots-setup.ru.md`](kb/02-opencomputers/robots-setup.ru.md) | Robots setup (RU) |
| [`kb/02-opencomputers/filtering-rules.md`](kb/02-opencomputers/filtering-rules.md) | `OpenComputers.cfg` HTTP allowlist |
| [`kb/02-opencomputers/component-me.md`](kb/02-opencomputers/component-me.md) | ME / AE2 Lua API notes |
| [`kb/02-opencomputers/component-internet.md`](kb/02-opencomputers/component-internet.md) | Internet card |
| [`kb/03-gtnh/ae2-patterns.md`](kb/03-gtnh/ae2-patterns.md) | Pattern programming |
| [`kb/03-gtnh/gt-miner.md`](kb/03-gtnh/gt-miner.md) | GT miners |
| [`kb/03-gtnh/ic2-crops.md`](kb/03-gtnh/ic2-crops.md) | IC2 crops |
| [`kb/03-gtnh/gt-power-deploy.md`](kb/03-gtnh/gt-power-deploy.md) | Power robots |

### NESQL & tools

| Document | Description |
|----------|-------------|
| [`kb/04-nesql/schema.md`](kb/04-nesql/schema.md) | SQLite schema |
| [`kb/04-nesql/export-howto.md`](kb/04-nesql/export-howto.md) | Export + import walkthrough |
| [`kb/04-nesql/wiki-icons.ru.md`](kb/04-nesql/wiki-icons.ru.md) | Item icons in UI |
| [`tools/nesql-import/README.md`](tools/nesql-import/README.md) | Import CLI |
| [`tools/deploy/README.md`](tools/deploy/README.md) | Deploy, backup, volumes |

### Other

| Document | Description |
|----------|-------------|
| [`kb/README.md`](kb/README.md) | How to use the knowledge base |
| [`kb/07-glossary.md`](kb/07-glossary.md) | GTNH/OC terms |
| [`kb/01-architecture/github-first-deploy.md`](kb/01-architecture/github-first-deploy.md) | First push to GitHub (RU) |
| [`oc-client/README.md`](oc-client/README.md) | Lua client quick reference |

`kb/05-vendored/` — git submodules (upstream RemoteOC, nesql-exporter, OpenComputers-GTNH). **Read-only** reference; do not edit.

---

## Publishing to GitHub

First-time setup (install Git, connect empty GitHub repo, push): **[`kb/01-architecture/github-first-deploy.md`](kb/01-architecture/github-first-deploy.md)** (Russian; steps are universal).

Before the first public push:

1. `cp oc-client/env.lua.example oc-client/env.lua` locally — do not commit `env.lua`.
2. `cp .env.example .env` — do not commit `.env` / `server/.env`.
3. `git rm --cached server/.env oc-client/env.lua` if they were ever tracked.
4. **Rotate `SERVER_TOKEN`** if it appeared in git history.
5. Keep private runbooks (IPs, SSH, world paths) out of the repo.
6. Do not commit `data/`, `*.sqlite`, or secrets inside submodules.

---

## License

**MIT** — see [`LICENSE`](LICENSE) (Copyright (c) 2024 z5882852).

Upstream [RemoteOC-GTNH-AE2](https://github.com/z5882852/RemoteOC-GTNH-AE2) is MIT. Third-party submodules under `kb/05-vendored/` have their own licenses (`LICENSE*`, `LICENSE.md` in each tree).
