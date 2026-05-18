# OpenComputers ↔ Backend: модель опроса

> **Source:** `oc-client/src/executor.lua`, `oc-client/run.lua`.
> **Last updated:** 2026-05-16

## Базовая идея

В OpenComputers Internet Card умеет **только исходящие HTTP**. Поэтому
ни WebSocket, ни push с бэка к OC невозможны. Используется long‑poll:

```
loop:
  taskId, commands, isChunked = GET /api/task/get
  if not taskId then sleep(env.pollingInterval) end
  results = []
  for cmd in commands: results.append(load(cmd, "=remote", "t", _G)())
  if isChunked: POST /api/task/chunked_report?chunked=...
  else:         POST /api/task/report
```

## Тайминги (по умолчанию)

| Параметр                  | Значение | Где            |
|---------------------------|----------|----------------|
| `env.pollingInterval`     | 8 c      | `env.lua`      |
| Таймаут `finishConnect()` | 2 c      | `executor.lua` |
| Таймаут `reportResults`   | 4 c      | `executor.lua` |
| `env.chunkSize`           | 256      | `env.lua`      |

`os.sleep(0)` обязателен каждые 50 итераций цикла, иначе VM ругается
`too long without yielding`.

## Память OC

| Профиль          | Лимит ≈    |
|------------------|------------|
| 2×T3.5 RAM       | ~ 1 000 предметов |
| 4×T3.5 RAM       | ~ 2 000 предметов |
| Creative memory  | без лимита        |

Для `getAllItems` (тяжёлая) — обязательно `chunked: true` в `task_config`.

## Запреты Internet Card

OpenComputers фильтрует адреса через `filteringRules` в `OpenComputers.cfg`.
Подвох: `"allow default"` неявно содержит `deny private` + `deny bogon` —
**127.0.0.0/8, 192.168.x, 10.x, 172.16-31.x будут заблокированы**.

Решение (приоритет правил — сверху вниз):

```hocon
filteringRules=[
  "allow ip:127.0.0.0/8",
  "allow ip:192.168.0.0/16",
  "allow ip:10.0.0.0/8",
  "allow ip:172.16.0.0/12",
  "allow all"
]
```

После правки → перезапуск Minecraft сервера.

## Контракт глобалов на OC

Плагины (`oc-client/plugins/*.lua`) должны регистрироваться в `_G`:

```lua
_G.ae = _G.ae or {}
local ae = _G.ae
function ae.foo() ... end
```

`executor.lua` запускает команды через `load(cmd, "=remote", "t", _G)`,
чтобы `return ae.getAllItems()` видел глобал.

## Push без push: «быстрая реакция»

Если нужно «уведомить браузер» (робот сломался, крафт завершён) — делается так:

1. OC поллит чаще (например, 2 c) → бэк ставит задачу `notify` → OC шлёт `report`.
2. Бэк держит **SSE** к браузеру и сразу пушит событие.

Прямой push OC→бэк невозможен.

## Несколько OC-клиентов

В `env.lua` указывается `clientId = "client_01"`. Бэк фильтрует задачи
по `client_id` в `task_config`. У каждого OC — свой бинд (фарм, шахта, AE),
один и тот же бэк.

## Известные ошибки

| Сообщение в OC                              | Причина                                       |
|---------------------------------------------|------------------------------------------------|
| `address is not allowed`                    | `filteringRules` блокируют (см. выше).         |
| `internet access is unavailable`            | Битый `filteringRules` или нет Internet Card.  |
| `Timeout while fetching commands`           | Бэк не ответил за 2 c.                         |
| `attempt to index global 'ae' (a nil value)`| `executor.lua` не передал `_G` в `load(...)`.  |
| `too long without yielding`                 | Забыли `os.sleep(0)` в горячем цикле.          |
