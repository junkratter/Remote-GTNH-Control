# OpenComputers: компонент `robot`

> **Source:** https://ocdoc.cil.li/component:robot
> **Last updated:** 2026-05-16

## Что это

Управление мобильным роботом OpenComputers. Доступен как
`require("robot")` (high-level, удобный) и `component.robot` (low-level).

```lua
local robot = require("robot")
```

## Движение

| Метод                | Действие                                             |
|----------------------|-------------------------------------------------------|
| `robot.forward()`    | Шаг вперёд (двигатель тратит энергию).               |
| `robot.back()`       | Шаг назад.                                            |
| `robot.up()` / `down()` | Шаг вверх/вниз.                                    |
| `robot.turnLeft()` / `turnRight()` | Поворот на 90°.                          |
| `robot.turnAround()` | Поворот на 180°.                                      |

Возвращают `true` или `false, reason` (`"impossible move"`, `"not enough energy"`).

## Манипуляции с блоками

| Метод                          | Где              |
|--------------------------------|------------------|
| `robot.swing([side])`          | Сломать блок.    |
| `robot.use([side])`            | Правый клик.     |
| `robot.place([side, sneaky])`  | Поставить блок из выбранного слота. |
| `robot.drop([side, count])`    | Выкинуть предмет.|
| `robot.suck([side, count])`    | Подобрать.       |

`side` ∈ `sides.front` (по умолчанию), `sides.up`, `sides.down`.

## Инвентарь робота

```lua
robot.select(slot)      -- выбрать слот (1..N)
robot.count([slot])     -- сколько предметов
robot.space([slot])     -- сколько ещё влезет
robot.compare([side])   -- сравнить с блоком впереди
robot.compareTo(slot)   -- сравнить с другим слотом
robot.transferTo(slot, count) -- передать в другой слот
```

## Энергия

```lua
local energy, max = computer.energy(), computer.maxEnergy()
-- Зарядка: робот возвращается на Charger.
```

## Контракты для наших плагинов

### `robot_crop.lua` (IC2 crops)

Использует `geolyzer` для скана грядки + `robot.use(sides.down)` для
снятия/посадки. Хранит state: `harvest_done`, `seed_inventory_slot`.

### `robot_miner.lua` (GT Miner)

Робот:

1. Принимает координаты от бэка (`x, y, z, dim`).
2. Идёт по навигации (GPS upgrade или relative-moves), ставит GT Miner.
3. Ждёт окончания (`computer.uptime() + N`).
4. Открывает выходной сундук, `suck()` всё в инвентарь.
5. Возвращается на базу, `drop()` в input-сундук AE.

State хранится на бэке: `idle | moving | placing | mining | returning | unloading | error`.

## Адресация роботов

У каждого робота — свой OC‑клиент с уникальным `env.clientId`, например
`robot_crop_01`, `robot_miner_02`. Бэк фильтрует задачи по `client_id`.

## Подводные камни

- Без GPS upgrade у робота нет понимания мировых координат — только
  относительные шаги. Решения: хранить позицию в `/data/robot_pos.json`
  на самом роботе и обновлять после каждого move, или поставить GPS.
- `swing()` ломает блок, но **не гарантирует** его подбора (могут быть
  чанк-границы). Всегда проверять `robot.suck()` или `inventory.size`.
- Робот не может ходить через жидкость/огонь без улучшений.
