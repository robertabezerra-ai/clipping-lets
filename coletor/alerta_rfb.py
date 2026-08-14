# -*- coding: utf-8 -*-
"""Alerta de publicação da Receita Federal.

Roda no fim de cada coleta. Compara os ids da RFB com o que já foi visto e,
se houver item novo, envia UM e-mail com todos eles.

Sem novidade => não envia nada. E-mail vazio treina o time a ignorar o alerta.

    python coletor/alerta_rfb.py --dry-run     # imprime, não envia
    python coletor/alerta_rfb.py               # envia de verdade
"""

import argparse
import json
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
ESTADO = DATA / "estado_rfb.json"
CONFIG = RAIZ / "config.local.yml"

ID_RFB = "receita_federal"
VERMELHO = "#D10A11"
CREME = "#EEE7D6"
PRETO = "#1D1D1B"


def _ler_config():
    """Le config.local.yml. Usa PyYAML se existir; senao, parser minimo."""
    if not CONFIG.exists():
        raise FileNotFoundError(
            f"crie {CONFIG.name} a partir de config.local.example.yml")
    texto = CONFIG.read_text(encoding="utf-8")
    try:
        import yaml
        return yaml.safe_load(texto)
    except ImportError:
        cfg, atual = {}, None
        for linha in texto.splitlines():
            if not linha.strip() or linha.lstrip().startswith("#"):
                continue
            if not linha.startswith(" "):
                atual = linha.split(":")[0].strip()
                cfg[atual] = {}
            elif ":" in linha:
                k, v = linha.split(":", 1)
                cfg[atual][k.strip()] = v.strip().strip('"').strip("'")
        return cfg


def _vistos():
    if ESTADO.exists():
        try:
            return set(json.loads(ESTADO.read_text(encoding="utf-8")).get("ids", []))
        except ValueError:
            pass
    return set()


def _gravar_vistos(ids):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps({
        "ids": sorted(ids),
        "ultimo_envio": datetime.now().isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def montar_email(novos):
    linhas = ""
    for n in novos:
        hora = n["publicado_em"][11:16].replace(":", "h")
        linhas += (
            f'<tr><td style="padding:10px 0;border-bottom:1px solid #ddd5c2">'
            f'<a href="{n["link"]}" style="color:{PRETO};font-size:15px;font-weight:600">'
            f'{n["titulo"]}</a><br>'
            f'<span style="color:#5c5c5a;font-size:12px">'
            f'publicado às {hora} · score de relevância {n["score"]}</span></td></tr>'
        )
    return (
        f'<div style="font-family:Calibri,Helvetica,Arial,sans-serif;background:{CREME};'
        f'padding:24px">'
        f'<div style="background:{VERMELHO};color:#fff;padding:14px 18px;font-size:16px;'
        f'font-weight:700">Receita Federal publicou {len(novos)} novidade(s)</div>'
        f'<table style="width:100%;background:#fff;padding:6px 18px;border-collapse:collapse">'
        f'{linhas}</table>'
        f'<p style="color:#5c5c5a;font-size:12px">Alerta automático do Clipping LETS · '
        f'{datetime.now().strftime("%d/%m/%Y às %H:%M")}</p></div>'
    )


def verificar(dados, dry_run=False):
    novos = [n for n in dados.get("noticias", [])
             if n["fonte_id"] == ID_RFB and n["id"] not in _vistos()]

    if not novos:
        print("Alerta RFB: nada novo a enviar.")
        return 0

    novos.sort(key=lambda n: n["publicado_em"], reverse=True)
    assunto = (f"[ALERTA RFB] {len(novos)} nova(s) publicação(ões) — "
               f"{datetime.now().strftime('%d/%m/%Y %H:%M')}")
    corpo = montar_email(novos)

    if dry_run:
        print("\n" + "=" * 68)
        print("ASSUNTO:", assunto)
        print("-" * 68)
        for n in novos:
            print(f"  • {n['titulo']}\n    {n['link']}")
        print("=" * 68)
        print(f"(dry-run: {len(corpo)} caracteres de HTML, nada enviado, "
              f"estado NÃO atualizado)")
        return len(novos)

    cfg = _ler_config()
    smtp = cfg["smtp"]
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = smtp["remetente"]
    destinatarios = cfg["alerta_rfb"]["destinatarios"]
    if isinstance(destinatarios, str):
        destinatarios = [d.strip() for d in destinatarios.strip("[]").split(",")]
    msg["To"] = ", ".join(destinatarios)
    msg.set_content("Seu cliente de e-mail não exibe HTML. Itens:\n\n" +
                    "\n".join(f"- {n['titulo']}\n  {n['link']}" for n in novos))
    msg.add_alternative(corpo, subtype="html")

    with smtplib.SMTP(smtp["host"], int(smtp["porta"]), timeout=30) as s:
        s.starttls()
        s.login(smtp["usuario"], smtp["senha"])
        s.send_message(msg)

    _gravar_vistos(_vistos() | {n["id"] for n in novos})
    print(f"Alerta RFB: e-mail enviado com {len(novos)} item(ns) para "
          f"{len(destinatarios)} destinatário(s).")
    return len(novos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="imprime em vez de enviar")
    a = ap.parse_args()
    arq = DATA / "noticias.json"
    if not arq.exists():
        print("Rode o coletor primeiro: python coletor/fetch.py")
        return 1
    verificar(json.loads(arq.read_text(encoding="utf-8")), dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
