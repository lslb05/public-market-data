"""Interface de linha de comando. A lógica vive no pacote; aqui só coordena."""

import argparse
import logging
import sys
from datetime import date

import httpx

from dados_mercado_publico.analitico import consultar_em
from dados_mercado_publico.config import Settings
from dados_mercado_publico.erros import ErroDeFonte
from dados_mercado_publico.ingestao import ingerir_fred


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    principal = argparse.ArgumentParser(prog="dados-mercado-publico")
    comandos = principal.add_subparsers(dest="comando", required=True)

    ingerir = comandos.add_parser("ingerir", help="coleta uma série e publica")
    ingerir.add_argument("--fonte", required=True, choices=["fred"])
    ingerir.add_argument("--serie", required=True)

    consultar = comandos.add_parser("consultar", help="a série como era em uma data")
    consultar.add_argument("--fonte", required=True, choices=["fred"])
    consultar.add_argument("--serie", required=True)
    consultar.add_argument("--em", required=True, type=date.fromisoformat)

    return principal.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argumentos = _argumentos(argv)
    config = Settings()
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if argumentos.comando == "ingerir":
        if not config.fred_api_key:
            print(
                "defina DADOS_MERCADO_PUBLICO_FRED_API_KEY (chave gratuita do FRED)",
                file=sys.stderr,
            )
            return 2
        try:
            with httpx.Client() as cliente:
                total = ingerir_fred(
                    serie=argumentos.serie,
                    chave=config.fred_api_key,
                    raiz=config.dados_dir,
                    cliente=cliente,
                )
        except ErroDeFonte as erro:
            print(f"falha na fonte: {erro}", file=sys.stderr)
            return 1
        print(f"{total} linhas em {argumentos.serie}")
        return 0

    parquet = (
        config.dados_dir
        / "analitico"
        / argumentos.fonte
        / f"{argumentos.serie}.parquet"
    )
    if not parquet.exists():
        print(f"série não ingerida: {argumentos.serie}", file=sys.stderr)
        return 2
    quadro = consultar_em(parquet, serie=argumentos.serie, em=argumentos.em)
    # CSV em vez do repr do Polars: a saída é pipeável e não depende do
    # console conseguir codificar os caracteres de desenho de caixa.
    print(quadro.write_csv().rstrip())
    return 0
