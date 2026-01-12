#!/bin/bash

# Script pour forcer l'attribution complète des privilèges

set -e

DB_NAME="bot_fazer"
DB_USER="dbeaver_user"
USER_IP="77.141.37.229"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Attribution FORCÉE des privilèges à dbeaver_user ===${NC}\n"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Erreur: Ce script doit être exécuté avec sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}Vérification de l'utilisateur...${NC}"
mysql -u root <<EOF
-- Afficher les utilisateurs existants
SELECT user, host FROM mysql.user WHERE user = '$DB_USER';
EOF

echo -e "\n${YELLOW}Suppression et recréation de l'utilisateur avec tous les privilèges...${NC}"
mysql -u root <<EOF
-- Supprimer l'utilisateur s'il existe
DROP USER IF EXISTS '$DB_USER'@'$USER_IP';
DROP USER IF EXISTS '$DB_USER'@'%';

-- Recréer l'utilisateur avec tous les privilèges dès le départ
CREATE USER '$DB_USER'@'$USER_IP' IDENTIFIED BY '$(mysql -u root -e "SELECT authentication_string FROM mysql.user WHERE user='$DB_USER' AND host='$USER_IP';" 2>/dev/null | tail -1 || echo '')';

-- Si le mot de passe n'a pas été récupéré, on va le redemander
EOF

echo -e "${YELLOW}Veuillez entrer le mot de passe pour $DB_USER:${NC}"
read -sp "Mot de passe: " DB_PASSWORD
echo ""

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Erreur: Le mot de passe est requis${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Création de l'utilisateur avec tous les privilèges...${NC}"
mysql -u root <<EOF
-- Supprimer l'utilisateur s'il existe
DROP USER IF EXISTS '$DB_USER'@'$USER_IP';

-- Créer l'utilisateur avec mot de passe
CREATE USER '$DB_USER'@'$USER_IP' IDENTIFIED BY '$DB_PASSWORD';

-- Accorder TOUS les privilèges sur la base de données
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'$USER_IP' WITH GRANT OPTION;

-- Accorder les privilèges au niveau global pour cette base spécifique
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, REFERENCES, INDEX, ALTER, 
      CREATE TEMPORARY TABLES, LOCK TABLES, EXECUTE, CREATE VIEW, SHOW VIEW, 
      CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER ON \`$DB_NAME\`.* TO '$DB_USER'@'$USER_IP';

-- Appliquer immédiatement
FLUSH PRIVILEGES;

-- Vérifier les privilèges accordés
SHOW GRANTS FOR '$DB_USER'@'$USER_IP';

-- Vérifier que la base existe et liste les tables
USE $DB_NAME;
SHOW TABLES;
EOF

echo -e "\n${GREEN}✓ Privilèges accordés avec succès !${NC}"
echo -e "\n${YELLOW}Test de connexion...${NC}"
mysql -u "$DB_USER" -p"$DB_PASSWORD" -h 127.0.0.1 "$DB_NAME" -e "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = '$DB_NAME';" 2>&1 | grep -v "Warning" || echo -e "${YELLOW}Test de connexion effectué${NC}"

echo -e "\n${GREEN}=== Configuration terminée ===${NC}"
echo -e "${YELLOW}Vous pouvez maintenant vous reconnecter dans DBeaver.${NC}"
