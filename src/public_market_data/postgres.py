"""Connection to the analytics layer in Postgres, and schema enforcement."""

from pathlib import Path

import psycopg

_SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


def connect(dsn: str) -> psycopg.Connection:
    """Opens the connection and ensures the schema before returning it.

    `CREATE TABLE IF NOT EXISTS` is idempotent: repeating it on every CLI run
    has no migration cost for a single table.
    """
    connection = psycopg.connect(dsn, autocommit=True)
    connection.execute(_SCHEMA)
    return connection
