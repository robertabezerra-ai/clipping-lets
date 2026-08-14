# Instrução para o Claude Code — "Clipping LETS"

> Cole este documento inteiro como primeira mensagem no Claude Code, dentro de uma pasta vazia.
> Anexe também os arquivos de referência listados em **§2**.

---

## 1. Objetivo

Construir uma ferramenta local que substitua o processo manual de montar o e-mail
**"Notícias diárias"** que a LETS Marketing envia para `consultores@letsmarketing.com.br`.

A ferramenta tem três partes:

1. **Coletor** — script que busca, uma vez por dia (ou sob demanda), as notícias publicadas
   por 22 veículos oficiais e as grava em JSON local.
2. **Página de curadoria** — HTML local onde o time filtra por dia, lê os títulos e
   **marca com checkbox** quais notícias entram no envio.
3. **Exportador Outlook** — botão que gera o HTML final do e-mail, no formato exato usado hoje,
   pronto para **copiar e colar no Outlook** (Ctrl+V preservando formatação).

Mais um requisito transversal: **alerta de Receita Federal** — sempre que a RFB publicar
qualquer coisa nova, destacar na página **e** disparar e-mail automático.

Não é um SaaS. Não precisa de login, deploy, banco de dados remoto ou multiusuário.
É uma ferramenta interna, roda no Mac da equipe.

---

## 2. Arquivos de referência anexados

| Arquivo | Para que serve |
|---|---|
| `ENC_ Notícias diárias _ 11_08_2026.eml` | **Fonte da verdade do formato do e-mail.** Extraia a parte `text/html` e replique a estrutura. |
| `Logos RGB.pdf` | Paleta oficial da marca LETS. |
| pasta `prototipo-clipping-lets/` | **Protótipo já funcionando com 6 das 22 fontes.** Use como ponto de partida: a página, o export para o Outlook e o alerta da RFB já estão prontos e testados. Sua tarefa é estender para as 22 fontes, não recomeçar. |

**Se o protótipo estiver anexado**, comece por ele: leia `index.html`, `coletor/fetch.py`,
`coletor/relevancia.py` e `coletor/alerta_rfb.py`, entenda as decisões já tomadas
e siga daí. Não reescreva o que já passa nos critérios de aceite.

**Antes de escrever qualquer código**, abra o `.eml`, extraia a parte `text/html`
e salve em `referencia/email-original.html`. Todo o §7 deve ser derivado desse arquivo,
não de suposições.

### Paleta LETS (extraída do PDF)

| Cor | HEX | RGB | Uso |
|---|---|---|---|
| Creme | `#EEE7D6` | 238, 231, 214 | fundo da página, faixas |
| Vermelho LETS | `#D10A11` | 209, 10, 17 | destaques, alertas, ações primárias |
| Preto LETS | `#1D1D1B` | 29, 29, 27 | texto, cabeçalhos |

Use **somente** essas três cores + branco e um cinza neutro derivado (`#6B6B69`) para texto secundário.

---

## 3. Arquitetura obrigatória

Coletor local em Python gerando JSON + página HTML estática que lê o JSON. **Sem backend rodando.**

```
coletor (python)  →  data/noticias.json  →  index.html (fetch local)  →  clipboard/HTML p/ Outlook
```

Motivo: elimina CORS, funciona offline, custo zero, o JSON é o histórico.

**Roda no Windows E no macOS.** O time usa os dois. Isso não é "nice to have" —
é requisito, e tem consequências concretas:

- **Nunca** monte caminho com `"pasta/" + nome`. Use `pathlib.Path` sempre.
- **Sempre** passe `encoding="utf-8"` em todo `open()`, `read_text()` e `write_text()`.
  O padrão do Windows é `cp1252` e vai quebrar em "Notícias", "Câmara", "Fazenda".
