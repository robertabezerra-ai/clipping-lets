# Clipping LETS

Ferramenta para montar o e-mail **Notícias diárias** sem trabalho manual:
o coletor busca as notícias das **22 fontes oficiais**, a página deixa você
marcar o que entra, e o botão gera o HTML pronto para colar no Outlook.
Sem backend, sem banco de dados, roda local.

---

## Ver funcionando agora (sem instalar nada)

Dê **duplo clique em `index.html`**. Ele já vem com notícias reais coletadas
das 22 fontes.

O que testar:

1. Navegue entre os dias com `‹ Dia anterior` / `Dia seguinte ›`.
2. Marque algumas notícias de veículos diferentes.
3. Clique em **Gerar HTML para Outlook** → **Copiar formatado** → cole num e-mail do Outlook.
4. Ligue **Listar cada veículo sem novidade** e gere de novo: as 22 linhas aparecem,
   as sem notícia como “Nada”, todas na ordem oficial.
5. Se algum dia tiver publicação da Receita Federal, veja o banner vermelho no topo.

---

## Coletar notícias de verdade

Precisa de **Python 3.11 ou mais novo**. Funciona igual no Windows e no Mac.

### Windows (PowerShell, na pasta do projeto)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py -m coletor.validar_fontes      # testa as 22 URLs, imprime tabela
py -m coletor.fetch --validar     # so testa as fontes
py -m coletor.fetch               # coleta e grava
```

Se o PowerShell reclamar de política de execução, rode uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### macOS / Linux (Terminal, na pasta do projeto)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m coletor.validar_fontes  # testa as 22 URLs, imprime tabela
python -m coletor.fetch --validar
python -m coletor.fetch
```

Depois de coletar, recarregue o `index.html` no navegador.

### Comandos úteis

| Comando | O que faz |
|---|---|
| `python -m coletor.validar_fontes` | testa as 22 URLs de `sources.yml` e imprime status/itens/data mais recente, sem gravar |
| `python -m coletor.fetch --validar` | mesma ideia, mas já rodando o parser completo de cada fonte |
| `python -m coletor.fetch --fonte senado` | coleta só uma fonte (para depurar o parser) |
| `python -m coletor.fetch --dias 30` | mantém 30 dias de histórico em vez de 90 |

As 22 fontes (URL, estratégia de coleta, se está `ok`/`instavel`/`falhou`) ficam em
[`sources.yml`](sources.yml), com uma nota explicando a escolha de cada uma.
Ajuste ali, não precisa mexer em código.

Para voltar aos dados de demonstração: `python coletor/seed_demo.py`

---

## Alerta da Receita Federal

Três saídas:

- **Na página** — banner vermelho no topo quando a RFB publicou algo no dia, mais
  um painel “Alerta da Receita Federal — quem recebe” onde você cadastra os
  destinatários (fica salvo no navegador) e pode disparar um `mailto:` manual.
- **Notificação do navegador** — botão “Ativar notificações” no mesmo painel.
  Avisa nesta aba quando a última coleta trouxe item novo da RFB. Só funciona
  com a página aberta; sem som por padrão (tem toggle pra ligar).
- **Por e-mail de verdade** — roda no fim de cada coleta e envia **um** e-mail com
  os itens novos. Sem novidade, não envia nada.

Para o e-mail funcionar, copie `config.local.example.yml` para `config.local.yml`
e preencha SMTP e destinatários (o painel da página gera o bloco YAML pronto pra
colar). Use **senha de aplicativo**, não a senha da conta.

Teste sem enviar:

```
python -m coletor.alerta_rfb --dry-run
```

---

## Rodar sozinho todo dia

**Windows** — Agendador de Tarefas: nova tarefa básica, ação
“Iniciar um programa”, programa `.venv\Scripts\python.exe`,
argumentos `-m coletor.fetch`, “Iniciar em” = a pasta do projeto
(sem isso os caminhos relativos falham). Repita para os horários
08h00, 12h00, 15h00 e 17h00, em dias úteis — o de 17h é a última coleta
do dia, pra deixar tempo de revisar e montar o e-mail antes do envio.

Prefere testar com duplo clique antes de agendar? Use o `coletar.bat`
desta pasta — ele ativa o venv e roda o coletor sozinho.

**macOS** — `crontab -e` e adicione (troque `/caminho/do/projeto` pelo
caminho absoluto real da pasta):

```
0 8,12,15,17 * * 1-5  cd /caminho/do/projeto && .venv/bin/python -m coletor.fetch
```

Não instalamos nada disso automaticamente — copie e agende você mesmo
quando quiser. Não usamos `launchd`: o cron já resolve e é mais simples
de explicar.

---

## Como o score de relevância funciona

[`relevancia.yml`](relevancia.yml) tem dois dicionários de termos: os que **sobem** o score
(decisão, tese, instrução normativa, reforma tributária, prazo, LGPD…) e os que
**descem** (posse, homenagem, comenda, apreensão de droga…). Toda notícia começa em 40.
Acima de **50** ganha o selo `Alta relevância`.

O score **nunca exclui nada** — só ordena e sinaliza. Quem decide é você.

Se o corte estiver largo ou apertado demais, ajuste os pesos direto no YAML —
não precisa mexer em `coletor/relevancia.py`. Cuidado: o casamento é por pedaço
de palavra, então plural pode precisar de entrada própria
(`medida provisoria` **e** `medidas provisorias`).

---

## Limitações conhecidas

`python -m coletor.validar_fontes` confirma **19 das 22 fontes ok**, testado contra os
sites reais. As 3 que não consegui deixar funcionando, com o motivo real (não
adivinhado — está tudo documentado em [`sources.yml`](sources.yml)):

- **STJ** — o portal (`stj.jus.br`) é um SharePoint que renderiza a listagem de
  notícias inteira via JavaScript; não há link nenhum no HTML cru, nem RSS, nem
  API pública que eu tenha achado.
- **Anbima** — mesma ideia: a listagem usa um CMS (Lumis) que carrega as notícias
  via chamada JavaScript cujo endpoint não aparece em lugar nenhum do HTML estático.
- **Coaf** — o portal devolve `401` pra qualquer requisição automatizada (RSS,
  scraping da página e a API do gov.br novo, testei os três), mesmo sem pressa
  entre tentativas. Parece bloqueio deliberado a bots.

Nos três casos, tentar “forçar” exigiria um navegador headless — que a
especificação deste projeto pede pra não usar.

Duas coisas que **não são bug**, é assim que as fontes publicam de verdade:

- **CARF** publica raramente na seção de notícias (a atividade dele é
  principalmente pauta de julgamento, que não entra por não ter valor editorial
  pros escritórios) — não estranhe ver poucos ou nenhum item na maioria dos dias.
- **Receita Federal e CVM** às vezes têm poucos itens no RSS oficial deles mesmo
  — o coletor está lendo certo, a fonte que publica pouco naquele momento.

Se uma fonte falhar, a página mostra “Nada” para ela igual a uma fonte que
simplesmente não publicou. **Confira o painel “Saúde das fontes” no rodapé
antes de enviar** — “Nada” pode significar “não coletado”, ele mostra qual é
qual e o motivo do erro.
