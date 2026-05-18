# Статус внедрения (форк gtnh-cyber)

Краткий чеклист по дорожной карте фронтенда и связанным задачам.

## Фазы плана (RemoteOC + workflow)

- [x] **Фаза 3 — Автокрафт AE2** — API `/api/autocraft/*` (паттерны, очередь, отмена, CPU scan), синхронизация `AutocraftRequest` по `/api/task/report`, OC `ae.programPattern` / `requestItem`, страница **Autocraft** (Patterns + Queue, NESQL). Тесты: `tests/integration/test_robots_and_autocraft.py`.
- [x] **Фаза 5 — Карта** — таблица `world_blocks`, POST `/api/map/scan`, GET `/api/map/blocks`, плагин `oc-client/plugins/geolyzer_map.lua`, страница **Map** (Leaflet). Тесты: `tests/integration/test_worldmap.py`.
- [x] **Фаза 6 — Квесты** — `/api/quests/tree`, `/api/quests/search`, страница **Quests** (дерево + поиск). Тесты: `tests/integration/test_nesql.py` (`test_api_quests_*`).

## Локализация (vue-i18n + Element Plus)

- [x] **Element Plus** — локаль не фиксируется в `main.js`; корень обёрнут в `ElConfigProvider`, `elementLocale` синхронизирован с `vue-i18n` (en / ru / zh-cn).
- [x] **`website/src/utils/task.js`** — сообщения об ошибках и уведомления через `i18n.global.t('errors.*')`, без захардкоженного китайского.
- [x] **`website/src/utils/automate.js`** — то же, ключи `errors.automate.*`.
- [x] **`website/src/pages/Automate.vue`** — все `ElMessage` / предупреждение о незаданном backend через `$t('automateUi.*')` и `info.backend_not_configured`.

### Дальше по плану (i18n / UX)

- [ ] **Шаблон и таблица Automate** — подписи колонок, кнопки, диалоги и сравнения с именами триггеров (`CPU空闲时`, `触发器` и т.д.) остаются на китайском в разметке; при необходимости вынести в i18n и/или опираться на стабильные `id` с бэкенда.
- [ ] **Страницы с сырым текстом ошибки** — `Autocraft.vue`, `Robots.vue`, `Wiki.vue` используют `ElMessage.error(String(err))`; при желании обернуть в общий ключ вида «Ошибка: {msg}» для единообразия.
- [ ] **Ручная проверка** — переключение ru/en/zh: Tasks, Automate, крафт из предметов; датапикеры и пустые состояния Element Plus.

## Прочее (из сессий)

ADR и детали OC — см. `kb/01-architecture/decisions/` и `README.md` репозитория.