- No começo do `fetch.py`, force UTF-8 no terminal:
  `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.
  Sem isso o `print` de um título acentuado derruba o script no PowerShell.
- Zero `os.system`, `subprocess` com shell, `bash`, `curl`, `sed` ou barra invertida em path.
- Não use `feedparser` como dependência obrigatória — use `requests` + `BeautifulSoup`,
  que instalam sem compilador no Windows.
- No `README.md`, os comandos vão em **duas colunas: PowerShell e Terminal**.
  Windows usa `py -m venv .venv` e `.\.venv\Scripts\Activate.ps1`;
  macOS usa `python3 -m venv .venv` e `source .venv/bin/activate`.
- Fim de linha: crie um `.gitattributes` com `* text=auto` para não gerar ruído de CRLF.

**Regras:**
- Python 3.11+, dependências mínimas: `requests`, `beautifulsoup4`, `lxml`, `pyyaml`.
  Use `requirements.txt` e um `venv`. Não use frameworks web.
- A página é **um único arquivo `index.html`** com CSS e JS inline. Sem build, sem npm, sem React.
- Como `fetch()` de arquivo local é bloqueado no `file://`, resolva assim: o coletor grava
  `data/noticias.js` no formato `window.DADOS = {...};` e o `index.html` carrega via `<script src>`.
  Grave **também** `data/noticias.json` puro (para inspeção e para o script de alerta).
- Nada de `localStorage` como única fonte de verdade: as seleções do usuário podem ficar em
  `localStorage` para não perder ao recarregar, mas o export sempre lê o estado atual da tela.

### Estrutura de arquivos

```
clipping-lets/
├── README.md                  # como rodar, em português, 10 linhas
├── requirements.txt
├── sources.yml                # configuração das 22 fontes (§4)
├── coletor/
│   ├── fetch.py               # entrypoint: python -m coletor.fetch
│   ├── parsers.py             # 1 função por estratégia (rss, gov_br, scrape_*)
│   ├── relevancia.py          # classificação/score (§6)
│   ├── alerta_rfb.py          # detecção + envio de e-mail (§8)
│   └── validar_fontes.py      # diagnóstico das URLs (§4)
├── data/
│   ├── noticias.json          # acumulado histórico
│   ├── noticias.js            # mesmo conteúdo, envelopado em window.DADOS
│   └── estado_rfb.json        # hashes já vistos da RFB
├── referencia/
│   └── email-original.html
├── index.html                 # página de curadoria
├── coletar.bat                # atalho de duplo clique no Windows
├── .gitattributes             # * text=auto
└── config.local.yml           # SMTP e destinatários (no .gitignore)
```

---

## 4. As 22 fontes

Ordem **obrigatória** — é a ordem das linhas do e-mail e deve ser a ordem na página:

`STF, STJ, TST, TRT-2, TRT-15, TJSP, PGFN, Senado, Câmara dos Deputados, Receita Federal,
Ministério da Fazenda, ANPD, Anbima, CVM, Bacen, Coaf, Cade, CNJ, MJSP, CARF,
Governo Federal, Congresso em Foco`

### URLs confirmadas pelo e-mail de referência

Estes domínios aparecem nos links do envio de 11/08/2026 — são o alvo correto:

| Veículo | Domínio/padrão observado |
|---|---|
| STF | `noticias.stf.jus.br/postsnoticias/...` |
| TRT-2 | `ww2.trt2.jus.br/noticias/noticias/noticia/...` |
| TJSP | `tjsp.jus.br/Noticias/Noticia?codigoNoticia=...` |
| Senado | `www12.senado.leg.br/noticias/materias/...` e `/noticias/audios/...` |
| Câmara | `camara.leg.br/noticias/<id>-<slug>` |
| ANPD | `gov.br/anpd/pt-br/assuntos/noticias/...` |
| CVM | `gov.br/cvm/pt-br/assuntos/noticias/<ano>/...` |
| Bacen | `bcb.gov.br/detalhenoticia/<id>/nota` |
| Governo Federal | `agenciagov.ebc.com.br/noticias/<AAAAMM>/...` |
| Congresso em Foco | `congressoemfoco.com.br/noticia/<id>/<slug>` |

