"""Command-line interface. Logic lives in the package; this only coordinates."""

import argparse
import logging
import sys
from datetime import date

import httpx
import psycopg

from public_market_data.analytics import exists, query_at
from public_market_data.config import Settings
from public_market_data.errors import SourceError
from public_market_data.ingestion.fred import ingest_fred
from public_market_data.postgres import connect


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="public-market-data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="collects a series and publishes it")
    ingest.add_argument("--source", required=True, choices=["fred"])
    ingest.add_argument("--series", required=True)

    query = subparsers.add_parser("query", help="the series as it was on a date")
    query.add_argument("--source", required=True, choices=["fred"])
    query.add_argument("--series", required=True)
    query.add_argument("--at", required=True, type=date.fromisoformat)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    config = Settings()
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        connection = connect(config.postgres_dsn)
    except psycopg.OperationalError as error:
        print(f"could not connect to Postgres: {error}", file=sys.stderr)
        return 2

    try:
        if args.command == "ingest":
            if not config.fred_api_key:
                print(
                    "set PUBLIC_MARKET_DATA_FRED_API_KEY (free FRED key)",
                    file=sys.stderr,
                )
                return 2
            try:
                with httpx.Client() as client:
                    total = ingest_fred(
                        series=args.series,
                        api_key=config.fred_api_key,
                        root=config.data_dir,
                        client=client,
                        connection=connection,
                    )
            except SourceError as error:
                print(f"source failure: {error}", file=sys.stderr)
                return 1
            print(f"{total} rows in {args.series}")
            return 0

        if not exists(connection, source=args.source, series=args.series):
            print(f"series not ingested: {args.series}", file=sys.stderr)
            return 2
        frame = query_at(connection, source=args.source, series=args.series, at=args.at)
        # CSV instead of Polars' repr: the output is pipeable and doesn't
        # depend on the console being able to render box-drawing characters.
        print(frame.write_csv().rstrip())
        return 0
    finally:
        connection.close()
