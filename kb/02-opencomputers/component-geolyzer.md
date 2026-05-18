# OpenComputers: компонент `geolyzer`

> **Source:** https://ocdoc.cil.li/component:geolyzer
> **Last updated:** 2026-05-16

## Что это

Geolyzer — апгрейд робота / отдельный блок, который сканирует **жёсткость
блоков** в окрестности и возвращает массив значений. На основе значений
можно эвристически отличить руду от камня (руды и ценные блоки имеют
характерные значения hardness).

В GTNH: API расширен — есть `analyze(side)` (детальный анализ блока)
и `scan(x, z[, ignoreReplaceable])`.

## API

```lua
local geo = component.geolyzer
geo.scan(x, z[, y[, w, d, h[, ignoreReplaceable]]])
-- Возвращает массив hardness-значений зоны w×d×h.
-- По умолчанию (без y/w/d/h): 8×8×64 (≈ от -32 до +32 по Y).

geo.analyze(side[, options])
-- Возвращает таблицу: {name, metadata, hardness, color, harvestable, ...}

geo.detect(side)
-- {hardness, isReplaceable} быстрый чек.

geo.store(side, dbAddress, slot)
-- Сохраняет блок в Database upgrade.
```

`side` — стандартные стороны OpenComputers: `sides.up`, `sides.down`,
`sides.front`, `sides.back`, `sides.left`, `sides.right`.

## Стратегия сканирования (для карты)

```lua
-- Робот идёт по сетке, каждые N блоков сканирует куб 8x8x64
local sides = require("sides")
local geo = component.geolyzer

local function scanRegion(x0, z0)
    local data = geo.scan(x0, z0)  -- 8*8*64 = 4096 значений
    return data
end
```

Результат — длинный flat-массив; индекс `(dx + 4) + (dz + 4)*8 + (dy + 32)*64`.

## Эвристика «это руда?»

Hardness руд GTNH часто выше 3.0 (камень — 1.5–3.0). Самые надёжные
маркеры:

- `hardness > 5.0` — кандидат на руду (диамант ≈ 3, обсидиан ≈ 50,
  GT ores ≈ 3–7 в зависимости от тира).
- Отрицательные значения = блок не идентифицируется (вне дальности).

Точнее: робот подходит вплотную, делает `analyze(sides.front)`, читает
`name` (например, `gregtech:gt.blockores`) и сохраняет в БД.

## Использование в фазе 5 (карта)

1. Робот патрулирует прямоугольник, каждые 8 блоков `scan(0,0)`.
2. Каждый «подозрительный» блок (hardness > порога) → `analyze(side)`.
3. На бэк уходит запись: `{x, y, z, dim, name, hardness, seen_at}`.
4. Бэк делает upsert в таблицу `world_blocks`, фронт показывает Leaflet‑карту.

## Ограничения

- Дальность сканирования по Y ограничена (~32 блока в обе стороны).
- Точность падает с расстоянием.
- Размер ответа: 4096 чисел ≈ 30–60 КБ JSON — chunk не обязателен,
  но `os.sleep(0)` между сканами обязателен.
