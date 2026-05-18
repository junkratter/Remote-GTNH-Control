# GTNH: развёртывание генераторов роботом

> **Last updated:** 2026-05-17  
> **Плагин:** `oc-client/plugins/robot_power.lua`  
> **API:** `/api/robots/power-jobs*`

## Назначение

Робот-оператор ставит **одноблочный генератор** (Combustion / Advanced Combustion)
или **Gas Turbine** и заливает **топливо из капсул** в инвентаре (diesel, gas, …).

Как у майнера: координаты с веб-UI, навигация **вручную**, выполнение через `/api/task/add`.

## Типы (метаданные в задании)

| `generator_kind` | Машина |
|------------------|--------|
| `combustion_generator` | LV Combustion Generator |
| `advanced_combustion_generator` | MV Advanced Combustion Generator |
| `gas_turbine` | одноблочная Gas Turbine (жидкое/газовое топливо) |

| `fuel_kind` | Примеры предметов в слотах робота |
|-----------|-----------------------------------|
| `diesel` | Diesel Cell / Fuel Canister |
| `gasoline` | Gasoline capsules |
| `gas` | Natural Gas / Gas Cell (для турбины) |
| `ethanol` | Ethanol cells |

## Инвентарь робота

| Слот | Содержимое |
|------|------------|
| 1 | Блок генератора (для `placeForward`) |
| 2–6 | Капсулы с топливом (`capsule_count` в задании) |

## Команды Lua (из задачи)

```lua
return robot_power.ping()
return robot_power.acceptJob({ job_id=1, x=100, y=70, z=200, dim=0,
  generator_kind="advanced_combustion_generator", fuel_kind="diesel", capsule_count=4 })
return robot_power.placeForward()
return robot_power.insertCapsules({ fuel_slots={2,3,4,5,6}, capsule_count=4 })
return robot_power.deploy({ job_id=1, x=100, y=70, z=200, dim=0,
  generator_kind="advanced_combustion_generator", fuel_kind="diesel",
  capsule_count=4, generator_slot=1, fuel_slots={2,3,4,5,6} })
```

## Подводные камни

- `robot.use(sides.front)` — правый клик по машине; GUI GT должен принять жидкость из капсулы.
- Gas Turbine часто принимает **gas**, не diesel — укажите `fuel_kind=gas` в задании.
- Подключите **кабель EU** к генератору после установки (вручную или вторым заданием).

## Ссылки

- `kb/02-opencomputers/robots-setup.ru.md` — §6  
- `kb/03-gtnh/gt-miner.md` — аналогичный сценарий для майнера