### Sua primeira tarefa técnica: descobrir e validar os feeds

**Não assuma URLs de RSS.** Escreva `coletor/validar_fontes.py` que, para cada veículo,
testa uma lista de candidatos e imprime uma tabela `veículo | url | status | nº de itens | data do item mais recente`.

Candidatos a testar, por estratégia:

- **Portais gov.br (Plone)** — RFB, Min. Fazenda, ANPD, CVM, Coaf, Cade, MJSP, CARF, PGFN:
  tente `<url-da-pasta-de-noticias>/RSS` e `.../@@rss`; se falhar, scraping da listagem.
- **WordPress** — CNJ, Congresso em Foco: tente `/feed/` e `/feed/?paged=1`.
- **Senado** — há RSS público de últimas notícias em `www12.senado.leg.br`; valide.
- **Câmara** — tem RSS de notícias **e** API de Dados Abertos (`dadosabertos.camara.leg.br`).
  Prefira o que retornar data de publicação confiável.
- **Bacen** — o site é SPA; procure o endpoint JSON que a própria página consome
  (inspecione as requisições de rede) antes de tentar scraping de HTML.
- **STF, STJ, TST, TRT-2, TRT-15, TJSP, Anbima, Agência Gov** — teste RSS; a maioria
  provavelmente exigirá **scraping da página de notícias**.

Registre o resultado em `sources.yml`, um bloco por veículo:

```yaml
- id: receita_federal
  nome: "Receita Federal"          # rótulo exato usado no e-mail
  ordem: 10
  estrategia: rss                  # rss | gov_br_rss | json_api | scrape
  url: "..."
  url_fallback: "..."              # usada se a principal falhar
  seletores:                       # só para estrategia: scrape
    item: "..."
    titulo: "..."
    link: "..."
    data: "..."
  alerta: true                     # apenas Receita Federal = true
  status_validacao: ok             # ok | instavel | falhou
```

**Regra de ouro do scraping:** um seletor CSS que quebra não pode derrubar a coleta inteira.
Cada fonte roda em `try/except` isolado, com `timeout=20`, 2 retries com backoff,
`User-Agent` de navegador real, e no máximo 1 requisição por segundo por domínio.
Falha de fonte gera aviso, não exceção.

---

## 5. Formato do dado coletado

`data/noticias.json`:

```json
{
  "gerado_em": "2026-08-12T18:30:00-03:00",
  "fontes_status": [
    {"id": "stf", "status": "ok", "itens": 4, "erro": null},
    {"id": "anbima", "status": "falhou", "itens": 0, "erro": "timeout"}
  ],
  "noticias": [
    {
      "id": "sha1 do link normalizado",
      "fonte_id": "stf",
      "fonte_nome": "STF",
      "titulo": "CNJ e Banco Central lançam iniciativa para ampliar segurança...",
      "link": "https://noticias.stf.jus.br/postsnoticias/...",
      "resumo": "primeiros 300 caracteres, se houver",
      "publicado_em": "2026-08-11T14:22:00-03:00",
      "dia": "2026-08-11",
      "score": 78,
      "tags": ["tributario", "precatorios"],
      "coletado_em": "2026-08-11T18:30:00-03:00"
    }
  ]
}
```

Requisitos do coletor:
- **Deduplicação por `id`** (SHA-1 do link sem querystring de tracking). Rodar 5x no mesmo dia
  não pode duplicar nada.
- **Acumula histórico**: nunca sobrescreve dias anteriores. Mantenha **90 dias**, descarte o resto.
- `dia` é derivado de `publicado_em` em `America/Sao_Paulo`. Se a fonte não expõe data,
  use a data da coleta e marque `"data_estimada": true`.
