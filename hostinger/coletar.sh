#!/bin/bash
# Coleta do Clipping LETS rodando no servidor da Hostinger (IP no Brasil).
# TST e os sites do gov.br recusam conexão vinda dos servidores do GitHub
# Actions (EUA), então a coleta agendada roda aqui, pelo Cron Jobs do hPanel,
# de hora em hora (o painel só aceita uma hora por tarefa):
#   0 * * * *  /bin/bash $HOME/clipping-coletor/hostinger/coletar.sh >> $HOME/clipping-coletor.log 2>&1
# e o próprio script só coleta nos horários abaixo. Rodar na mão com
# "bash hostinger/coletar.sh agora" ignora o horário.
# Depois de coletar, publica no GitHub (deploy key "Hostinger - coletor do
# clipping"), o que aciona a implantação automática da Hostinger e da Vercel.
set -euo pipefail

# tudo dentro de main(): o bash lê a função inteira antes de rodar, então o
# "git reset" abaixo pode atualizar este arquivo sem atrapalhar a execução
main() {
  # Horários em UTC (servidor está em UTC): 08h, 11h, 13h e 17h de Brasília.
  HORARIOS_UTC="11 14 16 20"
  if [ "${1:-}" != "agora" ] && [[ " $HORARIOS_UTC " != *" $(date -u +%H) "* ]]; then
    return 0
  fi

  cd "$HOME/clipping-coletor"

  # não deixa duas coletas rodarem ao mesmo tempo
  exec 9>"$HOME/.clipping-coletor.lock"
  flock -n 9 || { echo "$(date -u +%FT%TZ) coleta anterior ainda rodando, pulando"; return 0; }

  echo "=== $(date -u +%FT%TZ) início"

  # parte sempre da versão publicada (código + dados da última coleta)
  git fetch -q origin main
  git reset -q --hard origin/main

  # reinstala as bibliotecas só quando requirements.txt mudar
  # (venv não funciona nesta hospedagem, por isso pip --target)
  if ! cmp -s requirements.txt .libs/.requirements.txt 2>/dev/null; then
    rm -rf .libs
    python3 -m pip install -q --target .libs -r requirements.txt
    cp requirements.txt .libs/.requirements.txt
  fi

  PYTHONPATH=.libs python3 -m coletor.fetch --dias 90

  git add data/ index.html
  if git diff --staged --quiet; then
    echo "sem novidades"
  else
    git -c user.name="Clipping LETS bot (Hostinger)" \
        -c user.email="actions@users.noreply.github.com" \
        commit -q -m "Coleta automática $(date -u +'%Y-%m-%dT%H:%MZ')"
    git push -q origin HEAD:main
    echo "publicado"
  fi
  echo "=== $(date -u +%FT%TZ) fim"
}

main "$@"
