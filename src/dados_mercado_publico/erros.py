class ErroDeFonte(Exception):
    """Falha ao obter ou interpretar dado de uma fonte externa."""


class FonteIndisponivel(ErroDeFonte):
    """A fonte não respondeu dentro do limite de tentativas."""


class SchemaInesperado(ErroDeFonte):
    """O payload mudou de forma. A ingestão para em vez de adivinhar."""
