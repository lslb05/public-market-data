# Decisões

Registre somente decisões que alterem custo de mudança futuro.

## Modelo

### AAAA-MM-DD — Título

- **Contexto:** qual restrição ou problema exigiu decisão.
- **Decisão:** o caminho escolhido.
- **Alternativas:** opções relevantes descartadas.
- **Consequências:** ganhos, custos e gatilho para revisar.

### 2026-08-18 — Manter `CLAUDE.md` e `AGENTS.md` no repositório público

- **Contexto:** os dois arquivos declaram que o repositório é construído com
  apoio de agentes. A alternativa era ignorá-los no git para que o repositório
  público não revelasse o fluxo de trabalho.
- **Decisão:** manter os dois versionados e públicos.
- **Alternativas:** ignorar `AGENTS.md` no `.gitignore`; mantê-lo apenas local.
  Ambas quebram a delegação ao Codex, que lê esse arquivo do repositório — o
  custo é funcional e imediato, o ganho é cosmético.
- **Consequências:** o repositório declara o método em vez de escondê-lo, o que
  também é verificável por quem lê. Rever se algum destino exigir o contrário.

### 2026-08-19 — Camada analítica migra de Parquet/DuckDB para Postgres

- **Contexto:** este repositório vai virar a fonte de dados de vários outros
  projetos de portfólio (nowcasting, crédito, vol/opções, IA), que precisam
  consultar as mesmas séries sem importar código daqui. Um Parquet por série
  não é uma interface de consumo razoável para múltiplos consumidores.
- **Decisão:** a camada analítica passa a ser uma tabela Postgres
  (`series_vintage`), local via `docker-compose.yml`. A zona bruta
  (`bruto.py`) não muda — continua JSON imutável em disco.
- **Alternativas:** manter Parquet e deixar cada projeto consumidor ler o
  arquivo diretamente — acopla os consumidores ao layout de disco deste
  repositório, e não resolve concorrência de escrita quando o Airflow entrar.
- **Consequências:** ganho é uma interface de dados real (`DSN` + schema)
  em vez de um caminho de arquivo; custo é depender de Postgres rodando
  (local via Docker) até para os testes, que agora usam `testcontainers` e
  exigem Docker na máquina que roda `pytest`. Rever se o volume de séries
  algum dia justificar trocar Postgres por algo colunar.

### 2026-08-19 — Airflow com LocalExecutor, sem testar o DAG via pytest local

- **Contexto:** o próximo consumidor do Postgres precisa de agendamento, não
  só de execução manual por CLI. As opções de executor do Airflow vão de
  `SequentialExecutor` (um único worker, sem paralelismo real) a
  `CeleryExecutor`/`KubernetesExecutor` (workers distribuídos, exige
  Redis/broker e mais serviços no compose).
- **Decisão:** `LocalExecutor` — paraleliza tasks numa única máquina sem
  precisar de um broker externo. O DAG (`dags/ingestao_fred.py`) só orquestra;
  a lógica de ingestão continua em `src/`, testada por `pytest` fora do
  Airflow. A imagem do Airflow é construída localmente
  (`docker/airflow/Dockerfile`) instalando este pacote via `pip install`, em
  vez de montar `src/` como volume — a imagem fica autocontida e igual em dev
  e CI. Não instalei `apache-airflow` como dependência de teste local: a
  instalação nativa no Windows deste ambiente de dev quebraria o `uv sync` do
  projeto (Airflow não é oficialmente suportado fora de Linux/contêiner). A
  verificação de que o DAG importa sem erro roda dentro do container, num job
  de CI separado.
- **Alternativas:** `CeleryExecutor` — mais próximo de produção real, mas
  adiciona Redis e workers para um volume de dados que não precisa disso
  ainda. Instalar `apache-airflow` no `dev` do `pyproject.toml` para testar
  localmente — tentei evitar por causa da fragilidade de instalação no
  Windows e porque o valor de testar a estrutura do DAG fora do container é
  baixo comparado ao custo de manter essa dependência pesada.
- **Consequências:** ganho é orquestração real, testável e sem infraestrutura
  externa além do Docker que o projeto já exige; custo é que qualquer teste
  do DAG em si só roda dentro de um container Linux — se um dia isso for uma
  fricção real de desenvolvimento, reveja a instalação nativa via WSL2.
