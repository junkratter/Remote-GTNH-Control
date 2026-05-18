# OpenComputers: `filteringRules` — ловушки

> **Source:** Наша сессия 2026‑05‑15 + https://ocdoc.cil.li/sandbox:openos
> **Last updated:** 2026-05-16

## Где править

```
<minecraft>/config/OpenComputers.cfg
```

На нашем GTNH:

```
<minecraft>/config/OpenComputers.cfg   # пример: creative-инстанс
<minecraft>/config/OpenComputers.cfg   # второй инстанс — свой путь
```

После правки **обязательно** перезапустить Minecraft‑сервер.

## Базовый блок

```hocon
internet {
    enableHttp = true
    enableTcp  = true
    httpTimeout = 5
    filteringRules = [ "allow default" ]
}
```

## Подвох `"allow default"`

Внутри `allow default` уже зашиты `deny private` и `deny bogon`. Это
блокирует **127.0.0.0/8, 192.168.x, 10.x, 172.16-31.x** — то есть весь
LAN и localhost. Раскомментирование явных `deny private` тут не поможет —
их там и нет, но они **подразумеваются**.

## Рабочая конфигурация для нашего стека

```hocon
filteringRules = [
  "allow ip:127.0.0.0/8"
  "allow ip:192.168.0.0/16"
  "allow ip:10.0.0.0/8"
  "allow ip:172.16.0.0/12"
  "allow all"
]
```

Порядок важен — правила оцениваются сверху вниз. После `allow all`
дальнейшие правила игнорируются.

## Проверка после рестарта MC

В логе сервера должна быть строка:

```
[INFO] OpenComputers: Successfully applied 5 Internet Card filtering rules
```

На OC внутри игры:

```lua
local i = component.internet
local r = i.request("http://127.0.0.1:8856/api/task/get",
                    "",
                    {["X-Server-Token"]="<token>", ["X-Client-ID"]="client_01"})
while not r.finishConnect() do os.sleep(0) end
print(r.read())
r.close()
```

Если приходит `nil` / `address is not allowed` — правила не применились.

## Альтернативные сценарии

- **Только публичный домен:** оставить `allow default`, но в `env.lua`
  поставить публичный домен/IP — тогда private‑deny не сработает.
- **Hairpin NAT** (наш кейс): сервер не может достучаться до своего
  публичного IP. Решение — `iptables` в `/etc/ufw/before.rules` (см.
  `kb/01-architecture/overview.md`, раздел 2.5).
