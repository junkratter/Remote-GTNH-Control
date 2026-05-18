# ADR 005 — Performance baseline (NESQL / quests / wiki)

**Status:** implemented
**Date:** 2026-05-18
**Completed:** 2026-05-18

## Context

Hot endpoints under `/api/nesql/*` and `/api/quests/*` are slow on a
fully-imported NESQL (≈45k items, ≈230k recipes, ≈2k quests):

1. `server/app/modules/nesql/router.py` and `app/modules/quests/router.py`
   call `sqlite3.connect(path)` **per request** inside an `async` handler,
   blocking the event loop and paying connect/PRAGMA overhead each time.
2. Item search uses `LIKE '%q%'` against `nesql_items.localized_name`. The
   existing B-tree index on `localized_name`
   (`tools/nesql-import/import.py:38`) is unusable for leading-wildcard
   patterns, so every search is a full scan.
3. `/api/quests/tree` returns the whole flat list on every call; there is
   no in-process cache and no `ETag` / `Cache-Control`.
4. `create_app()` in `server/app/main.py:46` ships without `GZipMiddleware`,
   so quest descriptions and large NESQL payloads travel uncompressed.
5. The deploy runs a single uvicorn worker; any blocking SQLite call stalls
   the whole API.

The plan is to remove these bottlenecks **before** any domain-model
changes. Numbers in production logs and synthetic benchmarks show this
class of work (gzip + ETag + FTS5 + connection reuse) usually buys
×3–10 on read-heavy NESQL pages without touching business logic.

## Decision

1. **Single shared NESQL connection.**
   Open `sqlite3.connect(nesql_path, check_same_thread=False)` once in
   `lifespan()` (`server/app/main.py:29`) and store on `app.state.nesql`.
   Apply read-friendly pragmas at open time:

   ```sql
   PRAGMA query_only = 1;
   PRAGMA journal_mode = WAL;
   PRAGMA mmap_size = 268435456;
   PRAGMA cache_size = -65536;     -- ~64 MiB page cache
   PRAGMA temp_store = MEMORY;
   ```

   All NESQL handlers call into the shared connection via
   `await asyncio.to_thread(conn.execute, ...)` to keep the event loop
   responsive. Old `_open_nesql` context manager becomes a thin shim that
   yields `app.state.nesql` for backwards compatibility.

2. **FTS5 virtual tables on NESQL.**
   `tools/nesql-import/import.py` creates `nesql_items_fts` and
   `nesql_quests_fts` with `content='nesql_items' / 'nesql_quests'` and
   `content_rowid='id'`. Handlers route substring search through
   `MATCH ?` rather than `LIKE`. Schema migration is one-way (drop +
   recreate on next import); no data version bump required.

3. **HTTP layer: gzip + ETag + Cache-Control.**
   - Add `GZipMiddleware(minimum_size=1024)` in `create_app()`.
   - For read-only NESQL / quests responses set
     `Cache-Control: public, max-age=86400, stale-while-revalidate=86400`
     and an `ETag` derived from `mtime` of `nesql.sqlite` plus the query
     string. Clients revalidate cheaply with `If-None-Match`.
   - `/api/info/version` and `/api/health` stay uncached.

4. **In-process quest tree cache.**
   Compute the full quest tree once on first request, store on
   `app.state.quests_tree = {mtime, payload}` and invalidate when
   `nesql.sqlite` mtime changes. The cached payload is returned to
   `/api/quests/tree` and `/api/quests/lines` without touching SQLite
   again.

5. **Multi-worker uvicorn / gunicorn.**
   `tools/deploy/` and `server/Dockerfile` switch the entrypoint to
   `gunicorn -k uvicorn.workers.UvicornWorker -w ${BACKEND_WORKERS:-4}`.
   `BACKEND_WORKERS` defaults to `4` in `.env.example`. The shared NESQL
   connection is **per-process** — each worker opens its own.

6. **Optional: Redis for shared L1 cache.**
   Introduced behind an `OPTIONAL_REDIS_URL` env var. If set, hot lookups
   (`nesql:item:{unlocal}:{dmg}` → `(id, alias_id, mod_id)` and
   `nesql:recipes_by_output:{item_id}`) are cached with 24 h TTL and
   invalidated by `make nesql-import` (the import script flushes the
   `nesql:` namespace). The fallback path keeps everything in process
   memory — Redis is purely additive.

## Consequences

- `_open_nesql` semantics change: callers no longer own the connection;
  `with` blocks still work but must not call `conn.close()`. Tests
  monkey-patch `app.state.nesql` to a temp file connection.
- FTS5 requires SQLite built with FTS5 (default on official wheels and
  most distros). Bookkeeping query in `nesql_import_meta` records FTS
  presence so the API can fall back to `LIKE` if FTS is missing.
- HTTP cache + ETag relies on `nesql.sqlite` mtime being stable until the
  next import. Container restarts do not bust the cache; the file is on a
  persisted volume.
- Switching to `gunicorn` adds a dependency in `server/requirements.txt`
  and changes the process tree (one master, N workers). Logging stays the
  same; structured logs already include `pid`.
- Redis is **opt-in**. The performance baseline must hold even without
  Redis; failing to connect logs a warning and skips the cache.

## Links

- `server/app/modules/nesql/router.py`
- `server/app/modules/quests/router.py`
- `server/app/main.py`
- `tools/nesql-import/import.py`
- `kb/04-nesql/schema.md`
