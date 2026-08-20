-- Runs only on the volume's first initialization: creates Airflow's metadata
-- database separate from the application database (dados_mercado_publico),
-- which the image's POSTGRES_DB already creates.
CREATE DATABASE airflow;
