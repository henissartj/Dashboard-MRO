#!/usr/bin/env bash
set -e
cd /opt/mro_dash
git add -A
# Crée un commit seulement s'il y a des changements
if ! git diff --cached --quiet; then
  git commit -m "VPS backup: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
fi
git push
