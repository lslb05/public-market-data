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
- **Saída verificável:** Parquet bruto particionado por coleta, com manifesto, e
  uma tabela DuckDB consultável por data de conhecimento. Uma consulta em data
  passada não enxerga revisão publicada depois dela.
- **Fonte de dados permitida:** FRED/ALFRED, BCB SGS, CVM Dados Abertos, SEC
  EDGAR, B3 COTAHIST e Stooq. Nenhum dado, metodologia ou credencial do
  trabalho, em nenhuma hipótese.
- **Menor corte ponta a ponta:** `ingerir --fonte fred --serie GDP` grava a zona
  bruta com manifesto e constrói a tabela analítica; `consultar --serie GDP --em
  2020-06-30` devolve o valor que era conhecido naquela data.
- **Fora de escopo:** modelo, sinal e backtest (isso é outro repositório);
  orquestrador, que entra num corte posterior; Postgres; dado intradiário; e
  qualquer fonte que exija credencial institucional.

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
- **Pendente:** chave gratuita do FRED para a coleta ao vivo; os testes rodam
  offline com fixture versionada e não dependem dela.
- **Próximo passo:** BCB SGS — a fonte sem safra, que força o limite via
  `data_disponibilidade` a ser explícito.

