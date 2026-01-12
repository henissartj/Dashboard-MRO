#!/bin/bash
# Script pour ajouter la route /me dans nginx

CONFIG_FILE="/etc/nginx/sites-available/default"
BACKUP_FILE="/etc/nginx/sites-available/default.backup.$(date +%Y%m%d_%H%M%S)"

echo "Sauvegarde de la configuration actuelle..."
sudo cp "$CONFIG_FILE" "$BACKUP_FILE"

echo "Ajout de la route /me dans la configuration..."

# Créer un fichier temporaire avec la modification
TMP_FILE=$(mktemp)

# Lire le fichier et ajouter/modifier la règle /me
sudo sed -i.bak '/location \/api {/,/}/ {
    /location \/api {/a\
\
    location ~ ^/me$ {\
        proxy_pass http://127.0.0.1:8000/me;\
        proxy_set_header Host $host;\
        proxy_set_header X-Real-IP $remote_addr;\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\
        proxy_set_header X-Forwarded-Proto $scheme;\
    }
}' "$CONFIG_FILE" 2>/dev/null || {

# Si sed échoue, utiliser une approche différente
cat > "$TMP_FILE" << 'EOF'
    location ~ ^/me$ {
        proxy_pass http://127.0.0.1:8000/me;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

EOF

# Insérer après /api
sudo awk '
    /location \/api {/ {
        print
        getline
        while (!/^    }/) {
            print
            getline
        }
        print
        while ((getline line < "'"$TMP_FILE"'") > 0) {
            print line
        }
        close("'"$TMP_FILE"'")
        next
    }
    /location ~ \^\/me\$ {/ {
        # Skip existing /me block
        while (!/^    }/) {
            getline
        }
        getline
        next
    }
    { print }
' "$CONFIG_FILE" > "${CONFIG_FILE}.new" && sudo mv "${CONFIG_FILE}.new" "$CONFIG_FILE"
}

rm -f "$TMP_FILE"

echo "Vérification de la syntaxe nginx..."
if sudo nginx -t; then
    echo "✓ Syntaxe OK"
    echo "Rechargement de nginx..."
    sudo systemctl reload nginx && echo "✓ Nginx rechargé avec succès" || echo "✗ Erreur lors du rechargement"
else
    echo "✗ Erreur de syntaxe dans nginx.conf"
    echo "Restauration de la sauvegarde..."
    sudo cp "$BACKUP_FILE" "$CONFIG_FILE"
    exit 1
fi
