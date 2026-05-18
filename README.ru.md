# remote-gtnh-control

**Remote GTNH Control** — удалённый мониторинг и управление **Applied Energistics 2** в **GregTech: New Horizons** через **OpenComputers** и веб-интерфейс.

[English](README.md) · **Русский**

**Репозиторий:** [https://github.com/junkratter/Remote-GTNH-Control](https://github.com/junkratter/Remote-GTNH-Control).  
Нужен хост, доступный из сети, где крутится Minecraft (LAN или интернет), и один или несколько компьютеров OC в игре.

---

## Архитектура

```text
Браузер (Vue 3 SPA) ──HTTP──▶ FastAPI-монолит ◀── long-poll ── OpenComputers (Lua)
                                      │
                                      ├── SQLite (задачи, роботы, карта, автокрафт, …)
                                      └── nesql.sqlite (Wiki / квесты / рецепты)
```

OpenComputers умеет только **исходящий** HTTP → бэкенд — **единый монолит** с общей очередью задач. Push с сервера в OC невозможен.

---

## Возможности

### Из upstream RemoteOC

| Модуль | Описание |
|--------|----------|
| **Сеть AE2** | Предметы, жидкости, essentia; список и статус CPU |
| **Удалённый крафт** | Заказ крафта из веба (`ae.requestItem`) |
| **Автоматизация** | Триггеры и таймеры (`/api/automate/*`, задачи в `config.py`) |
| **Несколько клиентов** | Разные `clientId` на одном бэкенде |
| **Интерфейс** | Тёмная тема, мобильная вёрстка, настройки URL и токена |

### Добавлено в remote-gtnh-control

| Модуль | Описание |
|--------|----------|
| **Автокрафт** | Программирование слотов ME Interface, очередь крафтов, синхронизация после отчёта OC — [`/api/autocraft/*`](server/app/modules/autocraft/), страница **Autocraft** |
| **Роботы** | Реестр (`/api/robots/*`), задания майнера с постановкой в очередь OC, установка генераторов — плагины `robot_crop`, `robot_miner`, `robot_power` |
| **Карта мира** | `POST /api/map/scan`, Leaflet — плагин `geolyzer_map` |
| **Квесты** | Доска Better Questing из NESQL — `/api/quests/*` |
| **Wiki** | Просмотр предметов и рецептов — `/api/nesql/*` |
| **i18n** | Интерфейс: **en / ru / zh** (vue-i18n + Element Plus) |
| **Хранение данных** | Docker volume `remote_gtnh_control_data`; скрипты бэкапа и деплоя |
| **Тесты** | pytest + контрактные тесты `/api/task/*` |

---

## Структура репозитория

```text
remote-gtnh-control/
├── server/              FastAPI, SQLAlchemy 2, Alembic, SQLite
├── website/             Vue 3, Element Plus, Vite, vue-i18n
├── oc-client/           Lua-клиент и плагины (см. oc-client/README.md)
├── tools/
│   ├── kb-fetch/        Обновление выжимок в kb/
│   ├── nesql-import/    HSQLDB (экспорт из игры) → nesql.sqlite
│   └── deploy/          Docker, бэкап, регистрация роботов
├── kb/                  База знаний, ADR, гайды OC/GTNH
├── docker-compose.yml
├── Makefile
└── AGENTS.md            Правила для разработчиков
```

---

## Требования

| Компонент | Версия |
|-----------|--------|
| Бэкенд | Python **3.11** (`server/Dockerfile`) |
| Фронтенд | Node **18+**, npm |
| Docker (опционально) | Docker Compose v2 |
| OC-клиент (в игре) | OpenComputers **1.11.x** (GTNH), Internet Card, адаптер к ME |
| NESQL (опционально) | JDK для `tools/nesql-import`, мод [nesql-exporter](https://github.com/GTNewHorizons/nesql-exporter) на **клиенте** |

---

## Быстрый старт (Docker)

```bash
git clone https://github.com/junkratter/Remote-GTNH-Control.git remote-gtnh-control
cd remote-gtnh-control
git submodule update --init --recursive   # опционально: kb/05-vendored

cp .env.example .env
# Задайте SERVER_TOKEN (один секрет везде ниже)

docker compose up -d --build
```

| Сервис | Порт на хосте (по умолчанию) | В контейнере |
|--------|------------------------------|--------------|
| Веб-UI | **8855** | nginx :80 (прокси `/api/` → бэкенд) |
| API | **8856** | uvicorn :1030 |

- UI: `http://<хост>:8855`
- Документация API: `http://<хост>:8856/docs`

Порты в `.env`: `FRONTEND_PORT_HOST`, `BACKEND_PORT_HOST`.

**Данные:** SQLite в Docker volume **`remote_gtnh_control_data`** (переживает пересборку образов). Зеркало на хост для бэкапа:

```bash
chmod +x tools/deploy/*.sh
./tools/deploy/backup-data.sh    # → ./data/backend/
```

Подробнее: [`tools/deploy/README.md`](tools/deploy/README.md).

---

## Конфигурация

### Бэкенд (`.env`)

Скопируйте [`.env.example`](.env.example) → `.env`:

| Переменная | Назначение |
|------------|------------|
| `SERVER_TOKEN` | Общий секрет; заголовок `X-Server-Token` |
| `LOG_LEVEL` | например `INFO` |
| `BACKEND_PORT_HOST` / `FRONTEND_PORT_HOST` | Проброс портов (опционально) |

Не коммитьте `.env` и `server/.env`.

### Веб-интерфейс (браузер)

**Настройки** в SPA:

| Поле | Типичное значение |
|------|-------------------|
| URL бэкенда | **Пусто**, если UI и API на одном хосте (`:8855`, встроенный прокси); иначе `http://<хост>:8856` |
| Серверный токен | Тот же `SERVER_TOKEN` |

### OpenComputers (`oc-client/env.lua`)

```bash
cp oc-client/env.lua.example oc-client/env.lua
```

| Поле | Назначение |
|------|------------|
| `baseUrl` | Корень API, напр. `http://127.0.0.1:8856` на хосте MC |
| `clientId` | ID клиента OC (для AE — `client_01`) |
| `serverToken` | Как `SERVER_TOKEN` |
| `aeAddress` | UUID ME controller/interface (только AE) |

Не коммитьте `oc-client/env.lua`.

**Железо OC (AE):** CPU T3/APU, достаточно RAM под число типов предметов (см. upstream README), Internet Card, адаптер у ME.

**Фильтрация HTTP:** в GTNH по умолчанию блокируются private IP — разрешите подсеть бэкенда в `OpenComputers.cfg`. См. [`kb/02-opencomputers/filtering-rules.md`](kb/02-opencomputers/filtering-rules.md).

---

## Локальная разработка

```bash
make install
cp .env.example .env

make backend      # API :1030
make frontend     # Vite (см. website/package.json)
```

```bash
make test         # pytest + контракт
make openapi      # типы TS после изменений API
make kb-update    # обновить выжимки kb/
```

---

## Клиент OpenComputers

Исходники Lua-клиента — каталог **`oc-client/`** в репозитории  
[github.com/junkratter/Remote-GTNH-Control](https://github.com/junkratter/Remote-GTNH-Control): скопируйте дерево на диск компьютера OC или подтягивайте файлы через `wget` с **raw**-URL ветки `main` (см. ниже и `oc-client-install.md`).

**Базовый префикс для `wget` в OpenOS:**

```text
https://raw.githubusercontent.com/junkratter/Remote-GTNH-Control/main/oc-client/
```

### Установка

| Способ | Документ |
|--------|----------|
| Копирование `oc-client/` на диск OC | [`kb/02-opencomputers/oc-client-install.md`](kb/02-opencomputers/oc-client-install.md) |
| Кроп / майнер / энергия | [`kb/02-opencomputers/robots-setup.ru.md`](kb/02-opencomputers/robots-setup.ru.md) |
| Генераторы GT | [`kb/03-gtnh/gt-power-deploy.md`](kb/03-gtnh/gt-power-deploy.md) |

### Запуск

```text
cd /home/<папка-oc>
lua run.lua
lua run.lua --debug
```

Плагины в `plugins/*.lua` подгружаются автоматически.

### Регистрация роботов

**Роботы** → **Реестр**: `client_id`, роль (`ae`, `crop`, `miner`, `power`, …), метка.  
Или из JSON:

```bash
cp tools/deploy/robots.seed.example.json tools/deploy/robots.seed.json
# отредактировать, затем:
export SERVER_TOKEN=...
./tools/deploy/bootstrap-robots.sh
```

### Контракт `/api/task/*`

Не менять форматы `/api/task/get`, `/api/task/report`, `/api/task/chunked_report` и обёртку `{ code, message, data }` без:

1. `oc-client/src/executor.lua`
2. [`kb/01-architecture/api-contract.md`](kb/01-architecture/api-contract.md)
3. [`server/tests/contract/test_task_contract.py`](server/tests/contract/test_task_contract.py)

---

## Веб-приложение (страницы)

| Раздел | Назначение |
|--------|------------|
| **Предметы** | Склад AE, диалог крафта |
| **CPU** | Статус crafting CPU |
| **Задачи** | Именованные задачи (`getAllItems`, …) |
| **Автоматизация** | Триггеры и таймеры |
| **Автокрафт** | Паттерны ME + очередь |
| **Роботы** | Реестр, задания майнера и генераторов |
| **Карта** | Скан geolyzer |
| **Квесты** | Дерево / доска из NESQL |
| **Wiki** | Предметы и рецепты |
| **Настройки** | URL, токен, начало карты, язык |

Именованные AE-задачи по умолчанию используют `client_id: client_01` в [`server/app/automation/config.py`](server/app/automation/config.py) — измените под свой `env.lua`.

---

## NESQL (Wiki, квесты, автокрафт)

### 1. Экспорт в Minecraft (клиент)

Официальный мод: **[GTNewHorizons/nesql-exporter](https://github.com/GTNewHorizons/nesql-exporter)**.

- Соберите **`NESQL-Exporter-<версия>.jar`** + **`-deps.jar`** (`./gradlew build` → `build/libs/`, версия в `gradle.properties`, напр. **0.5.2**).
- В **`mods/`** инстанса — **только эта пара** (клиент, не серверный `mods/`).
- В мире: **`/nesql`**.
- Результат: `.minecraft/nesql/` (дамп HSQLDB).

Подробно: [`kb/04-nesql/export-howto.md`](kb/04-nesql/export-howto.md).

### 2. Импорт в бэкенд

```bash
cd tools/nesql-import
pip install -r requirements.txt

python import.py \
  --src /путь/к/nesql-db \
  --dst /путь/к/data/backend/nesql.sqlite \
  --hsqldb-jar ./vendor/hsqldb-2.7.4.jar
```

После импорта в Docker: [`tools/deploy/restore-data-volume.sh`](tools/deploy/restore-data-volume.sh) и `docker compose restart backend`.

Без импорта Wiki, квесты и подбор рецептов пустые.

**Иконки:** `website/public/items_GTNH280.json` + `website/public/img/items/` — [`kb/04-nesql/wiki-icons.ru.md`](kb/04-nesql/wiki-icons.ru.md).

---

## Оглавление документации

### Архитектура и API

| Файл | Описание |
|------|----------|
| [`AGENTS.md`](AGENTS.md) | Стек, границы, правила для разработчиков |
| [`kb/01-architecture/overview.md`](kb/01-architecture/overview.md) | Шаблон деплоя, troubleshooting |
| [`kb/01-architecture/api-contract.md`](kb/01-architecture/api-contract.md) | Контракт `/api/task/*` |
| [`kb/01-architecture/oc-polling.md`](kb/01-architecture/oc-polling.md) | Long-poll |
| [`kb/01-architecture/implementation-status.md`](kb/01-architecture/implementation-status.md) | Чеклист фич |
| [`kb/01-architecture/decisions/`](kb/01-architecture/decisions/) | ADR |

### OpenComputers и GTNH

| Файл | Описание |
|------|----------|
| [`kb/02-opencomputers/oc-client-install.md`](kb/02-opencomputers/oc-client-install.md) | Установка OC-клиента |
| [`kb/02-opencomputers/robots-setup.ru.md`](kb/02-opencomputers/robots-setup.ru.md) | Настройка роботов |
| [`kb/02-opencomputers/filtering-rules.md`](kb/02-opencomputers/filtering-rules.md) | `OpenComputers.cfg` |
| [`kb/02-opencomputers/component-me.md`](kb/02-opencomputers/component-me.md) | ME / AE2 |
| [`kb/02-opencomputers/component-internet.md`](kb/02-opencomputers/component-internet.md) | Internet Card |
| [`kb/03-gtnh/ae2-patterns.md`](kb/03-gtnh/ae2-patterns.md) | Паттерны AE2 |
| [`kb/03-gtnh/gt-miner.md`](kb/03-gtnh/gt-miner.md) | Майнеры GT |
| [`kb/03-gtnh/ic2-crops.md`](kb/03-gtnh/ic2-crops.md) | Кропы IC2 |
| [`kb/03-gtnh/gt-power-deploy.md`](kb/03-gtnh/gt-power-deploy.md) | Роботы-генераторы |

### NESQL и утилиты

| Файл | Описание |
|------|----------|
| [`kb/04-nesql/schema.md`](kb/04-nesql/schema.md) | Схема SQLite |
| [`kb/04-nesql/export-howto.md`](kb/04-nesql/export-howto.md) | Экспорт и импорт |
| [`kb/04-nesql/wiki-icons.ru.md`](kb/04-nesql/wiki-icons.ru.md) | Иконки в UI |
| [`tools/nesql-import/README.md`](tools/nesql-import/README.md) | CLI импорта |
| [`tools/deploy/README.md`](tools/deploy/README.md) | Деплой и бэкапы |

### Прочее

| Файл | Описание |
|------|----------|
| [`kb/README.md`](kb/README.md) | Как пользоваться kb/ |
| [`kb/07-glossary.md`](kb/07-glossary.md) | Термины GTNH/OC |
| [`oc-client/README.md`](oc-client/README.md) | Кратко про Lua-клиент |

`kb/05-vendored/` — git submodules (upstream). **Только чтение**, не редактировать.

## Заметка по секретам

1. Локально: `cp oc-client/env.lua.example oc-client/env.lua` — не коммитить `env.lua`.
2. `cp .env.example .env` — не коммитить `.env` / `server/.env`.
3. Не коммитить `data/`, `*.sqlite`, токены и приватные runbook'и (IP, SSH, пути к миру).

---

## Лицензия

**MIT** — см. [`LICENSE`](LICENSE). Происхождение от ветки RemoteOC-GTNH-AE2 / RemoteOC (MIT). Субмодули в `kb/05-vendored/` — свои лицензии в соответствующих каталогах.
