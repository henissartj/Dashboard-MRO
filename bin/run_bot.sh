#!/usr/bin/env bash
set -euo pipefail

# Charge l'environnement (.env) si présent
if [[ -f .env ]]; then
  # Exporter les variables depuis .env
  set -a
  source .env
  set +a
fi

exec python bot_labo.py
