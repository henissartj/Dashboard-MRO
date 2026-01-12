#!/bin/bash
# Script simple pour appliquer la configuration nginx

echo "Copie de la configuration corrigée..."
sudo cp /opt/mro_dash/default_nginx_config.txt /etc/nginx/sites-available/default

echo "Vérification de la syntaxe..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo "✓ Syntaxe OK"
    echo "Rechargement de nginx..."
    sudo systemctl reload nginx
    echo "✓ Configuration appliquée"
else
    echo "✗ Erreur de syntaxe:"
    sudo nginx -t 2>&1 | grep -i error
    exit 1
fi
