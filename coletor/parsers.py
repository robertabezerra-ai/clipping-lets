# -*- coding: utf-8 -*-
"""Um parser por estratégia declarada em sources.yml.

Cada parser recebe o dicionário da fonte (uma entrada de sources.yml) e
devolve uma lista de tuplas (titulo, link, resumo, quando, estimada).

estimada=True quando só achamos o dia, sem hora (a hora vira meio-dia) —
isso não significa que o dia esteja errado, só que a hora é um chute.

Regra de ouro (INSTRUCAO §4): um seletor que quebra não pode derrubar a
coleta inteira. Cada request individual tem timeout, 2 retries com
backoff e no máximo 1 requisição por segundo por domínio; quem decide se
a fonte falhou é fetch.py, não este módulo.
"""

import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup

FUSO_BR = timezone(timedelta(hours=-3))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT = 20

_ultima_req = {}


def baixar(url, aceita_json=False):
    """GET com User-Agent real, 2 retries e no máximo 1 req/s por domínio."""
    dominio = re.sub(r"^https?://([^/]+).*", r"\1", url)
    espera = 1.0 - (time.time() - _ultima_req.get(dominio, 0))
    if espera > 0:
        time.sleep(espera)
    cabecalhos = {"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"}
    if aceita_json:
        cabecalhos["Accept"] = "application/json"
    erro = None
    for tentativa in range(3):
        try:
            r = requests.get(url, headers=cabecalhos, timeout=TIMEOUT)
            _ultima_req[dominio] = time.time()
            r.raise_for_status()
            if not aceita_json:
                r.encoding = r.apparent_encoding or "utf-8"
            return r
        except Exception as e:                    # noqa: BLE001
            erro = e
            time.sleep(2 ** tentativa)
    raise RuntimeError(f"falhou após 3 tentativas: {erro}")


# ---------------------------------------------------------------------------
# Normalização de link — para deduplicar sem perder identidade
# ---------------------------------------------------------------------------

# só remove parâmetro de rastreamento; parâmetros de identidade (ex.:
# codigoNoticia do TJSP) continuam no link normalizado
TRACKING_QS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
               "utm_content", "fbclid", "gclid", "ref", "amp"}


def normalizar_link(link):
    partes = urlsplit(link)
    qs = [(k, v) for k, v in parse_qsl(partes.query, keep_blank_values=True)
          if k.lower() not in TRACKING_QS]
    return urlunsplit((partes.scheme, partes.netloc, partes.path,
                        urlencode(qs), ""))


# ---------------------------------------------------------------------------
# Extração de data em texto livre (scraping)
# ---------------------------------------------------------------------------

RE_DATA_HORA = re.compile(r"(\d{2})/(\d{2})/(\d{4})\D{0,4}(\d{1,2})[h:](\d{2})")
RE_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}
RE_DATA_EXTENSA = re.compile(
    r"(\d{1,2})\s+de\s+([a-zçã]+)\s+de\s+(\d{4})", re.IGNORECASE)


def _sem_acento(s):
    t = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def data_no_texto(txt):
    """dd/mm/aaaa[ hh:mm] em texto livre. Retorna (datetime, estimada)."""
    m = RE_DATA_HORA.search(txt)
    if m:
        d, mo, a, h, mi = m.groups()
        try:
            return datetime(int(a), int(mo), int(d), int(h), int(mi),
                             tzinfo=FUSO_BR), False
        except ValueError:
            return None, True
    m = RE_DATA.search(txt)
    if m:
        d, mo, a = m.groups()
        try:
            return datetime(int(a), int(mo), int(d), 12, 0,
                             tzinfo=FUSO_BR), True
        except ValueError:
            return None, True
    return None, True


def data_extensa_no_texto(txt):
    """'11 de agosto de 2026' em texto livre. Retorna (datetime, estimada)."""
    m = RE_DATA_EXTENSA.search(txt)
    if not m:
        return None, True
    d, mes_nome, a = m.groups()
    mes = MESES_PT.get(_sem_acento(mes_nome))
    if not mes:
        return None, True
    try:
        return datetime(int(a), mes, int(d), 12, 0, tzinfo=FUSO_BR), True
    except ValueError:
        return None, True


def _contexto(a, niveis=5):
    """Texto do elemento e de seus ancestrais — onde a data costuma estar."""
    partes, no = [], a
    for _ in range(niveis):
        if no is None:
            break
        partes.append(no.get_text(" ", strip=True))
        no = no.parent
    return " ".join(partes)


