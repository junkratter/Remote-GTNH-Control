# Knowledge base (`kb/`)

Справочные выжимки по OpenComputers, GTNH, NESQL и архитектуре проекта.

## Состав

| Каталог | Содержание |
|---------|------------|
| `01-architecture/` | Архитектура, ADR, контракт API |
| `02-opencomputers/` | OC: установка клиента, компоненты, фильтры HTTP |
| `03-gtnh/` | Игровые механики GTNH |
| `04-nesql/` | Схема NESQL, экспорт/импорт |
| `05-vendored/` | Git submodules (только чтение) |
| `07-glossary.md` | Термины RU↔EN |

Обновление внешних срезов: `make kb-update` (см. `tools/kb-fetch/`).

## ADR

Решения по архитектуре — в `kb/01-architecture/decisions/NNN-title.md` (формат Status / Context / Decision / Consequences).
