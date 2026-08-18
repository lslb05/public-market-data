"""Zona bruta: o que a fonte mandou, imutável, com o rastro de como veio."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Manifesto:
    fonte: str
    dataset: str
    url: str
    coletado_em: str
    versao_contrato: str
    sha256: str
    tamanho_bytes: int
    linhas: int


def gravar(
    raiz: Path,
    *,
    fonte: str,
    dataset: str,
    corpo: bytes,
    url: str,
    versao_contrato: str,
    linhas: int,
    coletado_em: datetime,
) -> Manifesto | None:
    """Grava uma coleta. Devolve None se o conteúdo é idêntico ao já guardado.

    A idempotência é por hash do corpo: reexecutar a ingestão sem que a fonte
    tenha mudado não cria partição nova.
    """
    digest = hashlib.sha256(corpo).hexdigest()
    pasta_dataset = raiz / fonte / dataset
    if _ja_guardado(pasta_dataset, digest):
        return None

    # Dois-pontos é ilegal em nome de arquivo no Windows, então o carimbo vai
    # compacto em vez de ISO 8601.
    particao = pasta_dataset / f"coleta={coletado_em.strftime('%Y%m%dT%H%M%SZ')}"
    particao.mkdir(parents=True, exist_ok=True)
    (particao / "dados.json").write_bytes(corpo)

    manifesto = Manifesto(
        fonte=fonte,
        dataset=dataset,
        url=url,
        coletado_em=coletado_em.isoformat(),
        versao_contrato=versao_contrato,
        sha256=digest,
        tamanho_bytes=len(corpo),
        linhas=linhas,
    )
    (particao / "manifesto.json").write_text(
        json.dumps(asdict(manifesto), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifesto


def _ja_guardado(pasta_dataset: Path, digest: str) -> bool:
    for arquivo in pasta_dataset.glob("coleta=*/manifesto.json"):
        if json.loads(arquivo.read_text(encoding="utf-8"))["sha256"] == digest:
            return True
    return False
