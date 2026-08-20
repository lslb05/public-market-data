# Contrato do projeto — Dados Mercado Publico

Leia o `CLAUDE.md` global e use este arquivo para o que é específico deste
repositório.

## Resultado do produto

- **Problema:** análise quantitativa exige saber o que estava disponível numa
  data passada, não a revisão de hoje. As fontes públicas de macro entregam a
  safra corrente e sobrescrevem o rastro anterior sem avisar, o que produz
  backtest otimista por vazamento de informação futura.
- **Usuário:** eu, e os projetos que consomem esta base — risco quantitativo e
  agente de research.
- **Saída verificável:** zona bruta particionada por coleta, com manifesto, e
  uma tabela Postgres (`series_vintage`) consultável por data de conhecimento.
  Uma consulta em data passada não enxerga revisão publicada depois dela.
- **Fonte de dados permitida:** FRED/ALFRED, BCB SGS, CVM Dados Abertos, SEC
  EDGAR, B3 COTAHIST e Stooq. Nenhum dado, metodologia ou credencial do
  trabalho, em nenhuma hipótese.
- **Menor corte ponta a ponta:** `ingerir --fonte fred --serie GDP` grava a zona
  bruta com manifesto e publica em `series_vintage`; `consultar --serie GDP --em
  2020-06-30` devolve o valor que era conhecido naquela data.
- **Fora de escopo:** modelo, sinal e backtest (isso é outro repositório);
  dado intradiário; e qualquer fonte que exija credencial institucional.
- **Interface pública:** `series_vintage` é o contrato para os projetos
  consumidores (risco quantitativo, agente de research). Eles leem via
  `DADOS_MERCADO_PUBLICO_POSTGRES_DSN`, nunca importam código deste
  repositório.

Não implemente enquanto um `PREENCHER` que altere o design continuar em aberto.

## Comandos

```bash
uv sync
uv run python scripts/format.py
uv run python scripts/check.py
```

## Regras locais

- O pacote é `dados_mercado_publico` e vive em `src/dados_mercado_publico`.
- Notebook importa de `src/`; código de produção nunca importa notebook.
- Configuração vem de ambiente por `Settings`.
- Preserve dado bruto e metadados temporais quando houver ingestão.
- Atualize este arquivo quando uma decisão estrutural mudar.

## Estilo

Código público, lido por gente. A regra é contenção — a lista completa está em
`AGENTS.md`, seção "Style", e vale igual para mim e para o Codex.

- Comentário explica *por quê*, nunca *o quê*. Se parafraseia a linha abaixo,
  apague; se a linha precisa de paráfrase, renomeie a variável.
- Docstring só onde a assinatura não basta (unidade, fuso, efeito colateral,
  o que levanta). Helper privado de três linhas não leva.
- Teste afirma comportamento que pode quebrar, não constante. Cobertura é
  consequência de testar o que importa, nunca meta a inflar.
- Não capture exceção que não sabe tratar; não abstraia com um único chamador.

## Autoria dos commits

Autor e committer são um só: o dono do repositório. Nenhum `Co-Authored-By:`,
nenhum trailer de sessão, nenhuma menção a Claude, Codex ou ferramenta. Não
altere `user.name` nem `user.email`.

## Estado da sessão

- **Decidido:** primeiro corte entregue — FRED/ALFRED da fonte à consulta
  point-in-time, com zona bruta imutável, manifesto e idempotência por hash.
  A consulta filtra pela janela de vigência da fonte, não pela data de coleta.
- **Decidido:** segundo corte entregue — a camada analítica trocou de
  Parquet/DuckDB para Postgres (`series_vintage`), local via
  `docker-compose.yml`. A idempotência passou a ser `ON CONFLICT DO NOTHING`
  na chave `(fonte, serie, data_evento, data_publicacao)`, em vez de dedup em
  memória. Testes usam Postgres efêmero via `testcontainers` — exigem Docker
  rodando na máquina que roda `pytest`.
- **Decidido:** terceiro corte entregue — orquestração via Airflow
  (`LocalExecutor`, sem Celery/Redis), imagem própria em
  `docker/airflow/Dockerfile` que instala este pacote, DAG `ingestao_fred`
  (`dags/ingestao_fred.py`) chamando `ingestao.ingerir_fred` — sem duplicar
  lógica. Metadado do Airflow em banco Postgres separado (`airflow`) na mesma
  instância do `series_vintage`. Testado subindo o stack de verdade
  (`docker compose build/up`) e confirmando `airflow dags list-import-errors`
  vazio e a task `ingerir` registrada — não há teste de unidade local do DAG
  porque instalar `apache-airflow` nativamente no ambiente de dev (Windows)
  quebraria o `uv sync` do projeto; o CI valida isso num job separado
  (`airflow-dag` em `.github/workflows/ci.yml`) que builda a imagem e roda
  `airflow dags list-import-errors` dentro do container.
- **Decidido:** quarto corte — reorganização por fonte, antes da 2ª fonte
  chegar. `contratos.py` e `ingestao.py` eram arquivos "genéricos" que só
  tinham FRED dentro; isso ia virar um arquivo crescendo por fonte, o
  inverso do que o nome prometia. `ObservacaoFred`/`RespostaFred` foram pra
  dentro de `fontes/fred.py` (o contrato mora junto do adaptador que o
  produz); `ingerir_fred` virou `ingestao/fred.py` (pasta, um arquivo por
  fonte, mesmo padrão de `fontes/`). `analitico.publicar()` parou de
  importar `ObservacaoFred` pelo nome e passou a exigir um `Protocol`
  estrutural (`analitico.Observacao`, quatro campos) — a camada
  verdadeiramente agnóstica de fonte não pode depender de um tipo com nome
  de fonte no meio. Regra registrada no README: arquivo por fonte é o
  padrão; vira pasta (`fontes/<fonte>/{__init__,contratos,...}.py`) quando a
  fonte acumular complexidade real (múltiplos endpoints, parsing não
  trivial, contrato grande) — decidido fonte a fonte, não de uma vez.
  `dags/` continua flat (`ingestao_<fonte>.py`), convenção padrão do
  Airflow, sem subpasta.
- **Pendente:** chave gratuita do FRED para a coleta ao vivo; os testes rodam
  offline com fixture versionada e não dependem dela.
- **Próximo passo:** BCB SGS — a fonte sem safra, que força o limite via
  `data_disponibilidade` a ser explícito. Primeiro teste real da convenção
  por fonte: `fontes/bcb.py`, `ingestao/bcb.py`, `dags/ingestao_bcb.py`, e
  `cli.py` ganha `"bcb"` nas choices de `--fonte`.

