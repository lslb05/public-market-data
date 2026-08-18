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
