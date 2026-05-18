# API контракт `/api/task/*`

> **Source:** `server/app/api/task.py` (текущая реализация).
> **Last updated:** 2026-05-16
>
> **КРИТИЧНО:** Этот контракт опрашивает Lua‑клиент в OpenComputers
> через long‑poll. **Не менять** без миграции в `oc-client/src/executor.lua`.

## Аутентификация

Заголовок `X-Server-Token: <SERVER_TOKEN>` обязателен для всех роутов
(сравнивается с `.env`). Отсутствие → HTTP 422; неверный → HTTP 403.

OC‑клиент дополнительно шлёт `X-Client-ID: <env.clientId>` (например, `client_01`).

## Эндпоинты

### GET `/api/task/get`

Возвращает первую `READY`-задачу для клиента.

```http
GET /api/task/get HTTP/1.1
X-Server-Token: <token>
X-Client-ID: client_01
```

Ответ при наличии задачи:

```json
{
  "code": 200,
  "message": "Commands for task fetched successfully",
  "data": {
    "taskId": "getAllItems",
    "commands": ["return ae.getAllItems()"],
    "is_chunked": true
  }
}
```

Если задач нет — `"data": null`, `"message": "No ready commands available"`.

После выдачи статус задачи переводится в `PENDING`.

### POST `/api/task/report`

Принимает результаты обычной (нечанковой) задачи.

```json
{
  "task_id": "abc-123",
  "results": ["{\"message\":\"success\",\"data\":...}"]
}
```

> Тело может прийти в **GBK** (особенность Lua/OC); backend пытается
> сначала UTF‑8, затем GBK.

После приёма статус → `COMPLETED`, вызывается `handle` и `callback` из `task_config`.

### POST `/api/task/chunked_report?chunked=N`

Чанковый аплоад для тяжёлых задач (`getAllItems`).

| `chunked` | Семантика                                  |
|-----------|---------------------------------------------|
| `1`       | Начало: сбросить буфер, статус `UPLOADING`. |
| `>1`      | Догрузить очередной чанк.                   |
| `0`       | Финал: дописать и перевести в `COMPLETED`.  |

Тело — то же, что и в `/report`, но `results` — list-of-lists для чанков.

### GET `/api/task/status?task_id=...&remove=true&use_gzip=false`

Состояние задачи по `task_id`. При `use_gzip=true` поле `result` — base64
от gzip‑архива JSON.

### POST `/api/task/add`

Создать произвольную задачу (произвольные команды).

```json
{ "task_id": "optional-id", "client_id": "client_01", "commands": ["return 1+1"] }
```

### POST `/api/task/task`

Запустить задачу по имени из `task_config` (например, `getAllItems`).

### GET `/api/task/history?task_id=...&start_time&end_time&use_gzip`

История выполнения задачи (только если в конфиге `save_history=true`).

## Статусы

| Статус       | Где выставляется                                    |
|--------------|------------------------------------------------------|
| `ready`      | `add_task`, `add_task_by_name`, `update_task`.       |
| `pending`    | После `GET /api/task/get` — выдано OC.               |
| `uploading`  | Активный приём чанков.                               |
| `completed`  | Финальные `report` / `chunked_report` с `chunked=0`. |

## Что нельзя ломать

- Имена полей в JSON ответа (`code`, `message`, `data`, `taskId`, `commands`, `is_chunked`).
- HTTP‑коды успеха = `200` (даже при ошибках бизнес‑логики — код 200 + `code: 4xx` в теле).
- Поведение `cache: true` в `task_config` — повторное добавление с тем же `task_id`
  обновляет статус, а не создаёт дубликат.
- Заголовки `X-Server-Token`, `X-Client-ID`.

## Расширение

Новые модули (`/api/robots/*`, `/api/autocraft/*`, `/api/map/*`, `/api/quests/*`,
`/api/nesql/*`) добавляются **рядом**, без правки `/api/task/*`.
