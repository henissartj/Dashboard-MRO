#!/bin/bash
# Script manuel simple pour corriger /me

CONFIG="/etc/nginx/sites-available/default"
BACKUP="${CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

echo "Sauvegarde..."
sudo cp "$CONFIG" "$BACKUP"

echo "Création de la nouvelle configuration..."

# Créer un fichier temporaire avec la bonne configuration
TMP=$(mktemp)

# Copier tout sauf le bloc location /me problématique
sudo awk '
    BEGIN { skip=0 }
    /location.*me/ { skip=1; next }
    skip && /^    }/ { skip=0; next }
    skip { next }
    { print }
' "$CONFIG" > "$TMP"

# Insérer le bon bloc après /api
sudo awk '
    /location \/api {/ {
        print
        getline
        while (!/^    }/) {
            print
            getline
        }
        print
        print "    location /me {"
        print "        proxy_pass http://127.0.0.1:8000;"
        print "        proxy_set_header Host $host;"
        print "        proxy_set_header X-Real-IP $remote_addr;"
        print "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
        print "        proxy_set_header X-Forwarded-Proto $scheme;"
        print "    }"
        print ""
        next
    }
    { print }
' "$TMP" > "${TMP}.new"

sudo mv "${TMP}.new" "$CONFIG"
rm -f "$TMP"

echo "Vérification..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
    echo "✓ OK"
    sudo systemctl reload nginx && echo "✓ Rechargé" || echo "✗ Erreur reload"
else
    echo "✗ Erreur syntaxe"
    sudo cp "$BACKUP" "$CONFIG"
    exit 1
fi
