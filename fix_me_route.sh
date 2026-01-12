#!/bin/bash
# Script pour corriger définitivement la route /me

CONFIG="/etc/nginx/sites-available/default"
BACKUP="${CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

echo "Sauvegarde de la configuration..."
sudo cp "$CONFIG" "$BACKUP"

echo "Correction de la route /me..."

# Remplacer la configuration problématique par la bonne
sudo sed -i '/location.*me/,/^    }/c\
    location /me {\
        proxy_pass http://127.0.0.1:8000;\
        proxy_set_header Host $host;\
        proxy_set_header X-Real-IP $remote_addr;\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\
        proxy_set_header X-Forwarded-Proto $scheme;\
    }' "$CONFIG"

echo "Configuration corrigée. Vérification de la syntaxe..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo "✓ Syntaxe OK"
    echo "Rechargement de nginx..."
    sudo systemctl reload nginx
    if [ $? -eq 0 ]; then
        echo "✓ Nginx rechargé avec succès!"
        echo ""
        echo "Test de la route..."
        sleep 1
        curl -s -k https://localhost/me | grep -o "<title>.*</title>" || echo "Testez manuellement: fazer.city/me"
    else
        echo "✗ Erreur lors du rechargement"
        echo "Restauration de la sauvegarde..."
        sudo cp "$BACKUP" "$CONFIG"
        sudo systemctl reload nginx
    fi
else
    echo "✗ Erreur de syntaxe:"
    sudo nginx -t 2>&1 | grep -i error
    echo "Restauration de la sauvegarde..."
    sudo cp "$BACKUP" "$CONFIG"
    exit 1
fi
