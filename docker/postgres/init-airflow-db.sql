-- Executado só na primeira inicialização do volume: cria o banco de
-- metadados do Airflow separado do banco de dados da aplicação
-- (dados_mercado_publico), que o POSTGRES_DB da imagem já cria.
CREATE DATABASE airflow;
