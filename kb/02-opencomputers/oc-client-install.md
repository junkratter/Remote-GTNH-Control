# OpenComputers client — installation

> **Source:** `gtnh-cyber/oc-client/`  
> **Last updated:** 2026-05-16  

## RU — куда класть файлы

Рабочая папка на диске OC — **один каталог** (например `/home/remote` или путь
на HDD), из которого запускается `run.lua`. Относительно неё нужны пути:

| Относительный путь | Назначение |
|--------------------|------------|
| `run.lua` | Точка входа, таймер опроса `/api/task/get` |
| `env.lua` | `baseUrl`, `clientId`, `serverToken`, `aeAddress`, пути API |
| `lib/*.lua` | JSON, base64, logger |
| `src/executor.lua` | HTTP + загрузка плагинов |
| `plugins/ae.lua` | AE2: сеть, крафт, **programPattern** |
| `plugins/robot_crop.lua` | Робот: кропы + геолайзер снизу (опционально) |
| `plugins/geolyzer_map.lua` | Карта: `geolyzer_map.push({...})` → `/api/map/scan` |
| `plugins/robot_miner.lua` | Робот: заготовка под шахтёр (ping / job) |

**Без git / wget:** скопируйте файлы с ПК на диск OC (Floppy, `/tmp`, вставка в
`edit` по частям). Содержимое — **как в репозитории** `oc-client/` (не копируйте
чужие однострочники из чата).

**`env.lua`:** `baseUrl` — URL бэкенда (порт по умолчанию `1030` в dev,
`8856` снаружи Docker в примере из `docker-compose.yml`). `serverToken` должен
совпадать с `SERVER_TOKEN` сервера. `clientId` — то же, что в веб-UI / реестре
роботов. `aeAddress` — UUID ME controller/interface из анализатора.

**Модули:** AE2 требует `plugins/ae.lua` + настроенный ME. Кропы — робот с
плагином `robot_crop.lua` (апгрейз **Geolyzer** даёт `scanBelow` / `scan`).
Шахтёр — `robot_miner.lua`. **Карта** — `geolyzer_map.lua` и поле `mapScanPath`
в `env.lua`. Команды с сервера: через **Tasks** —
`return robot_crop.harvestBelow()` и т.п.

## EN — layout

Same tree as above: one working directory, `lua run.lua` (or `sh` wrapper).
Copy files verbatim from `oc-client/` in the monorepo.

**wget (when Internet Card works):** from in-game shell, after `mkdir`:

```lua
-- replace BASE with raw URL prefix of your published oc-client/ tree, e.g.:
-- https://raw.githubusercontent.com/<you>/<fork>/main/oc-client/
```

```text
wget -f BASE/run.lua run.lua
wget -f BASE/env.lua env.lua
wget -f BASE/lib/logger.lua lib/logger.lua
wget -f BASE/lib/json.lua lib/json.lua
wget -f BASE/lib/json2.lua lib/json2.lua
wget -f BASE/lib/base64.lua lib/base64.lua
wget -f BASE/src/executor.lua src/executor.lua
wget -f BASE/plugins/ae.lua plugins/ae.lua
wget -f BASE/plugins/robot_crop.lua plugins/robot_crop.lua
wget -f BASE/plugins/robot_miner.lua plugins/robot_miner.lua
wget -f BASE/plugins/robot_power.lua plugins/robot_power.lua
wget -f BASE/plugins/geolyzer_map.lua plugins/geolyzer_map.lua
```

Upstream `setup.lua` in this repo still defaults to an older `client/` URL;
either pass your `BASE` as the first argument to `setup.lua` if you adapt it,
or use the commands above manually.

## See also

- **`kb/02-opencomputers/robots-setup.ru.md`** — пошагово: кроп-робот, сканер (карта), майнер, `env.lua`, веб-UI.  
- `kb/01-architecture/api-contract.md` — `/api/task/*` must stay stable.  
- `kb/01-architecture/decisions/002-robots-phase4.md` — robots module.  
- `kb/01-architecture/decisions/004-map-phase5.md` — карта мира.
