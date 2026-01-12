#!/bin/bash
# Script simple pour appliquer la configuration corrigée

CONFIG="/etc/nginx/sites-available/default"
FIXED="/opt/mro_dash/default_nginx_fixed.conf"
BACKUP="${CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

echo "Sauvegarde de la configuration actuelle..."
sudo cp "$CONFIG" "$BACKUP"

echo "Application de la configuration corrigée..."
sudo cp "$FIXED" "$CONFIG"

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
        echo "Restauration de la sauvegarde..."
        sudo cp "$BACKUP" "$CONFIG"
        sudo systemctl reload nginx
        exit 1
    fi
else
    echo "✗ Erreur de syntaxe:"
    sudo nginx -t 2>&1 | grep -i error
    echo "Restauration de la sauvegarde..."
    sudo cp "$BACKUP" "$CONFIG"
    exit 1
fi