- Rode com `--dias N` (padrão 1) e `--fonte <id>` para depurar uma fonte só.
- Log em `data/coleta.log`, formato legível, sem stacktrace no stdout.

---

## 6. Curadoria: o que é "relevante" para clientes jurídicos da LETS

A LETS é consultoria de marketing jurídico. O time envia aos consultores o que **rende pauta e
posicionamento para escritórios de advocacia** — decisões, teses, mudanças normativas, prazos.
Notícia institucional/administrativa do órgão normalmente **não** entra.

Implemente em `relevancia.py` um **score 0–100** transparente e configurável em `sources.yml`,
que apenas **ordena e pré-sinaliza** — nunca exclui automaticamente. A decisão final é humana.

**Sobe o score** (termos indicativos, expandir na implementação):
decisão, julgamento, tese, repetitivo, repercussão geral, súmula, liminar, ADI/ADC/ADPF,
condenação, indenização, prescrição, precedente, instrução normativa, portaria, resolução,
medida provisória, projeto de lei aprovado, prazo, obrigatoriedade, multa, sanção,
reforma tributária, LGPD, compliance, recuperação judicial, trabalhista, concorrencial.

**Desce o score:**
posse, homenagem, aniversário, seminário interno, evento comemorativo, campanha de doação,
vaga de estágio, agenda do presidente, luto oficial, resultado esportivo.

Na página, marque com um selo discreto: `Alta relevância` (score ≥ 60), sem selo para o resto.
Deixe os dicionários em YAML para o time ajustar sem mexer em código.

---

## 7. Página de curadoria (`index.html`)

**Layout:** coluna única, largura máx. 1100px, fundo `#EEE7D6`, cartões brancos,
tipografia sistema (`-apple-system, Segoe UI, sans-serif`). Cabeçalho preto `#1D1D1B`
com o nome "Clipping LETS" e a data selecionada.

**Barra de controles (fixa no topo ao rolar):**
- Seletor de **dia** (`<input type="date">`) + botões `‹ Ontem` / `Hoje ›`. Padrão: hoje.
  Dias sem notícia mostram estado vazio explicativo, não tela branca.
- Busca por texto livre (filtra título em tempo real).
- Filtro por veículo (chips multi-seleção).
- Toggle `Só alta relevância`.
- Contador ao vivo: `X selecionadas de Y`.
- Botões: **`Gerar HTML para Outlook`** (primário, vermelho `#D10A11`) e `Copiar para a área de transferência`.

**Lista:** agrupada por veículo, **na ordem fixa do §4**, com o nome do veículo como cabeçalho
de seção. Veículo sem notícia no dia aparece com `Nada` em cinza — espelha o e-mail e deixa
claro que a fonte foi checada.

Cada notícia é uma linha com:
- `<input type="checkbox">` grande (alvo de toque ≥ 24px), rótulo clicável inteiro;
- título como link (`target="_blank" rel="noopener"`), hora de publicação;
- selo `Alta relevância` quando aplicável; selo `NOVO` para itens da última coleta.

**Atalhos:** `Espaço` marca/desmarca o item focado, `J`/`K` navegam, `Cmd+Enter` gera o HTML.
Foco visível em tudo (`:focus-visible`), navegável 100% por teclado.

**Persistência:** seleções e filtros em `localStorage`, com chave por dia
(`selecao:2026-08-11`), para poder fechar e voltar.

**Painel de saúde das fontes:** rodapé recolhível listando `fontes_status`. Fonte que falhou
aparece em vermelho — o time precisa saber que "Nada" pode ser "não coletado".

---

## 8. Exportação para o Outlook

O envio atual é uma tabela de bordas cinzas com 22 linhas, sendo 16 delas escritas “Nada”.
Funciona, mas o time lê um formulário, não um informativo. **O layout novo é o requisito** —
use o `referencia/email-original.html` apenas para entender o conteúdo e a ordem, não a aparência.

