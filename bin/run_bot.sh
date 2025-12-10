#!/usr/bin/env bash
set -euo pipefail

# Charge l'environnement
# Priorité au fichier token externe si présent
if [[ -f /home/app/bot-discord/.env ]]; then
  set -a
  source /home/app/bot-discord/.env
  set +a
elif [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

# Bot unifié (Fcoins+Shop+Blackjack+Fun)
exec python bot_unifie.py
