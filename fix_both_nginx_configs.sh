#!/bin/bash
# Script pour corriger les deux configurations nginx

DEFAULT="/etc/nginx/sites-available/default"
BOTDEFAZER="/etc/nginx/sites-available/botdefazer"

BACKUP_DEFAULT="${DEFAULT}.backup.$(date +%Y%m%d_%H%M%S)"
BACKUP_BOT="${BOTDEFAZER}.backup.$(date +%Y%m%d_%H%M%S)"

echo "Sauvegarde des configurations..."
sudo cp "$DEFAULT" "$BACKUP_DEFAULT"
sudo cp "$BOTDEFAZER" "$BACKUP_BOT"

echo "Correction de /etc/nginx/sites-available/default..."

# Corriger default - remplacer location ~ ^/me$ par location /me
sudo sed -i 's|location ~ \^/me\$|location /me|' "$DEFAULT"
sudo sed -i 's|proxy_pass http://127.0.0.1:8000/me;|proxy_pass http://127.0.0.1:8000;|' "$DEFAULT"

echo "Correction de /etc/nginx/sites-available/botdefazer..."

# Corriger botdefazer - remplacer location ~ ^/me$ par location /me
sudo sed -i 's|location ~ \^/me\$|location /me|' "$BOTDEFAZER"
sudo sed -i 's|proxy_pass http://127.0.0.1:8000/me;|proxy_pass http://127.0.0.1:8000;|' "$BOTDEFAZER"

echo "Vérification de la syntaxe nginx..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo "✓ Syntaxe OK"
    echo "Rechargement de nginx..."
    if sudo systemctl reload nginx; then
        echo "✓ Nginx rechargé avec succès!"
        echo ""
        echo "Testez maintenant: fazer.city/me"
    else
        echo "✗ Erreur lors du rechargement"
        echo "Restauration des sauvegardes..."
        sudo cp "$BACKUP_DEFAULT" "$DEFAULT"
        sudo cp "$BACKUP_BOT" "$BOTDEFAZER"
        sudo systemctl reload nginx
        exit 1
    fi
else
    echo "✗ Erreur de syntaxe:"
    sudo nginx -t 2>&1 | grep -i error
    echo "Restauration des sauvegardes..."
    sudo cp "$BACKUP_DEFAULT" "$DEFAULT"
    sudo cp "$BACKUP_BOT" "$BOTDEFAZER"
    exit 1
fi
