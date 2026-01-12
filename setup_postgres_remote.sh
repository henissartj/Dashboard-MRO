#!/bin/bash

# Script spécifique pour configurer l'accès distant PostgreSQL pour la base "mro"

set -e

DB_NAME="mro"
DB_USER="dbeaver_user"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Configuration PostgreSQL pour DBeaver ===${NC}\n"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Erreur: Ce script doit être exécuté avec sudo${NC}"
    exit 1
fi

# Demander le mot de passe
read -sp "Mot de passe pour l'utilisateur $DB_USER: " DB_PASSWORD
echo ""
if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Erreur: Le mot de passe est requis${NC}"
    exit 1
fi

# Trouver la version PostgreSQL
PG_VERSION=$(psql --version 2>/dev/null | grep -oP '\d+' | head -1)
if [ -z "$PG_VERSION" ]; then
    echo -e "${RED}Erreur: PostgreSQL non trouvé${NC}"
    exit 1
fi

PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

if [ ! -f "$PG_CONF" ]; then
    echo -e "${RED}Erreur: Fichier de configuration non trouvé: $PG_CONF${NC}"
    exit 1
fi

echo -e "${YELLOW}Version PostgreSQL détectée: $PG_VERSION${NC}\n"

# Sauvegarder les configurations
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
cp "$PG_CONF" "${PG_CONF}.backup.$BACKUP_DATE"
cp "$PG_HBA" "${PG_HBA}.backup.$BACKUP_DATE"
echo -e "${GREEN}✓ Configurations sauvegardées${NC}"

# Modifier postgresql.conf
echo -e "${YELLOW}Configuration de listen_addresses...${NC}"
if grep -q "^listen_addresses" "$PG_CONF"; then
    sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PG_CONF"
else
    echo "listen_addresses = '*'" >> "$PG_CONF"
fi
echo -e "${GREEN}✓ listen_addresses = '*' configuré${NC}"

# Modifier pg_hba.conf
echo -e "${YELLOW}Configuration de pg_hba.conf...${NC}"
if ! grep -q "host.*all.*all.*0.0.0.0/0.*md5" "$PG_HBA"; then
    echo "" >> "$PG_HBA"
    echo "# Accès distant pour DBeaver" >> "$PG_HBA"
    echo "host    all             all             0.0.0.0/0               md5" >> "$PG_HBA"
    echo -e "${GREEN}✓ Règle d'accès distant ajoutée${NC}"
else
    echo -e "${YELLOW}⚠ Règle d'accès distant déjà présente${NC}"
fi

# Créer l'utilisateur PostgreSQL
echo -e "${YELLOW}Création de l'utilisateur PostgreSQL...${NC}"
sudo -u postgres psql <<EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    ELSE
        ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\c $DB_NAME
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
\q
EOF

echo -e "${GREEN}✓ Utilisateur créé et privilèges accordés${NC}"

# Configurer le pare-feu
echo -e "${YELLOW}Configuration du pare-feu...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 5432/tcp
    echo -e "${GREEN}✓ Port 5432 autorisé dans UFW${NC}"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=postgresql
    firewall-cmd --reload
    echo -e "${GREEN}✓ Port PostgreSQL autorisé dans firewalld${NC}"
else
    echo -e "${YELLOW}⚠ Aucun pare-feu géré détecté, configurez manuellement${NC}"
fi

# Redémarrer PostgreSQL
echo -e "${YELLOW}Redémarrage de PostgreSQL...${NC}"
systemctl restart postgresql
sleep 2

if systemctl is-active --quiet postgresql; then
    echo -e "${GREEN}✓ PostgreSQL redémarré avec succès${NC}"
else
    echo -e "${RED}✗ Erreur lors du redémarrage de PostgreSQL${NC}"
    exit 1
fi

# Afficher les informations de connexion
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "\n${GREEN}=== Configuration terminée avec succès ! ===${NC}\n"
echo -e "${YELLOW}Informations pour DBeaver:${NC}"
echo -e "  Hôte: ${GREEN}$SERVER_IP${NC}"
echo -e "  Port: ${GREEN}5432${NC}"
echo -e "  Base de données: ${GREEN}$DB_NAME${NC}"
echo -e "  Utilisateur: ${GREEN}$DB_USER${NC}"
echo -e "  Mot de passe: ${GREEN}[celui que vous avez défini]${NC}"
echo -e "\n${YELLOW}Vérification:${NC}"
echo -e "  Pour tester: psql -h $SERVER_IP -U $DB_USER -d $DB_NAME"
echo -e "\n${YELLOW}⚠️  Note de sécurité:${NC}"
echo -e "  L'accès est ouvert à toutes les IPs (0.0.0.0/0)"
echo -e "  Pour plus de sécurité, limitez l'accès à votre IP spécifique"
