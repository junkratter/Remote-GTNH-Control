# OpenComputers: ME Controller / ME Interface

> **Source:** https://ocdoc.cil.li/block:me_controller, https://wiki.gtnewhorizons.com/wiki/Open_Computers
> **Last updated:** 2026-05-16

## Подключение

Adapter блок должен **физически соприкасаться** с ME Controller **или**
ME Interface. Через MFU + adapter в радиусе 16 блоков — тоже работает.

После подключения компонент виден как `me_controller` или `me_interface`:

```lua
local component = require("component")
local me = component.me_controller  -- или me_interface
```

UUID видно через Analyzer (правый клик в руке) — записать в
`env.lua → aeAddress` для детерминированного `component.proxy(uuid)`.

## Ключевые методы ME

### Чтение состояния сети

| Метод                          | Возвращает                                   |
|--------------------------------|----------------------------------------------|
| `getItemsInNetwork([filter])`  | Все предметы в ME.                            |
| `getFluidsInNetwork()`         | Все жидкости.                                 |
| `getEssentiaInNetwork()`       | Essentia (Thaumcraft).                        |
| `getCraftables([filter])`      | Только крафтабельные предметы.                |
| `getCpus()`                    | Список Crafting CPU и их состояние.           |

`filter` — таблица: `{name="minecraft:cobblestone", damage=0, label="..."}`.

### Запрос крафта

```lua
local c = me.getCraftables({name="minecraft:torch", damage=0})[1]
local job = c.request(64 --[[amount]], true --[[prioritizePower]], "Cpu1" --[[cpuName]])
-- job:
job.isComputing(); job.isDone(); job.isCanceled(); job.hasFailed()
```

### CPU

```lua
for _, cpu in pairs(me.getCpus()) do
  print(cpu.name, cpu.busy, cpu.storage, cpu.coprocessors)
  -- cpu.cpu — userdata активного крафта:
  -- cpu.cpu.activeItems(), pendingItems(), storedItems(), finalOutput(),
  -- cpu.cpu.isActive(), isBusy(), cancel()
end
```

### ME Interface (расширенно)

ME Interface поверх обычных методов даёт паттерны (для автокрафта):

```lua
local iface = component.me_interface
iface.getInterfacePatterns()         -- список паттернов в слотах
iface.setInterfacePatternInput(slot, item_id, damage, amount)
iface.setInterfacePatternOutput(slot, item_id, damage, amount)
iface.removeInterfacePattern(slot)
```

Используется в Фазе 3 (программирование паттернов из UI).

## Тяжёлые операции

`getItemsInNetwork()` на большой сети — несколько тысяч записей по 5–10 КБ JSON.
Если выгружать одним запросом — OC уходит в OOM. Решение:

1. На стороне OC — yield (`os.sleep(0)` каждые 50 итераций).
2. На стороне бэка — `chunked: true` в `task_config`, передача через
   `/api/task/chunked_report?chunked=N`.

## Базовая схема записи Lua-плагина

```lua
-- oc-client/plugins/ae.lua
local component = require("component")
local env = require("env")
_G.ae = _G.ae or {}
local ae = _G.ae

local me  -- ленивая инициализация
local function getMe()
    if me then return me end
    if env.aeAddress and component.proxy(env.aeAddress) then
        me = component.proxy(env.aeAddress)
    elseif component.isAvailable("me_controller") then
        me = component.me_controller
    elseif component.isAvailable("me_interface") then
        me = component.me_interface
    end
    return me
end

function ae.getAllItems()
    local m = getMe()
    if not m then return { message = "ME unavailable" } end
    return { message = "success", data = m.getItemsInNetwork() }
end
```
