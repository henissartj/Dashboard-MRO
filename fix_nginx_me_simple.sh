#!/bin/bash
# Script simple pour corriger la route /me dans nginx

CONFIG="/etc/nginx/sites-available/default"

echo "Correction de la configuration nginx pour /me..."

# Créer une sauvegarde
sudo cp "$CONFIG" "${CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# Remplacer la ligne problématique
sudo sed -i 's|location ~ \^/me\$ {|location /me {|' "$CONFIG"
sudo sed -i 's|proxy_pass http://127.0.0.1:8000/me;|proxy_pass http://127.0.0.1:8000;|' "$CONFIG"

echo "Vérification de la syntaxe..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo "✓ Syntaxe OK"
    echo "Rechargement de nginx..."
    sudo systemctl reload nginx
    if [ $? -eq 0 ]; then
        echo "✓ Nginx rechargé avec succès"
        echo "Testez maintenant: curl -k https://localhost/me"
    else
        echo "✗ Erreur lors du rechargement"
        sudo systemctl status nginx.service --no-pager -l | tail -20
    fi
else
    echo "✗ Erreur de syntaxe:"
    sudo nginx -t 2>&1 | grep -i error
    echo "Restauration de la sauvegarde..."
    sudo cp "${CONFIG}.backup."* "$CONFIG" 2>/dev/null
    exit 1
fi
