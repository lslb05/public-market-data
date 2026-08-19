FROM apache/airflow:2.10.5-python3.12

COPY --chown=airflow:root pyproject.toml README.md /opt/dados_mercado_publico/
COPY --chown=airflow:root src /opt/dados_mercado_publico/src

RUN pip install --no-cache-dir /opt/dados_mercado_publico
