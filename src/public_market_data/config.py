"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings."""

    model_config = SettingsConfigDict(env_prefix="PUBLIC_MARKET_DATA_", extra="ignore")

    log_level: str = "INFO"
    data_dir: Path = Path("data")
    fred_api_key: str | None = None
    # No prefix on purpose: this is the same variable every other project in
    # the portfolio reads to reach this project's Postgres — one DSN
    # configures all of them, and the name predates this package's rename.
    postgres_dsn: str = Field(
        default="postgresql://dados:dados@localhost:5433/dados_mercado_publico",
        validation_alias=AliasChoices("DADOS_MERCADO_PUBLICO_POSTGRES_DSN"),
    )
