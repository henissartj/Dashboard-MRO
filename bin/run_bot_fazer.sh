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

# Clean up existing instances just in case
echo "🧹 Cleaning up old bot instances..."
pkill -f "bot.bot_de_fazer" || true
sleep 1

cd "${APP_DIR}"
source "${VENV_ACTIVATE}"

exec python -u -m bot.bot_de_fazer
