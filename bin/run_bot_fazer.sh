#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/mro_dash"
VENV_ACTIVATE="${APP_DIR}/.venv/bin/activate"

if [[ -f /etc/default/bot-fazer ]]; then
  set -a
  source /etc/default/bot-fazer
  set +a
fi

export DISCORD_BOT_TOKEN="${DISCORD_BOT_TOKEN:-${DISCORD_TOKEN:-}}"

cd "${APP_DIR}"
source "${VENV_ACTIVATE}"

exec python -u -m bot.bot_de_fazer
