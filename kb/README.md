# Knowledge base (kb/)

Structured notes on OpenComputers, GTNH, NESQL, AE2, and this project's architecture.
Intended for **human** contributors and operators — not shipped to automation tooling.

## How to navigate

1. Start with [`README.md`](../README.md) in the repo root (stack, quick start).
2. Architecture and API: [`01-architecture/`](01-architecture/) — overview, contract, ADRs.
3. OC client and robots: [`02-opencomputers/`](02-opencomputers/).
4. In-game mechanics: [`03-gtnh/`](03-gtnh/).
5. NESQL import and wiki icons: [`04-nesql/`](04-nesql/).
6. Upstream reference code: [`05-vendored/`](05-vendored/) (git submodules, read-only).
7. Terms: [`07-glossary.md`](07-glossary.md).

## Tree

```
kb/
├── 01-architecture/   Architecture, ADR, API contract, first GitHub push guide
├── 02-opencomputers/  OC excerpts + oc-client-install.md
├── 03-gtnh/           GTNH mechanics (crops, miner, AE2 patterns, power)
├── 04-nesql/          NESQL schema and import
├── 05-vendored/       Upstream submodules (read-only)
└── 07-glossary.md     GTNH/OC terms, RU↔EN
```

## Content rules

- Each file under `02-*` / `03-*` should stay a **short excerpt** (target ≤ ~200 lines), not a full wiki dump.
- Header: `Source:` and `Last updated:` where applicable.
- Refresh excerpts via `tools/kb-fetch/` (`make kb-update`).

## ADR (Architecture Decision Records)

`kb/01-architecture/decisions/NNN-title.md` — format: Status / Context / Decision / Consequences.
