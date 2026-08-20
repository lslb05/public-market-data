# public-market-data

Public market data ingestion that preserves **what was known on each date**,
so historical analysis doesn't use a future revision.

## The problem

Macro series get revised. FRED, BCB, and IBGE deliver today's reading and
overwrite the previous one without leaving a trace. A backtest built on top
of that sees, on a 2020 date, a GDP figure that was only published in 2021 —
and turns optimistic from a future-information leak that shows up in no log
anywhere.

This repository keeps the vintage: every value carries when it started being
valid and until when it was the current reading.

## Result

The same series, for the same reference period, queried on two dates:

```console
$ uv run python -m public_market_data query --source fred --series GDP --at 2020-05-01
event_date,value
2020-01-01,21561.139

$ uv run python -m public_market_data query --source fred --series GDP --at 2020-06-01
event_date,value
2020-01-01,21481.367
```

Q1 2020 GDP was 21,561.139 to anyone looking in May. The 05/28 revision
changed the number to 21,481.367. A May query doesn't see the June
revision — which is exactly the point.

The transcript above was produced with the fixture versioned in
`tests/fixtures/`, because a live fetch needs a FRED key. The code path is
the same; only the HTTP call is swapped.

## Problem and scope

- **User:** me, and the projects that consume this base — quantitative risk
  and the research agent.
- **Outcome:** lets a series be reconstructed as it was on a past date,
  without contaminating a backtest with a later revision.
- **Input:** FRED/ALFRED, via a public API with a free key. The series are
  public domain; the API docs are at
  <https://fred.stlouisfed.org/docs/api/fred/>.
- **Out of scope:** models, signals, and backtesting, which are a different
  repository; intraday data; and any source requiring institutional
  credentials.

## Architecture

```
Airflow (ingest_fred DAG, @daily)
    │  calls public_market_data.ingestion.fred.ingest_fred
    ▼
FRED API
    │  httpx, timeout, and 3 attempts
    ▼
sources/fred.py    adapter: fetch + Pydantic contract (FredObservation).
    │               a new field in the payload is a schema change, raises
    │
    ├─► raw.py         data/raw/<source>/<series>/collected=<timestamp>/
    │                  data.json (exactly what the source sent, byte for byte)
    │                  manifest.json (url, sha256, contract, rows)
    │
    └─► analytics.py   Postgres, series_vintage table
                       queried by knowledge date
```

The DAG (`dags/ingest_fred.py`) doesn't duplicate logic: it calls the same
function the CLI calls. The only thing Airflow adds is scheduling and
orchestration retries — idempotency and source-error handling already
existed.

**Organized by source, designed so the next source can arrive without
disturbing the current one.** `sources/<source>.py` is the adapter (talks to
the API, validates the payload, and returns objects that satisfy
`analytics.Observation` — a four-field structural `Protocol`, not a class to
inherit from). `ingestion/<source>.py` is the use case that wires that
adapter to the generic layer (`raw`, `analytics`, `postgres`) — that's why
it's a separate folder from `sources/`, not the same file: the adapter and
the orchestration change for different reasons. What's genuinely
source-agnostic (`raw.py`, `postgres.py`, `analytics.py`, `errors.py`,
`schema.sql`, `cli.py`) sits loose at the package root, with no folder,
because it doesn't grow per source — it grows by infrastructure decisions.

A simple source (FRED, one JSON endpoint) fits in a single file. A more
complex source (e.g. CVM, with multiple datasets and ZIP downloads) becomes
a folder — `sources/cvm/{__init__.py, contracts.py, download.py}` — once it
accumulates more than one reason to split (non-trivial parsing, a large
contract, its own pagination). Promoting a file to a folder is decided
source by source, when the real complexity shows up, not anticipated for
all of them at once.

