# Глоссарий GTNH / OpenComputers / AE2

> RU ↔ EN термины, чтобы агент и игрок говорили на одном языке.

| Термин (RU)               | EN                                | Что значит                                              |
|---------------------------|-----------------------------------|----------------------------------------------------------|
| Сеть AE / ME‑сеть          | AE / ME network                   | Applied Energistics 2 storage network.                  |
| ME‑контроллер              | ME Controller                     | Центральный блок AE2.                                   |
| ME‑интерфейс               | ME Interface                      | Интерфейс ввода/вывода + хранение паттернов.            |
| Паттерн                    | Encoded Pattern                   | Запись «рецепт + N выходов».                            |
| Автокрафт                  | Autocraft / Crafting CPU          | Заказ предметов через AE2.                              |
| OC, ОС                     | OpenComputers                     | Мод; компьютеры/роботы на Lua.                          |
| Адаптер                    | Adapter                           | Блок OC, подключающий машину к компьютеру.              |
| Геолайзер                  | Geolyzer                          | Апгрейд робота; сканирует hardness.                     |
| Интернет‑карта             | Internet Card                     | HTTP/TCP в OC; Tier 2+.                                 |
| GT, ГТ                     | GregTech                          | Мод-индустриализатор GTNH.                              |
| Майнер                     | Miner / Advanced Miner            | GT-машина «копай вниз».                                 |
| Кропсы / Айси‑кропы        | IC2 Crops                         | Селекционная ферма Industrial Craft 2.                  |
| Квестбук                   | BetterQuesting / Quest Book       | Дерево квестов в GTNH.                                  |
| Аспекты                    | Aspects                           | Thaumcraft эссенции (Aer, Metallum, ...).               |
| Жидкость / флюид           | Fluid                             | Любая жидкая в ME (сталкивается с термином «liquid»).   |
| Эссенция / источник        | Essentia                          | Thaumcraft Essentia в ME (отдельный API).               |
| Чанк                       | Chunk                             | 16×256×16 блоков MC.                                    |
| Тик                        | Tick                              | 1/20 секунды MC.                                        |
| Поллинг                    | Long polling                      | OC спрашивает бэк каждые `pollingInterval` секунд.      |
| Чанковая выгрузка          | Chunked upload                    | `POST /api/task/chunked_report?chunked=...`.            |
| Бэк / бэкенд               | Backend                           | Python FastAPI.                                         |
| Фронт                      | Frontend / SPA                    | Vue 3 + Element Plus.                                   |
| Робот                      | Robot                             | Мобильный OC компьютер.                                 |
| Адрес ME (UUID)            | ME UUID                           | Поле `env.aeAddress` — UUID из Analyzer.                |
| Креатив‑миры               | Creative                          | Наш `versions/2.8.4_creative`, порт 25565.              |
| Сервер‑токен               | `SERVER_TOKEN`                    | Совпадает в `.env` бэка и `env.lua` OC.                 |
