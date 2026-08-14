# -*- coding: utf-8 -*-
"""Gera data/noticias.json e data/noticias.js com noticias REAIS coletadas
em 12/08/2026, para o prototipo poder ser aberto sem depender de rede.

Rodar: python coletor/seed_demo.py
Depois disso, o coletor de verdade (fetch.py) sobrescreve estes arquivos.
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relevancia  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"

# (fonte_id, fonte_nome, ordem)
FONTES = [
    ("stf", "STF", 1),
    ("senado", "Senado", 8),
    ("camara", "Câmara dos Deputados", 9),
    ("receita_federal", "Receita Federal", 10),
    ("cvm", "CVM", 14),
    ("congresso_em_foco", "Congresso em Foco", 22),
]

S = "https://www12.senado.leg.br/noticias"
C = "https://www.camara.leg.br/noticias"
R = "https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/agosto"

# (fonte_id, data_hora ISO, titulo, link)
ITENS = [
    # ---------------- 12/08/2026 ----------------
    ("senado", "2026-08-12T12:08:00", "Comissão aprova atualização das regras do ECA sobre educação básica",
     f"{S}/materias/2026/08/12/comissao-aprova-atualizacao-das-regras-do-eca-sobre-educacao-basica"),
    ("senado", "2026-08-12T12:01:00", "Faculdades deverão facilitar consulta sobre regularidade de cursos superiores",
     f"{S}/materias/2026/08/12/faculdades-deverao-facilitar-consulta-sobre-regularidade-de-cursos-superiores"),
    ("senado", "2026-08-12T11:58:00", "Subcomissão fará diligência à Comunidade Ianomâmi de Maturacá (AM)",
     f"{S}/materias/2026/08/12/subcomissao-fara-diligencia-a-comunidade-ianomami-de-maturaca-am"),
    ("senado", "2026-08-12T11:52:00", "Aumento de penas por maus-tratos a animais passa em primeiro turno na CCJ",
     f"{S}/materias/2026/08/12/aumento-de-penas-por-maus-tratos-a-animais-passa-em-primeiro-turno-na-ccj"),
    ("senado", "2026-08-12T11:40:00", "Criação da Comenda Niède Guidon é aprovada pela CCT",
     f"{S}/materias/2026/08/12/criacao-da-comenda-niede-guidon-e-aprovada-pela-cct"),
    ("senado", "2026-08-12T11:04:00", "Prazo de cinco anos para sanções a notários e registradores vai a Plenário",
     f"{S}/materias/2026/08/12/prazo-de-cinco-anos-para-sancoes-a-notarios-e-registradores-vai-a-plenario"),
    ("senado", "2026-08-12T10:01:00", "Proteção à pessoa com Síndrome de Tourette vai à sanção",
     f"{S}/audios/2026/08/protecao-a-pessoa-com-sindrome-de-tourette-vai-a-sancao"),
    ("senado", "2026-08-12T09:05:00", "Senado aprova fundos para fortalecer Justiça, Defensoria e MP",
     f"{S}/videos/2026/08/senado-aprova-fundos-para-fortalecer-justica-defensoria-e-mp"),
    ("senado", "2026-08-12T08:31:00", "Sargento Reginauro, suplente de Girão, toma posse no Senado",
     f"{S}/videos/2026/08/sargento-reginauro-suplente-de-girao-toma-posse-no-senado"),

    ("camara", "2026-08-12T08:40:00", "Comissão externa debate políticas de acolhimento para pessoas deslocadas por eventos ambientais",
     f"{C}/1295394-comissao-externa-debate-politicas-de-acolhimento-para-pessoas-deslocadas-por-eventos-ambientais"),
    ("camara", "2026-08-12T08:34:00", "Comissão da Câmara debate misoginia em escolas e universidades nesta quarta-feira; participe",
     f"{C}/1295855-comissao-da-camara-debate-misoginia-em-escolas-e-universidades-nesta-quarta-feira-participe"),
    ("camara", "2026-08-12T08:25:00", "Comissão de Educação debate proibição de licenciaturas 100% a distância",
     f"{C}/1295723-comissao-de-educacao-debate-proibicao-de-licenciaturas-100-a-distancia"),
    ("camara", "2026-08-12T08:21:00", "Comissão pode votar nesta quarta parecer sobre mudanças no Código de Trânsito",
     f"{C}/1295691-comissao-pode-votar-nesta-quarta-parecer-sobre-mudancas-no-codigo-de-transito"),
    ("camara", "2026-08-12T08:18:00", "Comissão da Mulher escolherá as agraciadas com o Diploma Mulher-Cidadã Carlota Pereira de Queirós 2026",
     f"{C}/1296299-comissao-da-mulher-escolhera-as-agraciadas-com-o-diploma-mulher-cidada-carlota-pereira-de-queiros-2026"),
    ("camara", "2026-08-12T08:16:00", "Comissão debate projeto que institui marco de fomento à economia digital no Brasil; participe",
     f"{C}/1295718-comissao-debate-projeto-que-institui-marco-de-fomento-a-economia-digital-no-brasil-participe"),
    ("camara", "2026-08-12T08:10:00", "Comissão debate classificação de facções brasileiras como organizações terroristas pelos Estados Unidos",
     f"{C}/1296148-comissao-debate-classificacao-de-faccoes-brasileiras-como-organizacoes-terroristas-pelos-estados-unidos"),

    ("receita_federal", "2026-08-12T10:30:00", "Receita Federal retém 36,5 quilos de cocaína em Paranaguá",
     f"{R}/receita-federal-retem-36-5-quilos-de-cocaina-em-paranagua"),

    # ---------------- 11/08/2026 (dia do e-mail de referencia) ----------------
    ("stf", "2026-08-11T14:22:00", "CNJ e Banco Central lançam iniciativa para ampliar segurança nas transferências de precatórios",
     "https://noticias.stf.jus.br/postsnoticias/cnj-e-banco-central-lancam-iniciativa-para-ampliar-seguranca-nas-transferencias-de-precatorios/"),

    ("senado", "2026-08-11T18:10:00", "Cinco medidas provisórias perdem validade e outras cinco são prorrogadas",
     f"{S}/materias/2026/08/11/cinco-medidas-provisorias-perdem-validade-e-outras-cinco-sao-prorrogadas"),
    ("senado", "2026-08-11T17:30:00", "Projeto fixa em 20 anos a prescrição de crimes sexuais contra crianças e adolescentes",
     f"{S}/audios/2026/08/projeto-fixa-em-20-anos-a-prescricao-de-crimes-sexuais-contra-criancas-e-adolescentes"),
    ("senado", "2026-08-11T16:45:00", "Suspensão do ITR sobre imóvel rural invadido vai à Câmara",
     f"{S}/materias/2026/08/11/suspensao-do-itr-sobre-imovel-rural-invadido-vai-a-camara"),
    ("senado", "2026-08-11T15:20:00", "Produção de energias renováveis no Brasil será discutida em Plenário",
     f"{S}/audios/2026/08/producao-de-energias-renovaveis-no-brasil-sera-discutida-em-plenario"),
    ("senado", "2026-08-11T14:05:00", "CAE aprova transição de três anos para novo piso de médicos e dentistas",
     f"{S}/materias/2026/08/11/cae-aprova-transicao-de-tres-anos-para-novo-piso-de-medicos-e-dentistas"),

    ("camara", "2026-08-11T20:32:00", "Ministério da Fazenda apresenta na Câmara medidas contra bets ilegais",
     f"{C}/1296642-ministerio-da-fazenda-apresenta-na-camara-medidas-contra-bets-ilegais"),
    ("camara", "2026-08-11T18:00:00", "Projeto cria regras para combater desinformação sobre clima",
     f"{C}/1296366-projeto-cria-regras-para-combater-desinformacao-sobre-clima"),
    ("camara", "2026-08-11T17:15:00", "Hugo Motta espera votar projeto que reduz impostos sobre combustíveis ainda hoje",
     f"{C}/1296567-hugo-motta-espera-votar-projeto-que-reduz-impostos-sobre-combustiveis-ainda-hoje"),
    ("camara", "2026-08-11T16:00:00", "Projeto reduz de dois anos para 12 meses intervalo para usar FGTS na quitação de financiamento imobiliário",
     f"{C}/1295066-projeto-reduz-de-dois-anos-para-12-meses-intervalo-para-usar-fgts-na-quitacao-de-financiamento-imobiliario"),
    ("camara", "2026-08-11T15:10:00", "Projeto prevê punição por improbidade para gestor que deixar de usar recursos disponíveis",
     f"{C}/1296023-projeto-preve-punicao-por-improbidade-para-gestor-que-deixar-de-usar-recursos-disponiveis"),

    # >>> Estes tres sairam no site da RFB em 11/08 e NAO entraram no e-mail daquele dia.
    ("receita_federal", "2026-08-11T16:40:00", "CGSN atualiza regras do Simples Nacional para adequação à Reforma Tributária do Consumo",
     f"{R}/cgsn-atualiza-regras-do-simples-nacional-para-adequacao-a-reforma-tributaria-do-consumo"),
    ("receita_federal", "2026-08-11T11:20:00", "Chat RFB passa a ser acessado pelo portal Serviços da Receita Federal",
     f"{R}/chat-rfb-passa-a-ser-acessado-pelo-portal-servicos-da-receita-federal"),
    ("receita_federal", "2026-08-11T09:15:00", "Medicamentos para emagrecer são encontrados em sola de tênis no Paraná",
     f"{R}/pisando-na-saude-medicamentos-para-emagrecer-sao-encontrados-em-sola-de-tenis-no-parana"),

    ("cvm", "2026-08-11T17:50:00", "CVM comunica determinação judicial referente à alienação de bens envolvendo cinco fundos de investimento",
     "https://www.gov.br/cvm/pt-br/assuntos/noticias/2026/cvm-comunica-determinacao-judicial-referente-a-alienacao-de-bens-envolvendo-cinco-fundos-de-investimento-1"),

    ("congresso_em_foco", "2026-08-11T19:00:00", "Hugo Motta diz que PL da Misoginia é \"urgente para o Brasil\"",
     "https://www.congressoemfoco.com.br/noticia/121181/hugo-motta-diz-que-pl-da-misoginia-e-urgente-para-o-brasil"),
    ("congresso_em_foco", "2026-08-11T16:30:00", "Ao menos 15 candidatos ao Senado escolhem parentes como suplentes",
     "https://www.congressoemfoco.com.br/noticia/121145/ao-menos-15-candidatos-ao-senado-escolhem-parentes-como-suplentes"),
    ("congresso_em_foco", "2026-08-11T14:00:00", "OAB avalia avanços na elaboração de propostas legislativas tributárias",
     "https://www.congressoemfoco.com.br/noticia/121166/oab-avalia-avancos-na-elaboracao-de-propostas-legislativas-tributarias"),

    # ---------------- 10/08 e 06/08 (para testar o filtro de dia) ----------------
    ("receita_federal", "2026-08-10T14:00:00", "Mais de 5 toneladas de camarão apreendidas em operação conjunta",
     f"{R}/mais-de-5-toneladas-de-camarao-apreendidas-em-operacao-conjunta"),
    ("receita_federal", "2026-08-06T15:30:00", "Receita Federal orienta sobre os procedimentos para o recolhimento do imposto de renda retido na fonte sobre lucros e dividendos",
     f"{R}/receita-federal-orienta-sobre-os-procedimentos-para-o-recolhimento-do-imposto-de-renda-retido-na-fonte-sobre-lucros-e-dividendos"),
    ("receita_federal", "2026-08-06T10:00:00", "Desistência de parcelamentos previdenciários (GFIP/SEFIP e GPS) já pode ser solicitada pelo e-CAC",
     f"{R}/desistencia-de-parcelamentos-previdenciarios-gfip-sefip-e-gps-ja-pode-ser-solicitada-pelo-e-cac"),
]


def main():
    nomes = {f[0]: f[1] for f in FONTES}
    noticias = []
    for fonte_id, dt, titulo, link in ITENS:
        score, tags = relevancia.calcular(titulo)
        noticias.append({
            "id": hashlib.sha1(link.encode("utf-8")).hexdigest()[:16],
            "fonte_id": fonte_id,
            "fonte_nome": nomes[fonte_id],
            "titulo": titulo,
            "link": link,
            "resumo": "",
            "publicado_em": f"{dt}-03:00",
            "dia": dt[:10],
            "score": score,
            "tags": tags,
            "coletado_em": datetime.now().isoformat(timespec="seconds"),
        })

    noticias.sort(key=lambda n: (n["dia"], n["fonte_id"], n["publicado_em"]), reverse=True)

    dados = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "modo": "protótipo — 6 de 22 fontes",
        "limite_alta_relevancia": relevancia.ALTA_RELEVANCIA,
        "fontes": [{"id": i, "nome": n, "ordem": o} for i, n, o in FONTES],
        "fontes_status": [
            {"id": "stf", "status": "instavel", "itens": 1,
             "erro": "site é SPA; exige scraping do endpoint interno"},
            {"id": "senado", "status": "ok", "itens": 14, "erro": None},
            {"id": "camara", "status": "ok", "itens": 11, "erro": None},
            {"id": "receita_federal", "status": "ok", "itens": 6, "erro": None},
            {"id": "cvm", "status": "ok", "itens": 1, "erro": None},
            {"id": "congresso_em_foco", "status": "ok", "itens": 3, "erro": None},
        ],
        "noticias": noticias,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "noticias.json").write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "noticias.js").write_text(
        "window.DADOS = " + json.dumps(dados, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8")
    print(f"{len(noticias)} notícias gravadas em {DATA}")
    for d in sorted({n['dia'] for n in noticias}, reverse=True):
        print(f"  {d}: {sum(1 for n in noticias if n['dia'] == d)} itens")


if __name__ == "__main__":
    main()
