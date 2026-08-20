"""FRED/ALFRED adapter.

The API returns, per observation, the window during which that value was the
current reading. We request the full real-time window to receive every
vintage of the series, not just today's reading.
"""

import logging
import time
from datetime import date

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from public_market_data.errors import SourceError, SourceUnavailable, UnexpectedSchema

URL = "https://api.stlouisfed.org/fred/series/observations"
CONTRACT_VERSION = "fred.series.observations.v1"

_ATTEMPTS = 3
_TIMEOUT_S = 30.0

_log = logging.getLogger(__name__)


class FredObservation(BaseModel):
    """One series observation from ALFRED, as of the vintage it was published in.

    `publication_date` is when the value started being current for
    `event_date`, and `valid_until` is the last day it was the current
    reading. That pair is what lets us reconstruct what was known on a past
    date. These four fields are the structural contract
    `analytics.Observation` requires of every source.
    """

    # A new field in the payload is a schema change: ingestion needs to stop,
    # not slip past unnoticed into the analytics layer.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    event_date: date = Field(alias="date")
    publication_date: date = Field(alias="realtime_start")
    valid_until: date = Field(alias="realtime_end")
    value: float | None = Field(alias="value")

    @field_validator("value", mode="before")
    @classmethod
    def _dot_means_missing(cls, value: object) -> object:
        return None if value == "." else value


class FredResponse(BaseModel):
    # The envelope carries pagination and ordering that aren't our contract.
    model_config = ConfigDict(extra="ignore")

    observations: list[FredObservation]


def fetch(
    series: str,
    api_key: str,
    client: httpx.Client,
    wait_s: float = 1.0,
) -> tuple[bytes, list[FredObservation]]:
    """Returns the raw body and the validated observations.

    The raw body comes back too because the raw zone stores what the source
    sent, not our interpretation of it.
    """
    params = {
        "series_id": series,
        "api_key": api_key,
        "file_type": "json",
        # The full real-time window is what makes ALFRED return past
        # vintages instead of only the current one.
        "realtime_start": "1776-07-04",
        "realtime_end": "9999-12-31",
    }
    body = _get(params, client, wait_s)
    try:
        response = FredResponse.model_validate_json(body)
    except ValidationError as error:
        raise UnexpectedSchema(f"FRED payload's shape changed for {series}") from error
    return body, response.observations


def _get(params: dict[str, str], client: httpx.Client, wait_s: float) -> bytes:
    last: Exception | None = None
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            response = client.get(URL, params=params, timeout=_TIMEOUT_S)
        except httpx.TransportError as error:
            last = error
        else:
            if response.status_code < 400:
                return response.content
            # A 4xx is our fault — invalid key, nonexistent series. Retrying
            # won't fix it and still burns the rate limit.
            if response.status_code < 500:
                raise SourceError(f"FRED responded {response.status_code}")
            last = SourceError(f"FRED responded {response.status_code}")
        if attempt < _ATTEMPTS:
            _log.warning("attempt %d failed; retrying", attempt)
            time.sleep(wait_s * attempt)

    raise SourceUnavailable(f"FRED did not respond in {_ATTEMPTS} attempts") from last
