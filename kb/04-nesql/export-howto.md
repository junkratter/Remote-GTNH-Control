# NESQL: как экспортировать данные из Minecraft

> **Экспортёр для GTNH:** официальный репозиторий — **[GTNewHorizons/nesql-exporter](https://github.com/GTNewHorizons/nesql-exporter)**. **Готовых jar на GitHub Releases нет** — собери локально (`./gradlew build`) или используй доверенную сборку; в игре **`/nesql`**. Исходники для справки: submodule `kb/05-vendored/nesql-exporter` (read-only).  
> Старый [D-Cysteine/nesql-exporter](https://github.com/D-Cysteine/nesql-exporter) для актуального GTNH **не рекомендуется**. Другие форки ([RealSilverMoon](https://github.com/RealSilverMoon/nesql-exporter) и т.д.) могут давать **те же имена** jar — в `mods/` держи только **одну** пару «мод + deps».  
> **Last updated:** 2026-05-17

## 1. Установка

Мод **только клиентский** (зависимость: **NotEnoughItems**). Класть в `mods/` инстанса Prism / MultiMC (**не** в серверный `mods/`).

### 1.1. GTNewHorizons (рекомендуется)

Нужны **ровно два** файла из `build/libs/` после [сборки](#12-сборка-jar-из-gtnewhorizonsnesql-exporter). Версия в имени файла берётся из `gradle.properties` репозитория (сейчас **0.5.2**):

| Файл | Назначение |
|------|------------|
| `NESQL-Exporter-0.5.2.jar` | Сам мод |
| `NESQL-Exporter-0.5.2-deps.jar` | Зависимости Hibernate / SQL и т.д. (~25 MiB) |

Для полного экспорта аспектов Thaumcraft в рантайме нужен мод **[AspectRecipeIndex](https://github.com/GTNewHorizons/AspectRecipeIndex)** (jar в `mods/` той же версии линейки, что модпак; иначе при обработке рецептов возможен `NoClassDefFoundError: …aspectrecipeindex.ModItems` — см. §7). **Без AspectRecipeIndex** можно не пересобирать мод: отключи плагин **`thaumcraft`** в конфиге NESQL (§1.4) — в базе не будет таблиц аспектов, остальной экспорт сохранится.

В `mods/` **не** клади `*-sources.jar`, `*-dev.jar`, `*-sql.jar` — иначе Forge помечает их как «non-mod» и тащит в classpath (риск нестабильности).

### 1.2. Сборка jar из GTNewHorizons/nesql-exporter

```bash
git clone https://github.com/GTNewHorizons/nesql-exporter.git
cd nesql-exporter
./gradlew build
# только эти два файла копируй в mods/:
#   build/libs/NESQL-Exporter-<версия>.jar
#   build/libs/NESQL-Exporter-<версия>-deps.jar
```

Gradle тянет **RetroFuturaGradle** и артефакты с **`https://nexus.gtnewhorizons.com/repository/public/`**. Для самого Gradle нужен **JDK 17+**; компиляция под Minecraft 1.7.10 использует **Java 8 toolchain**. Если сборка падает:

| Симптом | Что попробовать |
|---------|-----------------|
| `Cannot find a Java installation … languageVersion=8` | В `settings.gradle.kts` **после** блока `pluginManagement { … }` добавить плагин `id("org.gradle.toolchains.foojay-resolver-convention") version "0.8.0"` ([документация Gradle](https://docs.gradle.org/current/userguide/toolchains.html#sub:download-repositories)), либо установить **JDK 8** (Temurin 8). |
| Плагин `com.gtnewhorizons.retrofuturagradle` не резолвится | В `pluginManagement.repositories` добавить `mavenCentral()`. При необходимости локально поднять версию `retrofuturagradle` в `build.gradle.kts` до актуальной с [релизов RetroFuturaGradle](https://github.com/GTNewHorizons/RetroFuturaGradle/releases) (патч только у себя; не слать в upstream без проверки). |

### 1.3. Старые / сторонние сборки

[RealSilverMoon/nesql-exporter](https://github.com/RealSilverMoon/nesql-exporter) и [D-Cysteine/nesql-exporter](https://github.com/D-Cysteine/nesql-exporter) могут публиковать готовые jar с похожими именами. Не клади их **вместе** с jar из GTNewHorizons.

Кратко по [README GTNewHorizons/nesql-exporter](https://github.com/GTNewHorizons/nesql-exporter):

1. Оба `NESQL-Exporter-*.jar` и `NESQL-Exporter-*-deps.jar` в `mods/`.
2. При наличии **BugTorch** — временно убрать из `mods/` (конфликт рендера зачарованных предметов при экспорте иконок).
3. Зайти в мир (удобен новый творческий одиночный).
4. В **GTNH NEI**: открыть инвентарь и дать списку предметов NEI прогрузиться — иначе часть предметов не попадёт в экспорт.
5. В чате: **`/nesql`** или **`/nesql имя_подпапки`** — база создаётся в `<minecraft>/nesql/` или `<minecraft>/nesql/имя_подпапки/`.
6. Можно поставить игру на паузу — экспорт идёт в фоне.
7. После экспорта оба jar можно удалить из `mods/`; BugTorch вернуть.

> OptiFine: при крашах трансформера — отключить OptiFine на время экспорта (как и для других тяжёлых клиентских модов).

### 1.4. Отключение плагинов без пересборки (в т.ч. Thaumcraft)

В коде экспортёра список активных плагинов задаётся опцией **`enabled_plugins`** ([`ConfigOptions.java`](https://github.com/GTNewHorizons/nesql-exporter/blob/main/src/main/java/com/github/dcysteine/nesql/exporter/main/config/ConfigOptions.java), [`PluginRegistry.java`](https://github.com/GTNewHorizons/nesql-exporter/blob/main/src/main/java/com/github/dcysteine/nesql/exporter/registry/PluginRegistry.java)). Имена плагинов: `base`, `minecraft`, `nei`, `forge`, `mobsinfo`, `avaritia`, `gregtech`, `thaumcraft`, `quest`.

**Готовый пресет** (только `base` + `minecraft` + `nei` + `gregtech` + `quest`, без Thaumcraft / Forge oredict / mobsinfo / Avaritia): скопируй [`kb/04-nesql/NESQL-Exporter.minimal.cfg`](NESQL-Exporter.minimal.cfg) в `<minecraft>/config/NESQL-Exporter.cfg` и перезапусти клиент.

Вручную:

1. Один раз включи запись конфига: в `<minecraft>/config/NESQL-Exporter.cfg` выставь **`enable_config_file=true`** (секция **`options`** / аналог в твоей версии файла — см. сгенерированный cfg после первого запуска с модом).
2. Перезапусти клиент, чтобы файл сохранился и подхватился.
3. В том же cfg в списке **`enabled_plugins`** оставь только нужные строки (см. пресет выше). Сохрани файл, перезапусти клиент и снова запусти **`/nesql`**.

В результате плагин Thaumcraft не инициализируется, обращений к **AspectRecipeIndex** не будет; **аспекты и связанные таблицы в дампе не появятся**. Без плагина **`forge`** в дампе не будет oredict / fluids из этого модуля — при необходимости добавь в список строку `forge`.

## 2. Запуск экспорта (in-game), выходные файлы

Команда:

```
/nesql
```

или, чтобы не затирать предыдущий каталог:

```
/nesql export_may2026
```

Файлы БД (HSQLDB), см. `Exporter.java` в репозитории — префикс **`nesql-db`**:

```
<minecraft>/nesql/              ← или nesql/<суффикс>/
├── nesql-db.script    ← SQL (для --source-sql в import.py)
├── nesql-db.properties
├── nesql-db.log
├── nesql-db.data
└── nesql-db.lobs      ← BLOB (иконки и т.п.)
```

- Полный экспорт GTNH у автора: **~60 мин**, база **~600 MiB** (см. README [GTNewHorizons/nesql-exporter](https://github.com/GTNewHorizons/nesql-exporter)).
- Прогресс смотри в **F3 → Mod Output** и `<minecraft>/logs/latest.log`.

Остановка: закрыть мир / прервать клиентом; отдельной команды `stop` в моде нет.

### Другие форки

У части сторонних сборок экспортёра встречаются другие подкоманды (например `/nesql start …`). Имена файлов БД могут отличаться (`nesql.script` вместо `nesql-db.script`). Импортёр `tools/nesql-import` принимает **любой** `.script` с `INSERT INTO` — укажи фактический путь к `*.script`.

## 3. Перенос на сервер

С локальной машины:

```bash
cd <minecraft>
tar czf /tmp/nesql.tgz nesql/
scp /tmp/nesql.tgz user@your-server:/tmp/
```

На сервере:

```bash
ssh user@your-server
mkdir -p /opt/remote-gtnh-control/data/nesql
cd /opt/remote-gtnh-control/data/nesql
tar xzf /tmp/nesql.tgz --strip-components=1
ls
# → подкаталоги с nesql-db.* или смешанный layout — положи путь к .script в --source-sql
```

## 4. Импорт в SQLite (на сервере)

В нашем форке `tools/nesql-import/import.py` умеет два режима:

### 4.1. Лайт-режим: `--source-sql` (без Java)

Парсит `INSERT INTO …` из файла скрипта HSQLDB. Пример (подставь свой подкаталог):

```bash
cd /opt/remote-gtnh-control
docker compose exec backend python /app/../tools/nesql-import/import.py \
    --source-sql /app/data/nesql/export_may2026/nesql-db.script \
    --dst /app/data/nesql.sqlite \
    --modules items,fluids,recipes,recipe_inputs,recipe_outputs,oredict,oredict_items,aspects,quests
```

С хоста:

```bash
cd /opt/remote-gtnh-control
python3 -m venv .venv && source .venv/bin/activate
pip install -r tools/nesql-import/requirements.txt    # необязательно для --source-sql
python tools/nesql-import/import.py \
    --source-sql data/nesql/export_may2026/nesql-db.script \
    --dst data/backend/nesql.sqlite
```

### 4.2. JDBC-режим: `--src` (с Java, для BLOB-данных)

Нужен, если хотим вытащить иконки/NBT из `.lobs`. Требует Java 11+ и
HSQLDB JAR (`hsqldb-2.7.4.jar`, скачать с https://hsqldb.org/).

```bash
mkdir -p tools/nesql-import/vendor
curl -L -o tools/nesql-import/vendor/hsqldb.jar \
    https://repo1.maven.org/maven2/org/hsqldb/hsqldb/2.7.4/hsqldb-2.7.4.jar
pip install -r tools/nesql-import/requirements.txt
python tools/nesql-import/import.py \
    --src data/nesql/export_may2026/nesql-db \
    --dst data/backend/nesql.sqlite \
    --hsqldb-jar tools/nesql-import/vendor/hsqldb.jar
```

(Префикс пути `--src` — каталог/имя без расширения, как создал экспортер.)

## 5. Проверка результата

```bash
sqlite3 data/backend/nesql.sqlite "SELECT module, row_count, imported_at FROM nesql_import_meta;"
# items|45123|2026-05-16 18:42:01
# recipes|231044|2026-05-16 18:43:15
# quests|1832|2026-05-16 18:43:18
# ...
```

Через бэкенд:

```bash
curl -fsS -H "X-Server-Token: $TOKEN" \
    http://127.0.0.1:18856/api/nesql/meta | jq
curl -fsS -H "X-Server-Token: $TOKEN" \
    "http://127.0.0.1:18856/api/nesql/items?q=iron&limit=5" | jq
curl -fsS -H "X-Server-Token: $TOKEN" \
    "http://127.0.0.1:18856/api/nesql/quests?q=GregTech&limit=5" | jq
```

## 6. Обновление при апдейте модпака

`NESQL-Exporter` не делает диффов. При мажорном апдейте модпака:

```bash
mv data/backend/nesql.sqlite data/backend/nesql_2.8.4.sqlite   # архив
# затем заново /nesql → scp → импорт
```

## 7. Частые ошибки

| Симптом | Лечение |
|---------|---------|
| Forge: «non-mod file … severe stability issues» | Убрать лишние `*-sources.jar` / `*-sql.jar` / дубликаты; оставить только **мод + deps** одного экспортёра (сейчас ожидаемые имена — `NESQL-Exporter-0.5.2.jar` + `NESQL-Exporter-0.5.2-deps.jar` из GTNewHorizons при версии в `gradle.properties` **0.5.2**). |
| Мод не грузится, а 25 MiB jar «не мод» | Большой файл — это **deps**; в `mods/` оба jar: `NESQL-Exporter-<версия>.jar` + `NESQL-Exporter-<версия>-deps.jar`. |
| `/nesql` неизвестна | Проверь, что загрузился `nesql-exporter` (FML лог); клиент 1.7.10 + NEI. |
| Пустой / короткий `nesql-db.script` | Не дождался конца; смотри `latest.log` и Mod Output; увеличь `-Xmx` (полный экспорт — долго и жирно по RAM). |
| Импорт: «script not found» | Укажи реальный путь к `…/nesql-db.script` (имя подкаталога после `/nesql суффикс`). |
| `Missing dependency 'jaydebeapi'` | Используй `--source-sql` (без Java) или поставь pip-deps. |
| 404 от `/api/nesql/meta` | Файл `data/backend/nesql.sqlite` не появился — проверь `--dst`. |
| После «Initializing plugins» в `latest.log`: `NoClassDefFoundError: gregtech/api/util/GT_LanguageManager` или `Class bytes are null for …GT_LanguageManager` | Собери и поставь актуальный экспортёр из **[GTNewHorizons/nesql-exporter](https://github.com/GTNewHorizons/nesql-exporter)** (`./gradlew build`). Убери старые jar (D-Cysteine / чужие форки), не смешивай две пары. После неудачи удали неполный `nesql/` (и `nesql-db.lck`, если есть) перед следующей попыткой. |
| Сразу после «Processing … crafting recipes» / `Exporting data…`: `NoClassDefFoundError: com/gtnewhorizons/aspectrecipeindex/ModItems` | Либо поставь **[AspectRecipeIndex](https://github.com/GTNewHorizons/AspectRecipeIndex)** в `mods/`, либо **отключи плагин `thaumcraft`** в `config/NESQL-Exporter.cfg` (список `enabled_plugins`, см. **§1.4**). После сбоя удали неполный каталог `nesql/…`. |
