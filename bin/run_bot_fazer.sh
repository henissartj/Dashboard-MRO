#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/mro_dash"
VENV_ACTIVATE="${APP_DIR}/.venv/bin/activate"

if [[ -f /home/app/bot-discord/.env ]]; then
  set -a
  source /home/app/bot-discord/.env
  set +a
elif [[ -f "${APP_DIR}/.env" ]]; then
  set -a
  source "${APP_DIR}/.env"
  set +a
fi

export DISCORD_BOT_TOKEN="${DISCORD_BOT_TOKEN:-${DISCORD_TOKEN:-}}"

cd "${APP_DIR}"
source "${VENV_ACTIVATE}"

exec python -u bot/bot_de_fazer.py