### Layout do e-mail (implementado e testado no protótipo)

Estrutura, de cima para baixo:

1. **Faixa preta** (`#1D1D1B`), com `Notícias diárias` em `#EEE7D6`, 19px, negrito, à esquerda,
   e a data `DD/MM/AAAA` em `#B9B2A2`, 13px, alinhada à direita.
2. **Régua vermelha** de 4px (`#D10A11`) logo abaixo — é o que dá a assinatura da marca.
3. **Linha de resumo** em cinza 11.5px: `10 notícias · 6 veículos`.
4. **Um bloco por veículo com notícia**, e só esses:
   - faixa clara (`#F7F3E9`) com **borda esquerda vermelha de 3px**, nome do veículo em
     `#D10A11`, 11px, negrito, **em maiúsculas**;
   - abaixo, cada notícia numa linha com bullet vermelho `▪` (`&#9642;`) na primeira célula
     de 16px e o título como link `#1D1D1B` sublinhado, 14px / `line-height:20px`,
     com `border-bottom:1px solid #DDD5C2` separando os itens.
5. **Rodapé creme** (`#EEE7D6`): `Sem novidades hoje: STJ · TST · TRT-15 · …` em 11.5px cinza.
   É assim que a informação dos 16 “Nada” continua presente sem ocupar 16 linhas.
6. **Receita Federal ganha destaque**: a faixa do veículo usa fundo `#FBE3E4` e prefixo `⚠ `
   (`&#9888;`). É o único veículo com tratamento diferente, e é intencional.

Largura `640px` (atributo `width="640"` **e** `style="width:640px;max-width:100%"`).
Fonte `Aptos,Aptos_EmbeddedFont,Aptos_MSFontService,Calibri,Helvetica,sans-serif`.

Mantenha o toggle **`Listar cada veículo sem novidade`** na página: desligado (padrão) resume no
rodapé; ligado volta a gerar um bloco por veículo com “Nada”, para quem preferir o formato antigo.

**Não** inclua assinatura — o Outlook insere a dele. O export termina no rodapé.

**Restrições técnicas de e-mail (não negociáveis).** O Outlook para Windows renderiza com o motor
do Word, não com um navegador:

- Zero CSS externo, zero `<style>`, zero classe, zero flexbox/grid, zero `position`,
  zero `border-radius`, zero imagem de fundo. Tudo inline, layout só com `<table>`.
- **`text-transform` não funciona** — o maiúsculo dos nomes de veículo tem que sair do código,
  com `toUpperCase()`.
- Toda `<table>` precisa de `role="presentation" cellpadding="0" cellspacing="0" border="0"`
  e de largura no atributo **e** no style, senão o Word estica.
- Espaçamento com `padding` em `<td>`. Nunca `margin` em `<div>`.
- `line-height` sempre explícito em px junto do `font-size`, senão o Word aplica o dele.
- Escapar `& < > "` nos títulos.
- Valide o resultado: `grep` no HTML gerado não pode encontrar `<style`, `class=`,
  `display:flex`, `display:grid` nem `border-radius`.

**Entrega em três formas, todas presentes:**
1. **Preview** renderizado num painel lateral/modal.
2. **`Copiar formatado`** — usa `ClipboardItem` com `text/html` **e** `text/plain`,
   para que o Ctrl+V no Outlook chegue com formatação. Fallback: `document.execCommand('copy')`
   sobre um elemento contenteditable. Teste os dois caminhos.
3. **`Baixar .html`** — salva `noticias-diarias-AAAA-MM-DD.html` (para abrir e copiar manualmente,
   ou anexar).

Inclua também um **`Copiar texto puro`** que gera a versão em lista simples
(`Veículo` / `- Título <link>`), útil para WhatsApp e para conferência.

---

## 9. Alerta de Receita Federal

Duas saídas, ambas obrigatórias.

