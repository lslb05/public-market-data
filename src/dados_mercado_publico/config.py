"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="DADOS_MERCADO_PUBLICO_", extra="ignore"
    )

    log_level: str = "INFO"
    dados_dir: Path = Path("data")
    fred_api_key: str | None = None
    # Aponta para o docker-compose deste repositório por padrão; sobrescreva
    # em produção via variável de ambiente.
    postgres_dsn: str = "postgresql://dados:dados@localhost:5433/dados_mercado_publico"
