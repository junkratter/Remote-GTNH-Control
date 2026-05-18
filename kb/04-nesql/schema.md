# NESQL Exporter: схема БД

> **Source:** https://github.com/GTNewHorizons/nesql-exporter  
> **Last updated:** 2026-05-17

## Где живёт

После **`/nesql`** в Minecraft (клиент с установленным экспортёром) данные пишутся в каталог под `.minecraft/nesql/` (или подкаталог, если указано имя репозитория в команде). Префикс файлов БД в коде — **`nesql-db`**:

```
<minecraft>/nesql/
├── nesql-db.script    -- HSQLDB DDL+данные (для --source-sql)
├── nesql-db.properties
├── nesql-db.log
├── nesql-db.data
└── nesql-db.lobs      -- BLOBы (иконки, NBT)
```

Объём ~600 МБ для полного GTNH.

## Основные таблицы

### `ITEM`

```sql
ITEM(
  ID            INTEGER PRIMARY KEY,
  UNLOCAL_NAME  VARCHAR,   -- 'item.IngotIron', 'tile.gt.blockmachines'
  LOCALIZED_NAME VARCHAR,  -- 'Iron Ingot'
  MOD_ID        VARCHAR,
  ITEM_DAMAGE   INTEGER,
  STACK_SIZE    INTEGER,
  MAX_DAMAGE    INTEGER,
  NBT_HASH      VARCHAR    -- хэш для уникализации
)
```

### `FLUID`

```sql
FLUID(ID, INTERNAL_NAME, LOCALIZED_NAME, MOD_ID, COLOR, TEMPERATURE, ...)
```

### `RECIPE` / `RECIPE_INPUT` / `RECIPE_OUTPUT`

```sql
RECIPE(
  ID INTEGER PRIMARY KEY,
  RECIPE_TYPE VARCHAR,   -- 'minecraft.crafting', 'gregtech.electrolyzer', ...
  EU_PER_TICK INTEGER,
  DURATION INTEGER,      -- ticks
  ...
)

RECIPE_INPUT(RECIPE_ID, SLOT, ITEM_ID|FLUID_ID, AMOUNT)
RECIPE_OUTPUT(RECIPE_ID, SLOT, ITEM_ID|FLUID_ID, AMOUNT, CHANCE)
```

### `ORE_DICTIONARY`

```sql
ORE_DICTIONARY(ID, NAME)
ORE_DICTIONARY_ITEM(ORE_ID, ITEM_ID)
```

### Quests (BetterQuesting)

```sql
QUEST(
  ID INTEGER PRIMARY KEY,
  NAME VARCHAR,
  DESCRIPTION TEXT,
  QUEST_LINE INTEGER,
  PARENT_ID  INTEGER,
  TASK_JSON  TEXT,        -- сырое описание задач
  REWARD_JSON TEXT
)
```

### Aspects (Thaumcraft)

```sql
ITEM_ASPECT(ITEM_ID, ASPECT_NAME, AMOUNT)
ASPECT(NAME, COMPONENTS)   -- 'Metallum=Terra+Vitreus' и т.п.
```

## Импорт в SQLite

HSQLDB → SQLite через `jaydebeapi` (Python + JDBC) или `hsqldb-cli`:

```bash
# Вариант 1: SqlTool из HSQLDB
java -jar hsqldb-sqltool.jar --rcFile nesql.rc --sql "SCRIPT 'export.sql';" sa
# затем доадаптировать DDL под SQLite

# Вариант 2: Python + jaydebeapi (что используем)
# --src: путь к префиксу БД без расширения (каталог с nesql-db.*)
python tools/nesql-import/import.py --src ~/minecraft/nesql/nesql-db --dst data/nesql.sqlite
```

## Подмножество для бэка

В `server/app/db/models.py` (модуль `nesql/`) переносим минимум:

| Наша таблица    | NESQL источник                        |
|-----------------|----------------------------------------|
| `nesql_items`   | `ITEM`                                 |
| `nesql_fluids`  | `FLUID`                                |
| `nesql_recipes` | `RECIPE` + INPUT/OUTPUT (JSON в одну колонку) |
| `nesql_oredict` | `ORE_DICTIONARY` + ORE_DICTIONARY_ITEM |
| `nesql_quests`  | `QUEST`                                |
| `nesql_item_aspects` | `ITEM_ASPECT`                     |

Индексы на `localized_name` (LIKE-поиск) и `mod_id`.

## Иконки

NESQL также экспортирует PNG иконки предметов в подкаталог. Для UI:

- Сложить иконки в `website/public/icons/` (Build step).
- Имя файла = `{mod_id}_{unlocal_name}_{damage}.png` (наша конвенция).
