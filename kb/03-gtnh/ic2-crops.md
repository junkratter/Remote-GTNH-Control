# GTNH: IC2 Crops (фарм и мутации)

> **Source:** https://wiki.gtnewhorizons.com/wiki/IC2_Crops, GTNH wiki, ftbwiki.org/IC2_Crop_Manipulator
> **Last updated:** 2026-05-16

## Принцип

IC2 crops — отдельный фарм поверх обычных пшеничных грядок. На блок земли
ставится `crops:cropBlock`, затем сидекапсула; растение растёт стадиями
0→4. На стадии 3 можно «right‑click» для сбора (drop), оставшись на
стадии 1 — продолжает расти.

Ключевые атрибуты растения:

| Атрибут          | Что значит                                    |
|------------------|------------------------------------------------|
| `growth`         | Скорость роста (1–32).                         |
| `gain`           | Дроп с харвеста (1–32).                         |
| `resistance`     | Сопротивляемость болезням (1–32).               |
| `tier`           | Тир (биржевая ценность).                        |
| `discovered`     | Идентифицирован игроком (или Cropnalyzer).      |

Сумма `growth + gain + resistance ≤ 32` (примерно), иначе мутации
становятся капризными.

## Скрещивание

Между двумя крестообразно стоящими крестами появляется sapling нового
вида. Шансы мутации зависят от:

- `growth + gain + resistance` родителей.
- Уровня освещения / биома / hydration / nutrients / weed‑ex.

GTNH добавляет десятки видов: ferru/aurelia/aluminia (металлы),
ultimateBloodCrop, sugarcane++, etc. Полный список в JEI (вкладка IC2 Crops).

## Команды робота для крафта-харвестера

Робот стоит над крестом (или соседним блоком), оборудование:

- Adapter + Inventory Controller upgrade — читать стадию.
- Inventory upgrade — место под дропы.
- Geolyzer upgrade — опционально, для скана wetness/nutrients.

```lua
local sides = require("sides")
local robot = require("robot")
local inv   = component.inventory_controller

-- Сканировать crop под роботом
local stack = inv.getStackInInternalSlot(1) -- пример
local crop  = inv.getStackInSlot(sides.down, ...)

if crop and crop.label == "Crop Stick" and crop.growth >= 3 then
    robot.swing(sides.down)
    robot.suck(sides.down)
end
```

Для скана *внутри* `cropBlock` нужен Inventory Controller или
peripheral `crop_manipulator` (IC2 addon).

## IC2 Crop Manipulator (peripheral)

Это блок-периферия для OpenComputers, который умеет:

- `getCrop(side)` — таблица `{name, growth, gain, resistance, scanned, tier}`.
- `harvestCrop(side)` — собрать урожай (≥ stage 3).
- `removeCrop(side)` — выкорчевать.
- `plantCrop(side, slot)` — посадить из инвентаря робота.

Если на сервере не установлен этот мод — fallback на `geolyzer` + `robot.swing()`.

## Стратегия плагина `oc-client/plugins/robot_crop.lua`

1. Бэк присылает задание `crop.scan_area({x,z,w,d})`.
2. Робот идёт по сетке, для каждого крестика → `getCrop(down)`.
3. Готовые (`growth ≥ 3`) — `harvest`.
4. Все слоты инвентаря → `drop(sides.front)` в воронку → AE.
5. На бэк уходит сводка `{harvested: N, scanned: [{name, gain, growth, resistance}], errors}`.

## Селекция

Отдельная задача `crop.breed_loop`: робот следит за двумя «родителями»,
вырезает все sapling‑дети, сканирует, если `gain > X` или `growth > Y`
— оставляет, иначе вырывает. Эволюционирует ферму к топ-генетике.

В первой итерации делаем только harvest, breed — позже.