**Na página — banner:**
- Banner no topo, fundo `#D10A11`, texto branco: `⚠ Receita Federal publicou N novidade(s) em DD/MM`,
  clicável, rola até a seção RFB. Esconde quando não há nada da RFB no dia.

**Na página — painel “quem recebe o alerta”** (requisito explícito da LETS):

Um `<details>` recolhível, visível acima da lista, com:

1. **Campo de texto para os destinatários**, aceitando vários endereços separados por vírgula
   ou ponto e vírgula. Placeholder com exemplo real:
   `laylla.cabral@letsmarketing.com.br, consultores@letsmarketing.com.br`.
2. Botão **`Salvar`** — grava numa variável em memória e espelha no `localStorage`
   (chave `clipping-lets:destinatarios-rfb`). Recarregar a página não perde o que foi digitado.
3. **Validação visível**: mostrar `✓ N destinatário(s) salvo(s): …` em verde, ou aviso em vermelho
   se nenhum endereço tiver `@`. Não use `alert()`.
4. Botão **`Enviar alerta agora`** — monta um `mailto:` com destinatários, assunto
   `[ALERTA RFB] N publicação(ões) — DD/MM/AAAA` e corpo em texto com título + link de cada item,
   e abre o Outlook já preenchido. Se a RFB não publicou nada no dia, avise em vez de abrir o e-mail.
   Deixe comentado no código que `mailto:` tem limite de tamanho (~2.000 caracteres) e por isso
   serve para o disparo manual, não para o automático.
5. **Bloco YAML gerado ao vivo**, com botão `Copiar bloco`:

   ```yaml
   alerta_rfb:
     destinatarios:
       - "laylla.cabral@letsmarketing.com.br"
   ```

   Junto, a frase: *o envio automático lê os destinatários de `config.local.yml`; cole este bloco
   lá para valer também nas coletas agendadas.*

Por que os dois lugares: a página é HTML estático e **não consegue escrever em arquivo nem enviar
e-mail sozinha**. Quem envia de verdade é o coletor. Em vez de esconder isso, o painel deixa o
caminho explícito — digite aqui, copie o bloco, cole no arquivo. Não invente um backend só para
salvar um campo de e-mail.

**Notificação do navegador:** botão `Ativar notificações` que pede `Notification.requestPermission()`
e notifica ao detectar item novo da RFB. Sem som automático — o navegador bloqueia e incomoda.
Som só como opção, desligada por padrão.

**Por e-mail (`coletor/alerta_rfb.py`):**
- Roda no fim de cada coleta. Compara os `id`s da RFB com `data/estado_rfb.json`.
- Item novo → envia e-mail via SMTP com assunto
  `[ALERTA RFB] N nova(s) publicação(ões) — DD/MM/AAAA HH:MM` e corpo HTML simples
  (mesma paleta LETS) listando título + link + horário.
- Nenhum item novo → **não envia nada**. Silêncio é sucesso; e-mail vazio treina o time a ignorar.
- Credenciais e destinatários em `config.local.yml` (no `.gitignore`), nunca no código:
  ```yaml
  smtp:
    host: smtp.office365.com
    porta: 587
    usuario: "..."
    senha: "..."        # senha de app, não a senha da conta
    remetente: "..."
  alerta_rfb:
    destinatarios: ["..."]
  ```
- Anti-spam: agrupe todos os itens novos da mesma coleta em **um** e-mail.
  Grave `ultimo_envio` e não reenvie o mesmo `id` nunca mais.
- Flag `--dry-run` que imprime o e-mail no terminal em vez de enviar. Use no desenvolvimento.
- Crie `config.local.example.yml` versionado, preenchido com placeholders.

**Agendamento — os dois sistemas.** Alvo: dias úteis às **08h00, 12h00, 15h00 e 17h30**
(America/Sao_Paulo). Não instale nada automaticamente; só documente e deixe pronto.

