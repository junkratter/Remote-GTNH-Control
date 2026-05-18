# GTNH: AE2 Patterns и автокрафт через OC

> **Source:** https://wiki.gtnewhorizons.com/wiki/Applied_Energistics_2, ME Interface API
> **Last updated:** 2026-05-16

## Что такое паттерн

`Encoded Pattern` — предмет, описывающий рецепт (inputs + outputs).
Помещённый в `ME Interface`, он делает соответствующий рецепт доступным
для автокрафта через ME сеть.

```
Encoded Pattern = template + N inputs + 1-9 outputs + processing/crafting флаг
```

Типы:

- **Crafting** — обычный 3×3 крафт; выходит из ME Interface в Molecular
  Assembler / любую соседнюю верстак-машину.
- **Processing** — машинный рецепт; ME Interface выкидывает inputs в
  сторону машины, ждёт обратно outputs (обычно через Storage Bus).

## API ME Interface

```lua
local iface = component.me_interface

iface.getInterfacePatterns()
-- [{slot=1, inputs={...}, outputs={...}, isCrafting=true}, ...]

iface.setInterfacePatternInput(slot, item)
-- item: {name="gregtech:gt.metaitem.01", damage=12345, amount=4}

iface.setInterfacePatternOutput(slot, item)
iface.removeInterfacePattern(slot)
```

Тонкость: на сильно модифицированных серверах часть методов может быть
переименована (например, `setProcessingInput`). Проверять Analyzer'ом
конкретный ME Interface.

## Программирование паттерна с бэка

```python
# server/app/modules/autocraft/patterns.py
def program_pattern(client_id, slot, inputs, outputs, kind="processing"):
    cmds = [f"return iface.removeInterfacePattern({slot})"]
    for i, inp in enumerate(inputs, 1):
        cmds.append(
            f"return iface.setInterfacePatternInput({slot}, "
            f"{{name='{inp['name']}', damage={inp['damage']}, amount={inp['amount']}}})"
        )
    for i, out in enumerate(outputs, 1):
        cmds.append(
            f"return iface.setInterfacePatternOutput({slot}, "
            f"{{name='{out['name']}', damage={out['damage']}, amount={out['amount']}}})"
        )
    return cmds
```

Команды складываются в один task → OC выполняет последовательно.

## Заказ крафта

Уже реализовано в `oc-client/plugins/ae.lua`:

```lua
ae.requestItem(name, damage, amount, cpuName, label)
```

UI шлёт `POST /api/autocraft/request` → бэк формирует задачу с этим
вызовом → OC отвечает таблицей `{item, failed, computing, done, canceled}`.

## Очередь / статус CPU

```lua
ae.getCpuList(true)  -- с детальной инфой: activeItems, pendingItems, finalOutput
```

UI рисует очередь крафтов, можно отменять через `ae.cancelCraftingByCpuName(name)`.

## Ограничения

- ME Interface держит максимум 36 паттернов (стандартный слот-лимит).
  Для большего — стек из нескольких Interface, бэк маршрутизирует
  паттерны по `iface_id`.
- `setInterfacePattern*` записывает в **сухую** ячейку; перед записью
  обязательно очистить (`removeInterfacePattern`), иначе ME может
  отбросить запись.
- Паттерн с пустыми inputs/outputs — UB; всегда валидировать на бэке.
