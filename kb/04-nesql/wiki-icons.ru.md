# Иконки предметов в Wiki / квестах / крафтах

> **Last updated:** 2026-05-17

Веб-панель показывает иконки из двух источников:

1. **`website/public/items_GTNH280.json`** — каталог registry id → `img_path`
2. **`website/public/img/items/`** — PNG-файлы (пути из `img_path`)

NESQL даёт **`icon_item_id`** для квестов и слотов рецептов; фронтенд
сопоставляет строку `mod_id` + `unlocal_name` + `damage` с каталогом
(`website/src/utils/items.js`, функции `nesqlToRegistry` / `fromNesqlItem`).

---

## Почему иконка «битая» или имя `gt.metaitem...`

| Причина | Что делать |
|---------|------------|
| Нет PNG в `public/img/items/` | Догрузить текстуры (см. ниже) |
| Нет meta в `items_GTNH280.json` | Обновить JSON из актуального ресурспака GTNH |
| Неверный `unlocal_name` в NESQL | Переимпортировать NESQL; для GT meta см. маппинг в `items.js` |
| Старый кэш браузера | Ctrl+F5 на странице Wiki / Квесты |

GregTech: в NESQL часто `gt.metaitem.01.32601`, в каталоге —
`gregtech:gt.metaitem.01` + damage `32601`. Это обрабатывается в коде;
если meta отсутствует в JSON, показывается `img/default.png`, но
**название** берётся из NESQL `localized_name`.

---

## Как догрузить иконки

### 1. Каталог предметов (`items_GTNH280.json`)

Источник — экспорт/сборка из GTNH (как в оригинальном RemoteOC / вашем пайплайне):

- Положите актуальный **`items_GTNH280.json`** (и опционально `.json.gz`) в
  `website/public/`.
- Версия в `website/src/utils/items.js` → `version: "2.8.0"` должна
  совпадать с суффиксом файла (`items_GTNH280.json`).

### 2. Папка текстур `img/items/`

Скопируйте дерево PNG в `website/public/img/items/`, сохраняя подпути
из `img_path` (например `gregtech/gt.metaitem.01~32601.png`).

Типичный источник — ресурспак / экспорт иконок из клиента GTNH 2.8.x.

Проверка локально:

```bash
ls website/public/img/items/gregtech/gt.metaitem.01~32601.png
```

### 3. Пересборка фронтенда / деплой

Иконки — статика nginx:

```bash
cd website && npm run build
# или на сервере: docker compose up -d --build frontend
```

Убедитесь, что `rsync` не исключает `website/public/img/` (папка большая).

### 4. NESQL (квесты и рецепты)

Иконки квестов берутся из поля **`icon_item_id`** в `nesql_quests`:

```bash
python3 tools/nesql-import/import.py \
  /path/to/nesql-db.script \
  data/backend/nesql.sqlite
```

Скопируйте `nesql.sqlite` на сервер в `data/backend/` (см. `README.ru.md`).

### 5. Русские названия квестов (BQ)

Отдельно от иконок:

```bash
python3 tools/bq-lang-pack/convert.py "/path/to/BQ RU.zip"
# → website/public/bq-ru.json
```

При локали **Русский** в UI подставляются строки из ресурспака BetterQuesting.

---

## Настройки в UI

| Раздел | Назначение |
|--------|------------|
| **Настройки → Карта мира** | Центр карты X/Z (F3), измерение по умолчанию |
| **Настройки → Произвольный источник данных** | Префикс URL, если JSON/картинки на другом хосте |
| **Настройки → Сжимать каталог предметов** | `items_GTNH280.json.gz` вместо `.json` |

---

## См. также

- `kb/04-nesql/export-howto.md` — экспорт NESQL из Minecraft  
- `kb/04-nesql/schema.md` — схема таблиц  
- `README.ru.md` — деплой и порты