- **Windows** — passo a passo do Agendador de Tarefas no README: ação "Iniciar um programa",
  programa `.venv\Scripts\python.exe`, argumentos `coletor\fetch.py`,
  campo **"Iniciar em"** preenchido com a pasta do projeto (sem isso os caminhos relativos falham).
  Entregue também um `coletar.bat` de uma linha que ative o venv e rode o coletor,
  para a pessoa poder testar com duplo clique.
- **macOS** — bloco de `crontab -e` pronto para copiar, com caminho absoluto.
- Não gere `launchd` plist: é mais frágil de explicar e o cron resolve.

---

## 10. Critérios de aceite

Só considere pronto quando **todos** passarem, e me mostre a evidência de cada um:

1. `python -m coletor.validar_fontes` imprime a tabela das 22 fontes com status real.
   **Pelo menos 18 devem estar `ok`.** Para as que falharem, documente o motivo no README.
2. `python -m coletor.fetch --dias 3` popula `data/noticias.json` com itens de múltiplos veículos,
   datas corretas e **zero duplicatas** (rodar duas vezes seguidas não altera a contagem).
3. Abrir `index.html` com duplo clique (protocolo `file://`) funciona — lista carregada,
   filtro por dia funcionando, sem erro no console.
4. Selecionar itens de 3 veículos, clicar em `Gerar HTML para Outlook`, colar num e-mail do Outlook
   **para Windows**: faixa preta, régua vermelha, blocos por veículo e rodapé de “sem novidades”
   aparecem como no §8. Me mostre print do resultado colado, não só o preview do navegador.
5. Nenhum veículo sem notícia aparece como bloco no modo padrão; todos eles aparecem no rodapé.
   Com o toggle ligado, os 22 voltam a aparecer, na ordem correta.
6. Painel de destinatários: digitar dois e-mails, salvar, recarregar a página — os valores
   continuam lá, e o bloco YAML reflete exatamente o que foi digitado.
7. `python -m coletor.alerta_rfb --dry-run` imprime um e-mail válido quando há item novo simulado,
   e imprime `nada a enviar` quando não há.
8. Navegação completa por teclado e contraste AA em todos os textos.
9. `README.md` permite que alguém sem contexto técnico instale e rode em menos de 5 minutos,
   **com os comandos de Windows e de macOS lado a lado**.
10. Nenhum `open()` sem `encoding="utf-8"` e nenhuma concatenação de caminho com `/` ou `\`.
   Verifique com `grep -rn "open(" coletor/` e me mostre o resultado.

---

## 11. Ordem de execução

Trabalhe em fases e **pare ao fim de cada uma para eu revisar**. Não emende as fases.

- **Fase 0** — Extrair o HTML do `.eml` para `referencia/`. Me mostrar a estrutura da tabela
  que você identificou e confirmar o entendimento **antes** de codar.
- **Fase 1** — `validar_fontes.py` + `sources.yml` preenchido com o resultado real.
- **Fase 2** — Coletor completo, com o JSON populado de 3 dias.
- **Fase 3** — `index.html`: listagem, filtro por dia, seleção.
- **Fase 4** — Exportador Outlook + comparação lado a lado com o original.
- **Fase 5** — Alerta RFB (página + e-mail) e agendamento.
- **Fase 6** — README, `.gitignore`, checklist do §10 verificado item por item.

## 12. Não faça

- Não invente URLs de RSS sem testar; se não achou, diga que não achou.
- Não use IA/LLM em runtime para resumir ou classificar — só dicionário de termos.
  A ferramenta precisa rodar sozinha, de graça, offline.
- Não crie banco de dados, Docker, CI, testes E2E com browser headless.
- Não altere a estrutura visual do e-mail "para melhorar". O formato atual é o requisito.
- Não faça commit de `config.local.yml`.
- Não instale `launchd`/cron sem eu pedir.
