"""Conexão com a camada analítica em Postgres e garantia do schema."""

from pathlib import Path

import psycopg

_SCHEMA = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


def conectar(dsn: str) -> psycopg.Connection:
    """Abre a conexão e garante o schema antes de devolvê-la.

    `CREATE TABLE IF NOT EXISTS` é idempotente: repetir a conexão em toda
    execução do CLI não tem custo de migração para uma tabela só.
    """
    conexao = psycopg.connect(dsn, autocommit=True)
    conexao.execute(_SCHEMA)
    return conexao
