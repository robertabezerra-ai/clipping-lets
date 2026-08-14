# -*- coding: utf-8 -*-
"""Score de relevancia 0-100 para clipping juridico da LETS.

Regra: o score APENAS ordena e sinaliza. Nunca exclui nada. A decisao
final e sempre humana, na pagina de curadoria.

Os dicionarios ficam em relevancia.yml (raiz do projeto), nao aqui — o
time ajusta os pesos direto no YAML, sem mexer em codigo.
"""

import unicodedata
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent


def _carregar():
    dados = yaml.safe_load((RAIZ / "relevancia.yml").read_text(encoding="utf-8"))
    return dados["base"], dados["alta_relevancia"], dados["sobe"], dados["desce"]


BASE, ALTA_RELEVANCIA, SOBE, DESCE = _carregar()


def _normalizar(texto):
    """minusculas, sem acento — para casar os dicionarios."""
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def calcular(titulo, resumo=""):
    """Retorna (score 0-100, lista de termos que pesaram)."""
    alvo = _normalizar(f"{titulo} {resumo}")
    score = BASE
    tags = []
    for termo, peso in {**SOBE, **DESCE}.items():
        if termo in alvo:
            score += peso
            tags.append(termo)
    return max(0, min(100, score)), tags