def _texto_limpo(html_ou_texto, limite=300):
    if not html_ou_texto:
        return ""
    texto = BeautifulSoup(html_ou_texto, "html.parser").get_text(" ", strip=True)
    return texto[:limite]


# ---------------------------------------------------------------------------
# scrape — varre <a href> da listagem, casa com padrao_link, lê data no
# contexto (ancestrais). Usado por a maioria das fontes sem feed.
# ---------------------------------------------------------------------------

def p_scrape(f):
    r = baixar(f["url"])
    sopa = BeautifulSoup(r.text, "html.parser")
    padrao = re.compile(f["padrao_link"])
    vistos, saida = set(), []
    for a in sopa.find_all("a", href=True):
        href = urljoin(f["url"], a["href"])
        if not padrao.search(href):
            continue
        # alguns sites (TJSP, Governo Federal/agenciagov) enrolam o card
        # inteiro — data, chapéu, título, resumo — num único <a>; se houver
        # um heading ou elemento com classe "titulo"/"title" dentro, o
        # título de verdade é o dele, não o texto inteiro do link
        titulo_el = (a.find(class_=re.compile(r"(?i)titulo|title"))
                     or a.find(["h1", "h2", "h3", "h4"]))
        titulo = (titulo_el or a).get_text(" ", strip=True)
        if len(titulo) < 15:
            continue
        chave = normalizar_link(href)
        if chave in vistos:
            continue
        quando, estimada = data_no_texto(_contexto(a))
        if quando is None:
            continue
        vistos.add(chave)
        resumo = ""
        if titulo_el is not None:
            # só conta como resumo um <p> comprido que não seja o próprio
            # título nem um chapéu/rótulo curto (ex.: "UC" no Governo Federal)
            for p in a.find_all("p"):
                if p is titulo_el:
                    continue
                texto_p = p.get_text(" ", strip=True)
                if len(texto_p) > 40:
                    resumo = _texto_limpo(texto_p)
                    break
        saida.append((titulo, chave, resumo, quando, estimada))
    return saida


def p_scrape_css(f):
    """Scraping com seletores CSS (item/titulo/data) — caso do CNJ, cujo
    tema (Elementor) não expõe link + data + título em texto plano perto
    um do outro o bastante para o casamento genérico por regex funcionar."""
    r = baixar(f["url"])
    sopa = BeautifulSoup(r.text, "html.parser")
    sel = f["seletores"]
    saida = []
    for item in sopa.select(sel["item"]):
        a = item.select_one(sel["titulo"])
        d = item.select_one(sel["data"])
        if not a or not d:
            continue
        titulo = a.get_text(" ", strip=True)
        href = urljoin(f["url"], a.get("href", ""))
        if f.get("formato_data") == "extenso_pt":
            quando, estimada = data_extensa_no_texto(d.get_text(" ", strip=True))
        else:
            quando, estimada = data_no_texto(d.get_text(" ", strip=True))
        if not titulo or not href or quando is None:
            continue
        excerto = item.select_one(".elementor-post__excerpt")
        resumo = _texto_limpo(excerto.get_text(" ", strip=True)) if excerto else ""
        saida.append((titulo, normalizar_link(href), resumo, quando, estimada))
    return saida


# ---------------------------------------------------------------------------
# rss — RSS 2.0 padrão: <item><title>/<link>/<pubDate>[/<description>]
# ---------------------------------------------------------------------------

def p_rss(f):
    r = baixar(f["url"])
    raiz = ET.fromstring(r.content)
    saida = []
    for item in raiz.iter("item"):
        titulo = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        bruto = (item.findtext("pubDate") or "").strip()
        if not titulo or not link or not bruto:
            continue
        try:
            quando = parsedate_to_datetime(bruto)
        except (TypeError, ValueError):
            continue
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=FUSO_BR)
        resumo = _texto_limpo(item.findtext("description") or "")
        saida.append((titulo, normalizar_link(link), resumo,
                      quando.astimezone(FUSO_BR), False))
    return saida


# ---------------------------------------------------------------------------
# gov_br_rss — RSS 1.0/RDF dos portais gov.br clássicos (Plone)
# ---------------------------------------------------------------------------

NS_DC = "{http://purl.org/dc/elements/1.1/}"
NS_RSS1 = "{http://purl.org/rss/1.0/}"


