class SourceError(Exception):
    """Failed to obtain or interpret data from an external source."""


class SourceUnavailable(SourceError):
    """The source didn't respond within the retry limit."""


class UnexpectedSchema(SourceError):
    """The payload's shape changed. Ingestion stops instead of guessing."""
