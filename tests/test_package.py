import pytest

from public_market_data.config import Settings


def test_reads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_MARKET_DATA_LOG_LEVEL", "DEBUG")

    assert Settings().log_level == "DEBUG"
