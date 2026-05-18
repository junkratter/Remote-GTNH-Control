# GTNH: Thaumcraft Aspects (для NESQL)

> **Source:** https://wiki.gtnewhorizons.com/wiki/Thaumcraft, NESQL exporter schema
> **Last updated:** 2026-05-16

## Что нужно знать

Thaumcraft хранит у каждого предмета список «аспектов» (Aer, Aqua, Ignis,
Terra, Ordo, Perditio + производные). Это маленькая таблица
`(item_id, aspect, amount)`, экспортируемая NESQL.

В GTNH аспектов ~200 (включая модовые: Metallum, Machina, Praecantatio
и т.д.).

## Зачем нам

- В UI поверх NESQL — окно «что в этом предмете по аспектам» (полезно
  для Thaumcraft исследований и нодов).
- Возможный «крафт-планнер» через Thaumic Tinkerer / Botania (Фаза 3+).
- Поиск предметов по требованиям квестов BetterQuesting (Фаза 6).

## Таблица в NESQL

После запуска `/nesql start` HSQLDB содержит, в т.ч.:

```
ITEM_ASPECT(
  ITEM_ID INT,            -- FK на ITEM
  ASPECT_NAME VARCHAR,    -- "Aer", "Metallum", ...
  AMOUNT INT
)
```

Запросы:

```sql
-- Все аспекты предмета "Iron Ingot":
SELECT a.ASPECT_NAME, a.AMOUNT
FROM ITEM i
JOIN ITEM_ASPECT a ON i.ID = a.ITEM_ID
WHERE i.UNLOCAL_NAME = 'item.IngotIron';

-- Все предметы с >= 4 Metallum:
SELECT i.UNLOCAL_NAME, a.AMOUNT
FROM ITEM_ASPECT a JOIN ITEM i ON i.ID = a.ITEM_ID
WHERE a.ASPECT_NAME = 'Metallum' AND a.AMOUNT >= 4
ORDER BY a.AMOUNT DESC;
```

## Импорт в нашу SQLite

В Фазе 2 (`tools/nesql-import/`) маппим в три таблицы:

```sql
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    unlocal_name TEXT,
    display_name TEXT,
    mod_id TEXT,
    damage INTEGER
);
CREATE TABLE aspects (
    name TEXT PRIMARY KEY,
    base_components TEXT  -- JSON: производные раскладываются на базовые
);
CREATE TABLE item_aspects (
    item_id INTEGER REFERENCES items(id),
    aspect_name TEXT REFERENCES aspects(name),
    amount INTEGER,
    PRIMARY KEY (item_id, aspect_name)
);
CREATE INDEX idx_item_aspects_aspect ON item_aspects(aspect_name);
```

## Тонкости

- В NESQL встречаются «синтетические» предметы (флюиды как item), их
  надо фильтровать в UI.
- У одного `unlocal_name` бывает несколько `damage` (метаданных) — это
  разные предметы (например, GT meta items).
- Объём после импорта ≈ 50–100 МБ; на SQLite живёт без проблем.
