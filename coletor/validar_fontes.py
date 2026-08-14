# -*- coding: utf-8 -*-
"""Diagnóstico das 22 fontes do Clipping LETS.

Usa exatamente os mesmos parsers de coletor/parsers.py que o coletor de
verdade (fetch.py) usa — valida o caminho que roda em produção, não uma
implementação paralela. Só lê; não grava nada.

    python -m coletor.validar_fontes
    python -m coletor.validar_fontes --fonte cnj
"""

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    print("Faltam dependências. Rode:  pip install -r requirements.txt")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parsers  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def testar(f):
    try:
        itens = parsers.coletar_fonte(f)
    except Exception as e:                          # noqa: BLE001
        return "falhou", 0, None, str(e)[:200]
    if not itens:
        return "falhou", 0, None, "0 itens reconhecidos"
    mais_recente = max(quando for _, _, _, quando, _ in itens)
    return "ok", len(itens), mais_recente, None


def main():
    ap = argparse.ArgumentParser(description="Valida as URLs das 22 fontes")
    ap.add_argument("--fonte", help="valida só esta fonte (id)")
    a = ap.parse_args()

    fontes = yaml.safe_load((RAIZ / "sources.yml").read_text(encoding="utf-8"))
    fontes.sort(key=lambda f: f["ordem"])
    if a.fonte:
        fontes = [f for f in fontes if f["id"] == a.fonte]
        if not fontes:
            print(f"Fonte '{a.fonte}' não existe em sources.yml")
            return 1

    print(f"{'veículo':<24} {'status':<9} {'itens':>5}  {'mais recente':<22} url")
    print("-" * 100)
    oks = 0
    for f in fontes:
        status, n, mais_recente, erro = testar(f)
        oks += status == "ok"
        recente = mais_recente.strftime("%d/%m/%Y %Hh%M") if mais_recente else "—"
        print(f"{f['nome']:<24} {status:<9} {n:>5}  {recente:<22} {f['url']}")
        if erro:
            print(f"{'':<24} motivo: {erro}")

    print("-" * 100)
    print(f"{oks}/{len(fontes)} fontes ok  "
          f"(critério de aceite: pelo menos 18 de 22)")
    return 0 if oks >= 18 else 2


if __name__ == "__main__":
    sys.exit(main())
