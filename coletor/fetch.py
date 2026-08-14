# -*- coding: utf-8 -*-
"""Coletor do Clipping LETS — as 22 fontes, configuradas em sources.yml.

Roda igual no Windows e no macOS/Linux.

    python -m coletor.fetch                  # coleta tudo
    python -m coletor.fetch --dias 3         # mantem 3 dias no recorte
    python -m coletor.fetch --fonte senado   # depura uma fonte
    python -m coletor.fetch --validar        # so testa as URLs, nao grava nada

Grava data/noticias.json e data/noticias.js (este ultimo para o index.html
poder ler via <script src>, ja que fetch() nao funciona em file://).
"""

import argparse
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Windows: garante UTF-8 no terminal (cp1252 quebra com acento)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    print("Faltam dependências. Rode:  pip install -r requirements.txt")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relevancia  # noqa: E402
import parsers      # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
LOG = DATA / "coleta.log"

FUSO_BR = timezone(timedelta(hours=-3))


def carregar_fontes():
    fontes = yaml.safe_load((RAIZ / "sources.yml").read_text(encoding="utf-8"))
    fontes.sort(key=lambda f: f["ordem"])
    return fontes


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------

def coletar(fontes, agora):
    noticias, status = [], []

    for f in fontes:
        try:
            itens = parsers.coletar_fonte(f)
            for titulo, link, resumo, quando, estimada in itens:
                score, tags = relevancia.calcular(titulo, resumo)
                noticias.append({
                    "id": hashlib.sha1(link.encode("utf-8")).hexdigest()[:16],
                    "fonte_id": f["id"],
                    "fonte_nome": f["nome"],
                    "titulo": titulo,
                    "link": link,
                    "resumo": resumo,
                    "publicado_em": quando.isoformat(timespec="seconds"),
                    "dia": quando.date().isoformat(),
                    "data_estimada": estimada,
                    "score": score,
                    "tags": tags,
                    "coletado_em": agora.isoformat(timespec="seconds"),
                })
            status.append({"id": f["id"], "status": "ok" if itens else "instavel",
                           "itens": len(itens),
                           "erro": None if itens else "0 itens — verifique o parser"})
            print(f"  {f['nome']:<24} {len(itens):>3} itens")
        except Exception as e:      # noqa: BLE001
            status.append({"id": f["id"], "status": "falhou", "itens": 0, "erro": str(e)[:200]})
            print(f"  {f['nome']:<24}  falhou: {str(e)[:90]}")

    return noticias, status


def mesclar(novas, dias_manter):
    """Junta com o historico, deduplica por id e descarta o que passou da janela."""
    antigo = {}
    arq = DATA / "noticias.json"
    if arq.exists():
        try:
            for n in json.loads(arq.read_text(encoding="utf-8")).get("noticias", []):
                antigo[n["id"]] = n
        except (ValueError, KeyError):
            pass
    for n in novas:
        if n["id"] in antigo:
            n["coletado_em"] = antigo[n["id"]]["coletado_em"]   # preserva o 1o avistamento
        antigo[n["id"]] = n

    corte = (datetime.now(FUSO_BR) - timedelta(days=dias_manter)).date().isoformat()
    saida = [n for n in antigo.values() if n["dia"] >= corte]
    saida.sort(key=lambda n: (n["dia"], n["fonte_id"], n["publicado_em"]), reverse=True)
    return saida


def gravar(noticias, status, fontes, agora):
    dados = {
        "gerado_em": agora.isoformat(timespec="seconds"),
        "modo": f"{len(fontes)} de 22 fontes",
        "limite_alta_relevancia": relevancia.ALTA_RELEVANCIA,
        "base_relevancia": relevancia.BASE,
        "fontes": [{"id": f["id"], "nome": f["nome"], "ordem": f["ordem"]} for f in fontes],
        "fontes_status": status,
        "noticias": noticias,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    corpo = json.dumps(dados, ensure_ascii=False, indent=2)
    (DATA / "noticias.json").write_text(corpo, encoding="utf-8")
    (DATA / "noticias.js").write_text("window.DADOS = " + corpo + ";\n", encoding="utf-8")
    with io.open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{dados['gerado_em']}  {len(noticias)} notícias  "
                 f"ok={sum(1 for s in status if s['status'] == 'ok')}/{len(status)}\n")
    _forcar_recarga_dados(agora)
    return dados


def _forcar_recarga_dados(agora):
    """Troca o ?v= do <script src="data/noticias.js?v=N"> do index.html pelo
    timestamp desta coleta, pra navegador nao servir noticias.js do cache
    quando alguem so recarrega a aba (importa sobretudo na versao hospedada;
    em file:// nao atrapalha)."""
    alvo = RAIZ / "index.html"
    if not alvo.exists():
        return
    html = alvo.read_text(encoding="utf-8")
    novo = re.sub(r'(data/noticias\.js\?v=)\d+', rf'\g<1>{int(agora.timestamp())}', html)
    if novo != html:
        alvo.write_text(novo, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Coletor do Clipping LETS")
    ap.add_argument("--dias", type=int, default=90, help="dias de histórico a manter")
    ap.add_argument("--fonte", help="coletar apenas esta fonte (id)")
    ap.add_argument("--validar", action="store_true", help="só testa as URLs, não grava")
    a = ap.parse_args()

    todas = carregar_fontes()
    fontes = [f for f in todas if not a.fonte or f["id"] == a.fonte]
    if not fontes:
        print(f"Fonte '{a.fonte}' não existe. Opções: " + ", ".join(f["id"] for f in todas))
        return 1

    agora = datetime.now(FUSO_BR)

    print(f"Coletando {len(fontes)} fonte(s)…")
    noticias, status = coletar(fontes, agora)

    if a.validar:
        print("\n--- validação (nada foi gravado) ---")
        for s in status:
            print(f"  {s['id']:<20} {s['status']:<9} {s['itens']:>3}  {s['erro'] or ''}")
        return 0 if all(s["status"] == "ok" for s in status) else 2

    dados = gravar(mesclar(noticias, a.dias), status, todas, agora)
    print(f"\n{len(dados['noticias'])} notícias no total em {DATA / 'noticias.json'}")

    # alerta de Receita Federal
    try:
        import alerta_rfb
        alerta_rfb.verificar(dados)
    except Exception as e:      # noqa: BLE001
        print(f"(alerta RFB não rodou: {e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
