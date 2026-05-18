# OpenComputers: компонент `internet`

> **Source:** https://ocdoc.cil.li/component:internet
> **Last updated:** 2026-05-16

## Что это

Программный API карты Internet Card (Tier 2+). Доступен как
`require("internet")` (high-level wrapper) или как компонент
`component.internet` (low-level).

## Методы (high-level `require("internet")`)

```lua
local internet = require("internet")

-- HTTP-запрос. postData / headers опциональны.
local req = internet.request(url, postData, headers)

-- TCP-сокет.
local sock = internet.open(address [, port])

-- iterator по строкам с веба.
for line in internet.request(url) do ... end
```

`internet.request()` возвращает **userdata**:

| Метод           | Описание                                       |
|-----------------|------------------------------------------------|
| `finishConnect()` | `true`, когда соединение установлено.        |
| `read([n])`     | Прочитать n байт (или EOF).                    |
| `response()`    | Возвращает `code, message, headers`.           |
| `close()`       | Закрыть соединение.                            |

## Типичный цикл

```lua
local req = internet.request("http://example.com", nil, {["X-Foo"]="bar"})
local startTime = computer.uptime()
while not req.finishConnect() do
    if computer.uptime() - startTime > 4 then
        req.close(); error("timeout")
    end
    os.sleep(0)
end
local data = ""
repeat
    local chunk = req.read()
    if chunk then data = data .. chunk end
until not chunk
req.close()
```

## Ограничения и фильтрация

- `filteringRules` в `OpenComputers.cfg` (см. `kb/02-opencomputers/filtering-rules.md`).
- TCP/HTTP можно выключить целиком (`enableTcp=false`, `enableHttp=false`).
- Максимальный размер ответа лимитируется в конфиге.

## Частые ошибки

| Сообщение                       | Причина                                  |
|---------------------------------|-------------------------------------------|
| `address is not allowed`        | Заблокировано `filteringRules`.           |
| `internet access is unavailable`| Сломан синтаксис `filteringRules`.        |
| `http requests are unavailable` | `enableHttp=false` в OpenComputers.cfg.   |

## Тонкость GBK

OC шлёт тело как байты. Если на сервере поднят Java/Python, парсящий
строго UTF‑8, возможна ошибка декодирования. В нашем бэке `decode_request_body()`
делает fallback UTF‑8 → GBK.
