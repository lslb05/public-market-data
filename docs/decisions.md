# Decisions

Record only decisions that change the future cost of change.

## Template

### YYYY-MM-DD — Title

- **Context:** what constraint or problem required a decision.
- **Decision:** the path chosen.
- **Alternatives:** relevant options discarded.
- **Consequences:** gains, costs and the trigger to revisit.

### 2026-08-18 — Keep `CLAUDE.md` and `AGENTS.md` in the public repository

- **Context:** both files declare that the repository is built with agent
  support. The alternative was ignoring them in git so the public
  repository wouldn't reveal the workflow.
- **Decision:** keep both versioned and public.
- **Alternatives:** ignore `AGENTS.md` in `.gitignore`; keep it local only.
  Both break delegation to Codex, which reads this file from the
  repository — the cost is functional and immediate, the gain is cosmetic.
- **Consequences:** the repository states the method instead of hiding it,
  which is also verifiable by whoever reads it. Revisit if some destination
  ever requires the opposite.

### 2026-08-19 — Analytics layer migrates from Parquet/DuckDB to Postgres

- **Context:** this repository is becoming the data source for several other
  portfolio projects (nowcasting, credit, vol/options, AI), which need to
  query the same series without importing code from here. One Parquet file
  per series isn't a reasonable consumption interface for multiple
  consumers.
- **Decision:** the analytics layer becomes a Postgres table
  (`series_vintage`), local via `docker-compose.yml`. The raw zone
  (`raw.py`) doesn't change — it stays immutable JSON on disk.
- **Alternatives:** keep Parquet and let each consuming project read the
  file directly — couples consumers to this repository's disk layout, and
  doesn't solve write concurrency once Airflow enters the picture.
- **Consequences:** the gain is a real data interface (`DSN` + schema)
  instead of a file path; the cost is depending on Postgres running (local
  via Docker) even for tests, which now use `testcontainers` and require
  Docker on the machine running `pytest`. Revisit if series volume ever
  justifies swapping Postgres for something columnar.

### 2026-08-19 — Airflow with LocalExecutor, no local pytest DAG test

- **Context:** the next Postgres consumer needs scheduling, not just manual
  CLI runs. Airflow's executor options range from `SequentialExecutor` (a
  single worker, no real parallelism) to
  `CeleryExecutor`/`KubernetesExecutor` (distributed workers, requiring
  Redis/a broker and more services in the compose file).
- **Decision:** `LocalExecutor` — parallelizes tasks on a single machine
  without needing an external broker. The DAG (`dags/ingest_fred.py`) only
  orchestrates; the ingestion logic stays in `src/`, tested by `pytest`
  outside Airflow. The Airflow image is built locally
  (`docker/airflow/Dockerfile`) by `pip install`-ing this package, instead
  of mounting `src/` as a volume — the image stays self-contained and
  identical in dev and CI. I didn't add `apache-airflow` as a local test
  dependency: installing it natively on this dev environment's Windows would
  break the project's `uv sync` (Airflow isn't officially supported outside
  Linux/a container). Verifying that the DAG imports without error runs
  inside the container, in a separate CI job.
- **Alternatives:** `CeleryExecutor` — closer to real production, but adds
  Redis and workers for a data volume that doesn't need it yet. Installing
  `apache-airflow` in `pyproject.toml`'s `dev` group to test locally — I
  tried to avoid this because of how fragile the install is on Windows, and
  because the value of testing the DAG's structure outside the container is
  low compared to the cost of maintaining that heavy dependency.
- **Consequences:** the gain is real, testable orchestration with no
  external infrastructure beyond the Docker the project already requires;
  the cost is that any test of the DAG itself only runs inside a Linux
  container — if that ever becomes real development friction, revisit a
  native install via WSL2.

### 2026-08-19 — Move source contracts and ingestion into per-source modules

- **Context:** `contratos.py` and `ingestao.py` were "generic" files that
  only had FRED inside; that was going to become a file that grows per
  source, the opposite of what its name promised, right before a second
  source arrives.
- **Decision:** `FredObservation`/`FredResponse` moved into `sources/fred.py`
  (the contract lives next to the adapter that produces it);
  `ingest_fred` became `ingestion/fred.py` (a folder, one file per source,
  matching `sources/`'s pattern). `analytics.publish()` stopped importing
  `FredObservation` by name and instead requires a structural `Protocol`
  (`analytics.Observation`, four fields) — the layer that's genuinely
  source-agnostic can't depend on a type with a source's name in the middle.
  Rule recorded in the README: one file per source is the default; it
  becomes a folder (`sources/<source>/{__init__,contracts,...}.py`) once a
  source accumulates real complexity (multiple endpoints, non-trivial
  parsing, a large contract) — decided source by source, not all at once.
  `dags/` stays flat (`ingest_<source>.py`), Airflow's standard convention,
  no subfolder.
- **Alternatives:** none seriously considered — the file was already growing
  in the wrong direction and the second source was imminent.
- **Consequences:** more files for a single-source project today, but the
  next source (BCB SGS) adds `sources/bcb.py` and `ingestion/bcb.py` without
  touching FRED's files. Revisit only if the per-source split itself proves
  wrong once BCB is in.