def p_gov_br_rss(f):
    """O <rdf:RDF> declara xmlns="http://purl.org/rss/1.0/" como namespace
    padrão, então <item>/<title>/<link>/<description> exigem o prefixo
    completo no ElementTree — só dc:date e dc:type (Dublin Core) não. O
    mesmo feed devolve pastas e imagens do diretório junto com as
    notícias; só dc:type=collective.nitf.content é notícia de verdade."""
    r = baixar(f["url"])
    raiz = ET.fromstring(r.content)
    saida = []
    for item in raiz.iter(f"{NS_RSS1}item"):
        tipo = item.findtext(f"{NS_DC}type") or ""
        if tipo != "collective.nitf.content":
            continue
        titulo = (item.findtext(f"{NS_RSS1}title") or "").strip()
        link = (item.findtext(f"{NS_RSS1}link") or "").strip()
        bruto = (item.findtext(f"{NS_DC}date") or "").strip()
        if not titulo or not link or not bruto:
            continue
        try:
            quando = datetime.fromisoformat(bruto.replace("Z", "+00:00"))
        except ValueError:
            continue
        resumo = _texto_limpo(item.findtext(f"{NS_RSS1}description") or "")
        saida.append((titulo, normalizar_link(link), resumo,
                      quando.astimezone(FUSO_BR), False))
    return saida


# ---------------------------------------------------------------------------
# json_api — cada fonte tem um formato de JSON diferente
# ---------------------------------------------------------------------------

def p_json_stf(f):
    r = baixar(f["url"], aceita_json=True)
    saida = []
    for p in r.json():
        titulo = _texto_limpo(p.get("title", {}).get("rendered", ""), 500)
        link = p.get("link", "")
        bruto = p.get("date", "")
        if not titulo or not link or not bruto:
            continue
        try:
            quando = datetime.fromisoformat(bruto).replace(tzinfo=FUSO_BR)
        except ValueError:
            continue
        resumo = _texto_limpo(p.get("excerpt", {}).get("rendered", ""))
        saida.append((titulo, normalizar_link(link), resumo, quando, False))
    return saida


def p_json_anpd(f):
    r = baixar(f["url"], aceita_json=True)
    saida = []
    for it in r.json().get("items", []):
        titulo = (it.get("title") or "").strip()
        link = it.get("@id", "")
        bruto = it.get("effective", "")
        if not titulo or not link or not bruto:
            continue
        try:
            quando = datetime.fromisoformat(bruto.replace("Z", "+00:00"))
        except ValueError:
            continue
        resumo = _texto_limpo(it.get("description") or "")
        saida.append((titulo, normalizar_link(link), resumo,
                      quando.astimezone(FUSO_BR), False))
    return saida


def p_json_bacen(f):
    r = baixar(f["url"], aceita_json=True)
    saida = []
    for it in r.json().get("conteudo", []):
        titulo = (it.get("titulo") or "").strip()
        id_ = it.get("Id")
        bruto = it.get("dataPublicacao", "")
        if not titulo or id_ is None or not bruto:
            continue
        try:
            quando = datetime.fromisoformat(bruto.replace("Z", "+00:00"))
        except ValueError:
            continue
        link = f"https://www.bcb.gov.br/detalhenoticia/{id_}/nota"
        resumo = _texto_limpo(it.get("lead") or "")
        saida.append((titulo, normalizar_link(link), resumo,
                      quando.astimezone(FUSO_BR), False))
    return saida


JSON_POR_ID = {"stf": p_json_stf, "anpd": p_json_anpd, "bacen": p_json_bacen}

POR_ESTRATEGIA = {"rss": p_rss, "gov_br_rss": p_gov_br_rss, "scrape": p_scrape}


def coletar_fonte(f):
    """Ponto de entrada único: escolhe o parser pela estratégia declarada
    em sources.yml e tenta url_fallback se a principal vier vazia."""
    tentativas = [f]
    if f.get("url_fallback"):
        alt = dict(f)
        alt["url"] = f["url_fallback"]
        tentativas.append(alt)

    ultimo_erro = None
    for alvo in tentativas:
        try:
            if alvo["estrategia"] == "json_api":
                itens = JSON_POR_ID[f["id"]](alvo)
            elif alvo["estrategia"] == "scrape" and "seletores" in alvo:
                itens = p_scrape_css(alvo)
            elif alvo["estrategia"] in POR_ESTRATEGIA:
                itens = POR_ESTRATEGIA[alvo["estrategia"]](alvo)
            else:
                raise RuntimeError(f"estratégia desconhecida: {alvo['estrategia']}")
            if itens:
                return itens
            ultimo_erro = "respondeu, mas 0 itens reconhecidos"
        except Exception as e:                      # noqa: BLE001
            ultimo_erro = str(e)[:200]

    if ultimo_erro:
        raise RuntimeError(ultimo_erro)
    return []
