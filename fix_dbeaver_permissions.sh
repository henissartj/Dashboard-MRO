#!/bin/bash

# Script pour accorder tous les privilèges à l'utilisateur dbeaver_user

set -e

DB_NAME="bot_fazer"
DB_USER="dbeaver_user"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Attribution des privilèges à dbeaver_user ===${NC}\n"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Erreur: Ce script doit être exécuté avec sudo${NC}"
    exit 1
fi

# Obtenir l'IP de l'utilisateur depuis les utilisateurs MySQL existants
echo -e "${YELLOW}Recherche de l'IP configurée pour $DB_USER...${NC}"
USER_HOST=$(mysql -u root -e "SELECT host FROM mysql.user WHERE user = '$DB_USER';" 2>/dev/null | grep -v host | head -1)

if [ -z "$USER_HOST" ]; then
    echo -e "${RED}Erreur: Utilisateur $DB_USER non trouvé${NC}"
    exit 1
fi

echo -e "${GREEN}✓ IP trouvée: $USER_HOST${NC}\n"

# Accorder tous les privilèges
echo -e "${YELLOW}Attribution des privilèges complets...${NC}"
mysql -u root <<EOF
-- Accorder tous les privilèges sur la base de données
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'$USER_HOST';

-- Accorder les privilèges sur toutes les tables existantes
USE $DB_NAME;
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, CREATE TEMPORARY TABLES, LOCK TABLES, EXECUTE, CREATE VIEW, SHOW VIEW, CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER ON \`$DB_NAME\`.* TO '$DB_USER'@'$USER_HOST';

-- Appliquer les changements
FLUSH PRIVILEGES;

-- Vérifier les privilèges
SHOW GRANTS FOR '$DB_USER'@'$USER_HOST';
EOF

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Privilèges accordés avec succès !${NC}"
    echo -e "\n${YELLOW}Vous pouvez maintenant utiliser DBeaver pour accéder à toutes les tables.${NC}"
else
    echo -e "\n${RED}✗ Erreur lors de l'attribution des privilèges${NC}"
    exit 1
fi
