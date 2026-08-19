CREATE TABLE IF NOT EXISTS series_vintage (
    fonte TEXT NOT NULL,
    serie TEXT NOT NULL,
    data_evento DATE NOT NULL,
    data_publicacao DATE NOT NULL,
    vigente_ate DATE NOT NULL,
    valor DOUBLE PRECISION,
    data_disponibilidade DATE NOT NULL,
    PRIMARY KEY (fonte, serie, data_evento, data_publicacao)
);

CREATE INDEX IF NOT EXISTS series_vintage_consulta
    ON series_vintage (fonte, serie, data_publicacao, vigente_ate);
