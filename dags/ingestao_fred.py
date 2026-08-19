"""DAG diário: ingere as séries FRED configuradas e publica em series_vintage.

A lógica de ingestão vive em `dados_mercado_publico` (testada por `pytest`
fora do Airflow); este módulo só faz a orquestração.
"""

from __future__ import annotations

from datetime import datetime

import httpx
from airflow.decorators import dag, task

from dados_mercado_publico.config import Settings
from dados_mercado_publico.ingestao import ingerir_fred
from dados_mercado_publico.postgres import conectar

SERIES_FRED = ["GDP"]


@dag(
    dag_id="ingestao_fred",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["dados-mercado-publico", "fred"],
)
def ingestao_fred() -> None:
    @task
    def ingerir(serie: str) -> int:
        config = Settings()
        if not config.fred_api_key:
            raise RuntimeError("DADOS_MERCADO_PUBLICO_FRED_API_KEY não definida")

        conexao = conectar(config.postgres_dsn)
        try:
            with httpx.Client() as cliente:
                return ingerir_fred(
                    serie=serie,
                    chave=config.fred_api_key,
                    raiz=config.dados_dir,
                    cliente=cliente,
                    conexao=conexao,
                )
        finally:
            conexao.close()

    ingerir.expand(serie=SERIES_FRED)


ingestao_fred()
