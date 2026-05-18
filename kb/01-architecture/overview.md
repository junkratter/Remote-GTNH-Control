# RemoteOC-GTNH-AE2 — справочник (выжимка)

> Сводка для повторного использования: официальная документация, настройки **вашего** сервера, GTNH/OpenComputers, типичные ошибки и советы сообщества.  
> Обновлено: 2026-05-15

**Основные ссылки**

| Ресурс | URL |
|--------|-----|
| Репозиторий (赛博监工 / GTNH Cyber Supervisor) | https://github.com/z5882852/RemoteOC-GTNH-AE2 |
| Базовый фреймворк RemoteOC | https://github.com/z5882852/RemoteOC |
| Releases (фронтенд) | https://github.com/z5882852/RemoteOC-GTNH-AE2/releases |
| GTNH Wiki — OpenComputers | https://wiki.gtnewhorizons.com/wiki/Open_Computers |
| OC — компонент Internet | https://ocdoc.cil.li/component:internet |
| OC — Internet Card | https://ocdoc.cil.li/item:internet_card |
| GTNH OpenComputers (форк) | https://github.com/GTNewHorizons/OpenComputers |
| Альтернатива | https://github.com/5418ly/GTNH-OC-AE-Controller |

---

## 1. Что это и как устроено

**RemoteOC-GTNH-AE2** — удалённый мониторинг и управление сетью AE2 в GregTech: New Horizons через компьютер OpenComputers и веб-интерфейс.

Трёхуровневая схема:

```
Браузер (Vue SPA) → Backend (Python, Docker) → OC-клиент в Minecraft (Lua) → ME Controller/Interface
```

**Возможности**

- Просмотр предметов, жидкостей, essentia, CPU, задач крафта
- Удалённый заказ крафта (remote craft)
- Автоматизация (триггеры, таймеры в `config.py`)
- Плагин monitor — Lapotron capacitor / wireless grid (опционально)
- Несколько OC-клиентов (`clientId` в `env.lua`)
- Тёмная тема, мобильная вёрстка

**Требования по README:** хост с доступом извне (для веба); в игре — OC с интернет-картой и адаптером к ME.

---

## 2. Развёртывание (шаблон)

> Приватные IP, пути к миру и учётные данные храните **локально** (не в git).
> См. `tools/deploy/`, `.env.example`, `oc-client/env.lua.example`.

### 2.1. Docker Compose (gtnh-cyber)

```bash
cp .env.example .env   # SERVER_TOKEN=change_me
docker compose up -d --build
```

| Сервис | Порт по умолчанию (хост) |
|--------|---------------------------|
| Backend | `8856` → `1030` |
| Frontend | `8855` → `80` |

Данные SQLite: Docker volume `gtnh_cyber_data` (см. `tools/deploy/backup-data.sh`).

**Проверка API:**

```bash
curl -H "X-Server-Token: <TOKEN>" \
  "http://127.0.0.1:8856/api/task/get" \
  -H "X-Client-ID: client_01"
```

### 2.2. OC-клиент

Скопировать `oc-client/env.lua.example` → `oc-client/env.lua`, задать `baseUrl`, `clientId`, `serverToken`, `aeAddress`.

На том же хосте, что и Minecraft: `baseUrl = "http://127.0.0.1:8856"`.

### 2.3. OpenComputers — filteringRules

Файл: `<minecraft>/config/OpenComputers.cfg`

**Важно:** одно правило `"allow default"` **всё равно блокирует private IP** (внутри него `deny private` + `deny bogon`). Закомментировать явные `deny` недостаточно.

**Рабочая конфигурация (применена):**

```hocon
filteringRules=[
  "allow ip:127.0.0.0/8",
  "allow ip:192.168.0.0/16",
  "allow ip:172.16.0.0/12",
  "allow ip:10.0.0.0/8",
  "allow all"
]
```

После изменения — **перезапуск Minecraft-сервера**. В логе: `Successfully applied 5 Internet Card filtering rules`.

