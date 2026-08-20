# Project contract — Public Market Data

Read the global `CLAUDE.md` and use this file for what's specific to this
repository.

## Product outcome

- **Problem:** quantitative analysis needs to know what was available on a
  past date, not today's revision. Public macro sources deliver the current
  vintage and overwrite the previous trail without warning, which produces
  an optimistic backtest from a future-information leak.
- **User:** me, and the projects that consume this base — quantitative risk
  and the research agent.
- **Verifiable output:** a raw zone partitioned by collection run, with a
  manifest, and a Postgres table (`series_vintage`) queryable by knowledge
  date. A query on a past date doesn't see a revision published after it.
- **Allowed data source:** FRED/ALFRED, BCB SGS, CVM Dados Abertos, SEC
  EDGAR, B3 COTAHIST, and Stooq. No data, methodology, or credential from
  work, under any circumstance.
- **Smallest end-to-end cut:** `ingest --source fred --series GDP` writes the
  raw zone with a manifest and publishes to `series_vintage`;
  `query --series GDP --at 2020-06-30` returns the value that was known on
  that date.
- **Out of scope:** models, signals, and backtesting (that's a different
  repository); intraday data; and any source requiring institutional
  credentials.
- **Public interface:** `series_vintage` is the contract for the consuming
  projects (quantitative risk, research agent). They read via
  `DADOS_MERCADO_PUBLICO_POSTGRES_DSN`, never import code from this
  repository.

Do not implement while a `FILL_IN` that changes the design is still open.

## Commands

```bash
uv sync
uv run python scripts/format.py
uv run python scripts/check.py
```

## Local rules

- The package is `public_market_data` and lives in `src/public_market_data`.
- Notebooks import from `src/`; production code never imports a notebook.
- Configuration comes from the environment via `Settings`.
- Preserve raw data and time-vintage metadata whenever there's ingestion.
- Update this file when a structural decision changes.

## Style

Public code, read by people. The rule is restraint — the full list is in
`AGENTS.md`, "Style" section, and applies equally to me and to Codex.

- A comment explains *why*, never *what*. If it paraphrases the line below,
  delete it; if the line needs paraphrasing, rename the variable instead.
- Docstrings only where the signature isn't enough (unit, timezone, side
  effect, what it raises). A three-line private helper doesn't need one.
- Tests assert behavior that can break, not a constant. Coverage is a
  consequence of testing what matters, never a target to inflate.
- Don't catch an exception you don't know how to handle; don't abstract for
  a single caller.

## Commit authorship

Author and committer are one and the same: the repository owner. No
`Co-Authored-By:`, no session trailer, no mention of Claude, Codex or any
tool. Don't change `user.name` or `user.email`.

## Session state

- **Decided:** first cut delivered — FRED/ALFRED from source to
  point-in-time query, with an immutable raw zone, a manifest, and
  hash-based idempotency. The query filters by the source's validity
  window, not by collection date.
- **Decided:** second cut delivered — the analytics layer switched from
  Parquet/DuckDB to Postgres (`series_vintage`), local via
  `docker-compose.yml`. Idempotency became `ON CONFLICT DO NOTHING` on the
  key `(fonte, serie, data_evento, data_publicacao)`, instead of in-memory
  dedup. Tests use an ephemeral Postgres via `testcontainers` — they require
  Docker running on the machine that runs `pytest`.
- **Decided:** third cut delivered — orchestration via Airflow
  (`LocalExecutor`, no Celery/Redis), a dedicated image in
  `docker/airflow/Dockerfile` that installs this package, an `ingest_fred`
  DAG (`dags/ingest_fred.py`) calling `ingestion.ingest_fred` — no
  duplicated logic. Airflow's metadata lives in a separate Postgres database
  (`airflow`) on the same instance as `series_vintage`. Tested by bringing
  up the real stack (`docker compose build/up`) and confirming
  `airflow dags list-import-errors` is empty and the `ingest` task is
  registered — there's no local unit test for the DAG because installing
  `apache-airflow` natively in the dev environment (Windows) would break the
  project's `uv sync`; CI validates this in a separate job
  (`airflow-dag` in `.github/workflows/ci.yml`) that builds the image and
  runs `airflow dags list-import-errors` inside the container.
- **Decided:** fourth cut — reorganize by source, ahead of the 2nd source
  arriving. `contratos.py` and `ingestao.py` were "generic" files that only
  had FRED inside; that was going to become a file growing per source, the
  opposite of what its name promised. `FredObservation`/`FredResponse` moved
  into `sources/fred.py` (the contract lives next to the adapter that
  produces it); `ingest_fred` became `ingestion/fred.py` (a folder, one file
  per source, matching `sources/`'s pattern). `analytics.publish()` stopped
  importing `FredObservation` by name and instead requires a structural
  `Protocol` (`analytics.Observation`, four fields) — the layer that's
  genuinely source-agnostic can't depend on a type with a source's name in
  the middle. Rule recorded in the README: one file per source is the
  default; it becomes a folder (`sources/<source>/{__init__,contracts,...}.py`)
  once a source accumulates real complexity (multiple endpoints,
  non-trivial parsing, a large contract) — decided source by source, not all
  at once. `dags/` stays flat (`ingest_<source>.py`), Airflow's standard
  convention, no subfolder.
- **Pending:** a free FRED key for live collection; tests run offline with a
  versioned fixture and don't depend on it.
- **Next step:** BCB SGS — the source without vintages, which forces the
  `data_disponibilidade` upper bound to be explicit. The first real test of
  the per-source convention: `sources/bcb.py`, `ingestion/bcb.py`,
  `dags/ingest_bcb.py`, and `cli.py` gets `"bcb"` added to `--source`'s
  choices.