`series_vintage(fonte, serie, data_evento, data_publicacao, vigente_ate,
valor, data_disponibilidade)` is this project's public interface: any other
repository reads from it via `DADOS_MERCADO_PUBLICO_POSTGRES_DSN`, without
importing code from here. (Table and column names stay in Portuguese
deliberately — they're the shared contract every consuming repo already
reads by name; renaming them would be a breaking change across the
portfolio, not a translation.) Primary key `(fonte, serie, data_evento,
data_publicacao)` — the same idempotency key as always.

Three decisions worth explaining:

**Three dates on every row.** `data_evento` is the reference period,
`data_publicacao` is when the source announced that value, and
`data_disponibilidade` is when we collected it. ALFRED returns the first two
as `realtime_start`/`realtime_end`, and that pair is what the query uses.

**The collection date doesn't filter the query — for this source.** ALFRED
publishes each vintage's real validity window, so it's the authority. A
source without vintages is a different story: for BCB SGS, which only
returns the current reading, the instant of our own collection becomes the
only reliable upper bound. That difference is a real limitation, documented
here instead of papered over.

**Idempotency by hashing the body.** Rerunning ingestion when the source
hasn't changed doesn't create a new partition or duplicate a row downstream.
The analytics layer's key is `(fonte, serie, data_evento, data_publicacao)`,
and the first occurrence wins, preserving when that value was first seen —
which is why Airflow can freely rerun the DAG without duplicating data.

## Running locally

Requirements: Python 3.12, [`uv`](https://docs.astral.sh/uv/), and Docker
(for the local Postgres).

```bash
uv sync
cp .env.example .env      # and fill in the FRED key
docker compose up -d      # brings up Postgres on localhost:5433
uv run python -m public_market_data ingest --source fred --series GDP
uv run python -m public_market_data query --source fred --series GDP --at 2020-05-01
```

The FRED key is free: <https://fredaccount.stlouisfed.org/apikeys>. Without
it the `ingest` command explains what's missing and exits with code 2,
instead of crashing. Without Postgres up, any command does the same.

The schema (`series_vintage`) is created automatically on the first
connection — there's no separate migration step.

### Airflow

`docker-compose.yml` also brings up Airflow (`LocalExecutor`, no
Celery/Redis — the simplest setup that's still real Airflow, fitting for a
portfolio project's volume):

```bash
docker compose up -d              # postgres + airflow-init (once) + scheduler
docker compose up -d airflow-webserver
```

UI at <http://localhost:8081> (user/password `admin`/`admin`, created by
`airflow-init`). The `ingest_fred` DAG runs `@daily`; to trigger it manually:

```bash
docker compose exec airflow-scheduler airflow dags trigger ingest_fred
```

Airflow's metadata lives in a separate Postgres database (`airflow`) on the
same server as `series_vintage` — two databases, one instance, no extra
infrastructure.

Verification:

```bash
uv run python scripts/check.py     # format, lint, types and tests
uv run python scripts/format.py    # applies formatting and fixes
```

## How this was validated

12 tests, 92% coverage. What they pin down:

- a query on a past date doesn't see a revision published later;
- reingesting the same content doesn't duplicate a partition or a row;
- the raw zone stores the original body byte for byte;
- the manifest doesn't contain the API key;
- a new field in the payload stops ingestion instead of slipping through;
- FRED's `.` becomes null, not zero;
- a 4xx isn't retried; a 5xx exhausts three attempts and becomes a named error.

## Limitations

- One source only. BCB SGS, CVM, SEC EDGAR, and EOD price are the next cuts —
  each becomes a new task on the same DAG or its own DAG.
- ALFRED exposes vintages; not every source does. Where it doesn't,
  point-in-time will be weaker, and that will be documented per source.
- `LocalExecutor`, not `CeleryExecutor`/`KubernetesExecutor`: parallelism
  limited to one machine. Enough for this project's series volume; revisit
  if that ever becomes a real bottleneck.
- Postgres and Airflow are local via `docker-compose`; production
  (credentials, backup, high availability) is deferred until there's a real
  environment to host it in.
