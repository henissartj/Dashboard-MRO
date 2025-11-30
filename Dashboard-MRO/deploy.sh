#!/usr/bin/env bash
set -euo pipefail

### ─────────────────────────────
### CONFIG
### ─────────────────────────────
APP_DIR="/opt/mro_dash"
BRANCH="vps"                    # <── ICI : branche par défaut = vps
SERVICE_NAME="mro_dash"
DOMAIN="epheverisme.art"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${APP_DIR}/.venv"
REQ_FILE="${APP_DIR}/requirements.txt"
HEALTH_LOCAL_URL="http://127.0.0.1:8050/"
HEALTH_PUBLIC_URL="http://${DOMAIN}/"

### ─────────────────────────────
### HELPERS
### ─────────────────────────────
log()   { echo -e "\033[1;34m[deploy]\033[0m $*"; }
ok()    { echo -e "\033[1;32m[ok]\033[0m $*"; }
warn()  { echo -e "\033[1;33m[warn]\033[0m $*"; }
fail()  { echo -e "\033[1;31m[fail]\033[0m $*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || fail "Commande requise manquante: $1"; }
healthcheck() { curl -fsS --max-time 5 -I "$1" >/dev/null; }

### ─────────────────────────────
### CHECKS
### ─────────────────────────────
need git; need curl; need systemctl; need "$PYTHON_BIN"

log "Déploiement dans ${APP_DIR} (branche: ${BRANCH})"
cd "$APP_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "Ce dossier n'est pas un dépôt git. Fais 'git init' + 'git remote add origin …' d'abord."
fi

PREV_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo "unknown")" || true

log "Récupération remote…"
git fetch --all --prune || true

log "Passage sur la branche locale ${BRANCH}…"
git checkout -q "${BRANCH}" || git checkout -b "${BRANCH}"

# NE faire un reset dur que si la branche distante existe
if git ls-remote --exit-code --heads origin "${BRANCH}" >/dev/null 2>&1; then
  log "Sync sur origin/${BRANCH}…"
  git reset --hard "origin/${BRANCH}"
  ok "Synchronisé avec origin/${BRANCH}"
else
  warn "origin/${BRANCH} n'existe pas. Je ne touche pas au working tree local."
fi

NEW_COMMIT="$(git rev-parse HEAD)"
ok "Code local -> ${NEW_COMMIT}"

# VENV
if [[ ! -d "${VENV_DIR}" ]]; then
  log "Création du venv (${VENV_DIR})…"
  "$PYTHON_BIN" -m venv "${VENV_DIR}"
fi
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

log "Upgrade pip/setuptools/wheel…"
pip install -q --upgrade pip setuptools wheel

# Dépendances
if [[ -f "${REQ_FILE}" ]]; then
  log "Installation requirements.txt…"
  pip install -q -r "${REQ_FILE}"
else
  warn "requirements.txt absent, install minimal…"
  pip install -q dash plotly numpy scipy gunicorn kaleido==0.2.1
fi

# Vérif syntaxe (non bloquante)
log "Vérification syntaxe Python…"
python -m py_compile app.py pages/*.py 2>/dev/null || true

# Restart service
log "Restart service ${SERVICE_NAME}…"
sudo systemctl daemon-reload || true
sudo systemctl restart "${SERVICE_NAME}"

# Health local
log "Health-check local ${HEALTH_LOCAL_URL}…"
if healthcheck "${HEALTH_LOCAL_URL}"; then
  ok "Gunicorn OK."
else
  warn "Health local KO. Tentative rollback…"
  if [[ "${PREV_COMMIT}" != "unknown" ]]; then
    git reset --hard "${PREV_COMMIT}"
    sudo systemctl restart "${SERVICE_NAME}"
    sleep 2
    healthcheck "${HEALTH_LOCAL_URL}" && ok "Rollback OK." || fail "Rollback KO. Vois: journalctl -u ${SERVICE_NAME} -n 200 --no-pager"
  else
    fail "Impossible de rollback (commit précédent inconnu)."
  fi
fi

# Health public (info)
log "Health-check public ${HEALTH_PUBLIC_URL}…"
if healthcheck "${HEALTH_PUBLIC_URL}"; then
  ok "Nginx répond."
else
  warn "Nginx HTTP KO (peut-être HTTPS)."
fi

ok "Déploiement terminé."