# Craft resolved graph — operational checklist

Use after importing **NESQL** into `nesql.sqlite` and pointing **`SYNC_DATABASE_URL`** at the **main** database (SQLite locally or Postgres on Docker).

## Order

1. **Aliases / OreDict**: seed alias rows so inputs resolve consistently (`seed_aliases`, documented alongside `server/app/modules/craft/seed_aliases.py`).
2. **Rebuild resolved**:  
   `NESQL_SQLITE_PATH=/path/to/nesql.sqlite make craft-graph-build`  
   This truncates `craft_recipes_resolved` (+ inputs/outputs) and writes freshness stats into `craft_resolved_snapshot` id `1`.
3. **Prod Docker**: after pulling compose changes with Postgres enabled, run **`docker compose exec backend alembic upgrade head`** once on an empty Postgres schema before SQLite→PG data copy (`tools/deploy/README.md`, `tools/migrate-sqlite-to-pg.py`).
4. **Smoke**: **`GET /api/craft/health`** → counts + optional `resolved_graph_built_at`; **`POST /api/craft/plan`** against a known alias id.

## Related API

- **`GET /api/craft/item-alias?nesql_item_id=&damage=`** — ensures a singleton alias for picker-driven flows.
- **`GET /api/craft/me/stock`** — Redis-backed AE overlay hints per alias when **`OPTIONAL_REDIS_URL`** is set and **`getAllItems`** tasks completed.
