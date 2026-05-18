# `website/src/api/`

Типизированный клиент к бэкенду GTNH Cyber.

## Файлы

- `openapi.json` — генерируется из бэкенда (`backend → /openapi.json`).
- `generated/schema.d.ts` — TS-типы, выводятся из `openapi.json` через
  `openapi-typescript`.
- `index.ts` — обёртки на `openapi-fetch` с авто-инжектом `X-Server-Token`.

## Обновление

```bash
# Вариант 1: бэкенд работает в Docker / dev
npm run openapi:fetch -- http://127.0.0.1:8856
npm run openapi:generate

# Вариант 2: бэкенд не запущен, дампим из исходников
cd ../server && . .venv/bin/activate && python scripts/dump_openapi.py
cd ../website && npm run openapi:generate
```

## Использование

```ts
import { api, robotsApi } from "@/api"

// Низкоуровневый, типы выводятся из схемы:
const resp = await api.GET("/api/info/version")
if (resp.data?.code === 200) console.log(resp.data.data)

// Высокоуровневые шорткаты (см. index.ts):
const robots = await robotsApi.list()
```

## Запреты

- Не редактировать `generated/schema.d.ts` вручную — перетрётся.
- Не дёргать `axios` напрямую в новых страницах — пользоваться этим клиентом.
