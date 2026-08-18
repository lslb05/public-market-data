"""Contratos dos payloads externos, validados na fronteira de entrada."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ObservacaoFred(BaseModel):
    """Uma observacao de serie do ALFRED, na safra em que foi publicada.

    `data_publicacao` e quando o valor passou a valer para `data_evento`, e
    `vigente_ate` e o ultimo dia em que ele foi a leitura corrente. E esse par
    que permite reconstruir o que se sabia numa data passada.
    """

    # Campo novo no payload e mudanca de schema: precisa parar a ingestao, nao
    # passar despercebido para dentro da camada analitica.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    data_evento: date = Field(alias="date")
    data_publicacao: date = Field(alias="realtime_start")
    vigente_ate: date = Field(alias="realtime_end")
    valor: float | None = Field(alias="value")

    @field_validator("valor", mode="before")
    @classmethod
    def _ponto_significa_ausente(cls, valor: object) -> object:
        return None if valor == "." else valor


class RespostaFred(BaseModel):
    # O envelope carrega paginacao e ordenacao que nao sao contrato nosso.
    model_config = ConfigDict(extra="ignore")

    observations: list[ObservacaoFred]
