# `tools/nesql-import/`

Импортирует HSQLDB-дамп `NESQL-Exporter` в нашу SQLite (по умолчанию
`server/data/nesql.sqlite`). Используется в Фазе 2 (Wiki / Quests).

## Установка

```bash
cd tools/nesql-import
pip install -r requirements.txt
# нужна Java JDK (для JDBC HSQLDB), HSQLDB jar лежит рядом в `vendor/`
```

## Использование

```bash
# Полный импорт
python import.py \
    --src ./data/nesql/nesql-db \
    --dst ./data/backend/nesql.sqlite \
    --hsqldb-jar ./vendor/hsqldb-2.7.4.jar

# Импорт только items + recipes (быстрее)
python import.py --modules items,recipes
```

## Что делает

1. Поднимает HSQLDB через JDBC (`jaydebeapi`).
2. Селектит данные пакетами по 5000 строк.
3. Пишет в новую SQLite (`nesql.sqlite`) транзакцией.
4. Создаёт индексы (`localized_name`, `mod_id`, `aspect_name`, …).
5. По умолчанию — идемпотентный `REPLACE INTO`.

Целевая схема — `kb/04-nesql/schema.md`.

## Размеры

- Полный GTNH: HSQLDB ≈ 600 МБ, SQLite ≈ 100 МБ.
- Время импорта: 3–10 мин в зависимости от диска.

## Ошибки

| Симптом                              | Лечение                              |
|--------------------------------------|---------------------------------------|
| `JDBC class not found`               | Указать `--hsqldb-jar`.               |
| `Database lock failed`               | Не запускать игру и импорт одновременно. |
| `disk I/O error` в SQLite            | Проверить место на диске.             |
