# dados-mercado-publico

Ingestão de dados públicos de mercado que preserva **o que se sabia em cada
data**, para que análise histórica não use revisão futura.

## O problema

Série macroeconômica é revisada. FRED, BCB e IBGE entregam a leitura de hoje e
sobrescrevem a anterior sem deixar rastro. Um backtest construído sobre isso vê,
numa data de 2020, um PIB que só foi publicado em 2021 — e fica otimista por um
vazamento de informação futura que não aparece em log nenhum.

Este repositório guarda a safra: cada valor carrega quando passou a valer e até
quando foi a leitura corrente.

## Resultado

A mesma série, no mesmo período de referência, consultada em duas datas:

```console
$ uv run python -m dados_mercado_publico consultar --fonte fred --serie GDP --em 2020-05-01
data_evento,valor
2020-01-01,21561.139

$ uv run python -m dados_mercado_publico consultar --fonte fred --serie GDP --em 2020-06-01
data_evento,valor
2020-01-01,21481.367
```

O PIB do primeiro trimestre de 2020 valia 21.561,139 para quem olhasse em maio.
A revisão de 28/05 mudou o número para 21.481,367. Uma consulta em maio não
enxerga a revisão de junho — que é justamente o ponto.

A transcrição acima foi produzida com a fixture versionada em
`tests/fixtures/`, porque a coleta ao vivo exige chave do FRED. O caminho de
código é o mesmo; só a chamada HTTP é substituída.

## Problema e escopo

- **Usuário:** eu, e os projetos que consomem esta base — risco quantitativo e
  agente de research.
- **Decisão:** permite reconstruir uma série como ela era numa data passada,
  sem contaminar backtest com revisão posterior.
- **Entrada:** FRED/ALFRED, via API pública com chave gratuita. As séries são de
  domínio público; a documentação da API está em
  <https://fred.stlouisfed.org/docs/api/fred/>.
- **Fora de escopo:** modelo, sinal e backtest, que são outro repositório;
  dado intradiário; e qualquer fonte que exija credencial institucional.

## Arquitetura

```
Airflow (DAG ingestao_fred, @daily)
    │  chama dados_mercado_publico.ingestao.ingerir_fred
    ▼
API do FRED
    │  httpx, timeout e 3 tentativas
    ▼
contratos.py      Pydantic valida na fronteira; campo novo levanta erro
    │
    ├─► bruto.py       data/bruto/<fonte>/<serie>/coleta=<carimbo>/
    │                  dados.json (o que a fonte mandou, byte a byte)
    │                  manifesto.json (url, sha256, contrato, linhas)
    │
    └─► analitico.py   Postgres, tabela series_vintage
                       consulta por data de conhecimento
```

O DAG (`dags/ingestao_fred.py`) não duplica lógica: chama a mesma função que
o CLI chama. A única coisa que o Airflow adiciona é agendamento e retentativa
de orquestração — a idempotência e o tratamento de erro de fonte já existiam.

`series_vintage(fonte, serie, data_evento, data_publicacao, vigente_ate,
valor, data_disponibilidade)` é a interface pública deste projeto: qualquer
outro repositório lê dela via `DADOS_MERCADO_PUBLICO_POSTGRES_DSN`, sem
importar código daqui. Chave primária `(fonte, serie, data_evento,
data_publicacao)` — mesma chave de idempotência de sempre.

Três decisões que valem explicação:

**Três datas em toda linha.** `data_evento` é o período de referência,
`data_publicacao` é quando a fonte divulgou aquele valor, `data_disponibilidade`
é quando nós coletamos. O ALFRED devolve as duas primeiras em
`realtime_start`/`realtime_end`, e é esse par que a consulta usa.

**A data de coleta não filtra a consulta — para esta fonte.** O ALFRED publica a
janela real de vigência de cada safra, então ele é a autoridade. Fonte sem safra
é outra história: para o BCB SGS, que só devolve a leitura corrente, o instante
da nossa coleta passa a ser o único limite superior confiável. Essa diferença é
uma limitação real e está registrada aqui em vez de maquiada.

**Idempotência por hash do corpo.** Reexecutar a ingestão sem que a fonte tenha
mudado não cria partição nova nem duplica linha adiante. A chave da camada
analítica é `(fonte, serie, data_evento, data_publicacao)`, e a primeira
ocorrência vence, preservando quando aquele valor foi visto pela primeira vez —
é por isso que o Airflow pode reexecutar o DAG livremente sem duplicar dado.

## Executar localmente

Requisitos: Python 3.12, [`uv`](https://docs.astral.sh/uv/) e Docker (para o
Postgres local).

```bash
uv sync
cp .env.example .env      # e preencha a chave do FRED
docker compose up -d      # sobe o Postgres em localhost:5433
uv run python -m dados_mercado_publico ingerir --fonte fred --serie GDP
uv run python -m dados_mercado_publico consultar --fonte fred --serie GDP --em 2020-05-01
```

A chave do FRED é gratuita: <https://fredaccount.stlouisfed.org/apikeys>. Sem
ela o comando `ingerir` orienta e sai com código 2, em vez de estourar. Sem o
Postgres de pé, qualquer comando orienta e sai com código 2 da mesma forma.

O schema (`series_vintage`) é criado automaticamente na primeira conexão —
não há passo de migração separado.

### Airflow

`docker-compose.yml` também sobe o Airflow (`LocalExecutor`, sem
Celery/Redis — é a forma mais simples que ainda é um Airflow real, adequada
ao volume de um projeto de portfólio):

```bash
docker compose up -d              # postgres + airflow-init (uma vez) + scheduler
docker compose up -d airflow-webserver
```

UI em <http://localhost:8081> (usuário/senha `admin`/`admin`, criados pelo
`airflow-init`). O DAG `ingestao_fred` roda `@daily`; para disparar manualmente:

```bash
docker compose exec airflow-scheduler airflow dags trigger ingestao_fred
```

O metadado do Airflow vive num banco Postgres separado (`airflow`) no mesmo
servidor do `series_vintage` — dois bancos, uma instância, sem infra extra.

Verificação:

```bash
uv run python scripts/check.py     # formato, lint, tipos e teste
uv run python scripts/format.py    # aplica formatação e correções
```

## Como foi validado

12 testes, 92% de cobertura. O que eles fixam:

- consulta em data passada não enxerga revisão publicada depois;
- reingestão do mesmo conteúdo não duplica partição nem linha;
- a zona bruta guarda o corpo original byte a byte;
- o manifesto não contém a chave de API;
- campo novo no payload para a ingestão em vez de passar batido;
- `.` do FRED vira nulo, não zero;
- 4xx não é repetido; 5xx esgota três tentativas e vira erro nomeado.

## Limitações

- Uma fonte só. BCB SGS, CVM, SEC EDGAR e preço EOD são os próximos cortes —
  cada uma vira uma task nova no mesmo DAG ou um DAG próprio.
- O ALFRED expõe safras; nem toda fonte expõe. Onde não houver, o
  point-in-time será mais fraco e isso ficará documentado por fonte.
- `LocalExecutor`, não `CeleryExecutor`/`KubernetesExecutor`: paralelismo
  limitado a uma máquina. Suficiente para o volume de séries deste projeto;
  reveja se algum dia isso virar gargalo real.
- Postgres e Airflow locais via `docker-compose`; produção (credencial,
  backup, alta disponibilidade) fica para quando houver um ambiente real
  para hospedar.
