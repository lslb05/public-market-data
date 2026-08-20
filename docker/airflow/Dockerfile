FROM apache/airflow:2.10.5-python3.12

COPY --chown=airflow:root pyproject.toml README.md /opt/public_market_data/
COPY --chown=airflow:root src /opt/public_market_data/src

RUN pip install --no-cache-dir /opt/public_market_data
