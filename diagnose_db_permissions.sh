#!/bin/bash

# Script de diagnostic pour les permissions MySQL

set -e

DB_NAME="bot_fazer"
DB_USER="dbeaver_user"
USER_IP="77.141.37.229"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Diagnostic des Permissions MySQL ===${NC}\n"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Erreur: Ce script doit être exécuté avec sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}1. Vérification de l'utilisateur...${NC}"
mysql -u root <<EOF
SELECT user, host FROM mysql.user WHERE user = '$DB_USER';
EOF

echo -e "\n${YELLOW}2. Privilèges actuels pour $DB_USER@$USER_IP:${NC}"
mysql -u root <<EOF
SHOW GRANTS FOR '$DB_USER'@'$USER_IP';
EOF

echo -e "\n${YELLOW}3. Vérification de l'existence de la base de données $DB_NAME:${NC}"
mysql -u root <<EOF
SHOW DATABASES LIKE '$DB_NAME';
EOF

echo -e "\n${YELLOW}4. Tables dans la base $DB_NAME:${NC}"
mysql -u root <<EOF
USE $DB_NAME;
SHOW TABLES;
EOF

echo -e "\n${YELLOW}5. Vérification spécifique de la table 'users' (avec 's'):${NC}"
mysql -u root <<EOF
USE $DB_NAME;
SHOW TABLES LIKE 'users';
SELECT COUNT(*) as count FROM users LIMIT 1;
EOF

echo -e "\n${YELLOW}6. Vérification de la table système 'user' (sans 's') dans mysql:${NC}"
mysql -u root <<EOF
USE mysql;
SHOW TABLES LIKE 'user';
EOF

echo -e "\n${BLUE}=== Diagnostic terminé ===${NC}"
echo -e "\n${YELLOW}Note: Si vous essayez d'accéder à 'user' au lieu de 'users',${NC}"
echo -e "${YELLOW}assurez-vous d'être connecté à la base 'bot_fazer' et non à 'mysql'.${NC}"