На **2.8.4 :25566** по умолчанию остаются строгие `deny` — для RemoteOC используйте creative или скопируйте правила.

---

## 3. Официальная установка (GitHub README)

Источник: [README RemoteOC-GTNH-AE2](https://github.com/z5882852/RemoteOC-GTNH-AE2)

### 3.1. Docker (рекомендуется)

1. Установить Docker + Docker Compose
2. Скачать `docker-compose.yml` и `server/.env`
3. Настроить `.env` (`SERVER_TOKEN`, при необходимости порты)
4. `docker compose up -d`
5. По умолчанию в upstream: фронт **80**, бэкенд **8080** — у вас переопределено на **8855/8856**

### 3.2. Backend без Docker

```bash
git clone https://github.com/z5882852/RemoteOC-GTNH-AE2.git
cd RemoteOC-GTNH-AE2/server
pip install -r requirements.txt
# правка .env и config.py
python run.py --port 8080
```

### 3.3. OC-клиент в игре

**Железо (минимум):**

| Компонент | Требование |
|-----------|------------|
| CPU | T3 CPU или T3 APU |
| RAM | 2× T3.5 (4× T3.5 при >1000 типов предметов; creative memory при >2000) |
| Карта | Internet Card (Tier 2) |
| Блок | Adapter вплотную к ME Controller или ME Interface |
| Анализатор | Снять UUID ME-блока для `env.lua` |

**Установка файлов:**

```bash
# в OpenOS на компьютере:
wget https://raw.githubusercontent.com/z5882852/RemoteOC-GTNH-AE2/main/client/setup.lua
setup.lua
```

Если GitHub недоступен — скопировать папку `client/` целиком на диск OC (`/home/...`).

**`env.lua` (обязательные поля):**

```lua
local env = {
  pollingInterval = 8,
  baseUrl = "http://<IP_или_домен>:<порт_бэкенда>",  -- без /api/... в конце
  clientId = "client_01",
  serverToken = "<тот же что SERVER_TOKEN в .env>",
  aeAddress = "<UUID ME из анализатора>",  -- не оставлять xxxxxxxx-...
  chunkSize = 256,
  getPath = "/api/task/get",
  reportPath = "/api/task/report",
  chunkedReportPath = "/api/task/chunked_report",
}
return env
```

**Порты:** с хоста Minecraft обращаться к **8856** (маппинг Docker), не к **1030** (внутренний порт контейнера).

**Запуск:**

```bash
run.lua
run.lua --debug   # подробные логи
```

### 3.4. Задачи бэкенда (`server/config.py`)

| task_id | Команда OC | Примечание |
|---------|------------|------------|
| `getCpuDetailList` | `return ae.getCpuList(true)` | |
| `getCpuList` | `return ae.getCpuList()` | |
| `getAllItems` | `return ae.getAllItems()` | `chunked: true`, тяжёлая |
| `getAllSilempleItems` | `return ae.getAllSilempleItems()` | легче для теста |
| `getAllCraftables` | `return ae.getAllCraftables()` | |
| `getAllCraftablesAndCpus` | 2 команды | |

Команды всегда с **точкой**: `ae.getAllItems()`, не `ae-getAllItems()`.

### 3.5. Плагин monitor (опционально)

- Адаптер на Lapotron Capacitor Bank
- В `config.py` → `timer_task_config["monitor"]`
- Включить страницу в настройках веб-UI

---

## 4. GTNH Wiki — OpenComputers + AE (кратко)

Источник: [GTNH Wiki Open Computers](https://wiki.gtnewhorizons.com/wiki/Open_Computers)

**Подключение к машинам:** Adapter рядом с ME Controller **или** MFU + adapter в радиусе 16 блоков.

**Список компонентов в OC:**

```lua
local component = require("component")
for k,v in component.list() do print(k,v) end
```

**ME Controller / ME Interface** — ключевые методы:

- `getItemsInNetwork([filter])` — предметы
- `getFluidsInNetwork()` — жидкости
- `getCpus()` — статус CPU
- `getCraftables([filter])` → `.request(amount, prioritizePower, cpuName)`

**Фильтр таблицей:** `{label="...", size=2}` и т.д.

**ME Interface** дополнительно: конфиг слотов, паттерны через database — для мета-автоматизации.

---

## 5. OpenComputers Internet Card (официальная OC-документация)

Источник: [component:internet](https://ocdoc.cil.li/component:internet)

- Компонент: `internet` (карта Tier 2+)
- HTTP: `request(url, postData?, headers?)` → userdata, далее `finishConnect()`, `read()`, `response()`, `close()`
- TCP: `connect(address, port?)`
- Сигнал при готовности данных: `internet_ready`

**Ошибки GTNH-сервера:**

- `address is not allowed` — сработал `filteringRules` (см. раздел 2.6)
- `internet access is unavailable` — неверные/битые правила в конфиге
- `http requests are unavailable` — `enableHttp=false`

**Правило `"allow default"` (подвох):** внутри применяются встроенные `deny private`, `deny bogon`, `allow all` — **127.0.0.x и 192.168.x.x блокируются**.

---

## 6. Советы сообщества (Reddit / форумы / практика)

> Прямых популярных тредов Reddit именно про RemoteOC-GTNH-AE2 мало; ниже — консолидированные рекомендации из GTNH Wiki, OC-документации, GitHub Issues/Discussions и типичного опыта настройки (в т.ч. вашей сессии).

### 6.1. Сборка OC

1. **Adapter + ME** — ME Controller или ME Interface должен **соприкасаться** с адаптером (не через воздух).
2. **Analyzer** — записать адрес в `env.aeAddress`; placeholder `xxxxxxxx-...` ломает загрузку `ae.lua`.
3. **Internet Card** обязательна; без неё `require("internet")` в RemoteOC не работает.
4. **Память** — при таймаутах/OOM на `getAllItems` сначала проверить `getAllSilempleItems`, затем увеличить RAM.
5. **Tier** — не экономить на CPU/RAM на больших сетях AE.

### 6.2. Сеть и URL

1. **`baseUrl`** — схема `http://`, **без** trailing path; пути заданы в `getPath` / `reportPath`.
2. **localhost с OC** = машина, где крутится **Minecraft server**, не ваш ПК с Docker (если MC на удалённом хосте).
3. **Публичный IP с того же хоста** — часто не работает без NAT hairpin (раздел 2.5); используйте `127.0.0.1` или LAN IP.
4. **Токен** — должен совпадать в `.env` бэкенда и `env.lua` на OC; регистр важен.
5. **Таймаут OC** — в `executor.lua` ожидание `finishConnect()` ~2–4 с; медленный ответ = `Timeout while fetching commands`.

### 6.3. Отладка

```bash
# на OC:
run.lua --debug
# искать:
#   Successfully loaded plugin: ae
#   Unable to connect to the server
#   Timeout while fetching commands
```

**Тест AE вручную на OC:**

```lua
local i = component.internet
local h = {["X-Server-Token"]="TOKEN", ["X-Client-ID"]="client_01"}
local r = i.request("http://127.0.0.1:8856/api/task/get?client_id=client_01", "", h)
while not r.finishConnect() do os.sleep(0) end
print(r.read())
r.close()
```

**Тест плагина ae:**

```lua
print(ae and ae.getAllSilempleItems() or "plugin ae not loaded")
```

### 6.4. Даты в логе `1970-01-03`

У OC нет реального времени без GPS/World Sensor — на логику RemoteOC не влияет.

### 6.5. Альтернативы

- [GTNH-OC-AE-Controller](https://github.com/5418ly/GTNH-OC-AE-Controller) — другой стек (Flask/Java), похожая идея.
- [z5882852/GTNH-OC-AE-Controller](https://github.com/z5882852/GTNH-OC-AE-Controller) — вариант от того же автора.

### 6.6. Reddit / FTF (общие темы, применимые к GTNH+AE)

- Удалённый мониторинг AE исторически обсуждали через ComputerCraft/OpenPeripheral; для GTNH актуален именно **OpenComputers + adapter**.
- r/feedthebeast, r/GTNH: ищите `"OpenComputers"`, `"internet card"`, `"AE2 automation"` — чаще про Lua-скрипты и `filteringRules`, чем про RemoteOC по имени.
- [FTB — Tracking AE2 inventory](https://forum.feed-the-beast.com/threads/tracking-ae2-inventory-with-computercraft.163836/) — концептуально схожая задача (внешний скрипт ↔ сеть хранения).

---

## 7. Частые ошибки (чеклист)

| Симптом | Причина | Решение |
|---------|---------|---------|
| Таймаут на публичном IP с самого сервера | NAT hairpin | В `/etc/ufw/before.rules` — OUTPUT DNAT `YOUR_PUBLIC_IP:{80,443,8855,8856}` → `127.0.0.1`; `sysctl route_localnet=1`; либо `curl` на `127.0.0.1:18855` / `18856` |
| `address is not allowed` | `filteringRules` | Явные `allow ip:...` (раздел 2.6), рестарт MC |
| `ae` is nil / index nil | Плагин не в `_G` или `load()` без `_G` | Обновить `executor.lua` (`load(..., _G)`), `ae.lua`, `run.lua --debug` |
| `ae-getAllItems` / arithmetic | Опечатка: дефис вместо точки | Команда: `return ae.getAllItems()` |
| HTTP 422 на API | Нет заголовка `x-server-token` | Добавить токен |
| HTTP 403 | Неверный токен | Сверить `.env` и `env.lua` |
| Chunked OK, но пустые данные | Ошибка в команде ушла как JSON-ошибка | Смотреть DEBUG-лог OC |
| OOM / зависание на getAllItems | Мало RAM на OC | 4× T3.5 / creative memory |
| Порт 1030 в URL | Путаница Docker | Снаружи контейнера использовать **8856** |

---

## 8. Полезные команды (шпаргалка)

```bash
# --- Docker RemoteOC ---
cd /opt/gtnh-cyber && docker compose ps
docker compose restart && docker compose logs -f roc-gtnh-backend

# --- Minecraft creative ---
sudo -u minecraft screen -ls
sudo -u minecraft screen -r gtnh_creative

# --- Проверка портов ---
ss -tlnp | grep -E '8856|8855|25565'

# --- API ---
curl -sS -H "x-server-token: $TOKEN" \
  "http://127.0.0.1:8856/api/task/get?client_id=client_01"

# --- NAT hairpin тест (с хоста на свой WAN / домены) ---
curl -sS -m 5 -o /dev/null -w "%{http_code}\n" https://gtnh.example.com/
curl -sS -m 5 https://api.gtnh.example.com/api/info/version
```

```lua
-- --- На OC-компьютере ---
component.list()                    -- что видит компьютер
require("env").aeAddress          -- текущий адрес ME
run.lua --debug
```

---

## 9. Структура репозитория (для навигации)

```
RemoteOC-GTNH-AE2/
├── client/           # Lua: env.lua, run.lua, plugins/ae.lua, src/executor.lua
├── server/           # Python: config.py, .env, run.py
├── website/          # Vue SPA
├── docker-compose.yml
└── README.md
```

**Версия upstream (releases):** v2.2.0 (Nov 2025) — см. GitHub Releases для совместимости с GTNH 2.8.x.

---

## 10. История правок на вашем сервере (сессия 2026-05-15)

1. SSH-ключ для `admin1` — доступ к хосту
2. Диагностика: путь `versions/2.8.4_creative`, порт 25565
3. OpenComputers `filteringRules` — замена `"allow default"` на явные allow
4. NAT hairpin для публичных портов фронта/бэка (если нужен curl с хоста на свой WAN IP)
5. Патч `client/plugins/ae.lua` — ленивая инициализация ME, понятные ошибки
6. Перезапуск `docker compose` стека RemoteOC

---

*Файл можно копировать в wiki/репозиторий проекта. При смене токена или IP обновите разделы 2.2, 2.5 и `env.lua`.*
