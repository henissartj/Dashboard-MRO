#!/bin/bash

# Script final pour corriger définitivement les permissions

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

echo -e "${GREEN}=== Correction FINALE des permissions ===${NC}\n"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Erreur: Ce script doit être exécuté avec sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}Veuillez entrer le mot de passe pour $DB_USER:${NC}"
read -sp "Mot de passe: " DB_PASSWORD
echo ""

if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Erreur: Le mot de passe est requis${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Étape 1: Suppression complète de l'utilisateur...${NC}"
mysql -u root <<EOF
DROP USER IF EXISTS '$DB_USER'@'$USER_IP';
DROP USER IF EXISTS '$DB_USER'@'%';
FLUSH PRIVILEGES;
EOF

echo -e "${GREEN}✓ Utilisateur supprimé${NC}"

echo -e "\n${YELLOW}Étape 2: Création de l'utilisateur avec mot de passe...${NC}"
mysql -u root <<EOF
CREATE USER '$DB_USER'@'$USER_IP' IDENTIFIED BY '$DB_PASSWORD';
FLUSH PRIVILEGES;
EOF

echo -e "${GREEN}✓ Utilisateur créé${NC}"

echo -e "\n${YELLOW}Étape 3: Attribution de TOUS les privilèges sur bot_fazer...${NC}"
mysql -u root <<EOF
-- Accorder tous les privilèges avec GRANT OPTION
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'$USER_IP' WITH GRANT OPTION;

-- Privilèges explicites au cas où
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, REFERENCES, INDEX, ALTER, 
      CREATE TEMPORARY TABLES, LOCK TABLES, EXECUTE, CREATE VIEW, SHOW VIEW, 
      CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER ON \`$DB_NAME\`.* TO '$DB_USER'@'$USER_IP';

FLUSH PRIVILEGES;
EOF

echo -e "${GREEN}✓ Privilèges accordés${NC}"

echo -e "\n${YELLOW}Étape 4: Vérification des privilèges...${NC}"
mysql -u root <<EOF
SHOW GRANTS FOR '$DB_USER'@'$USER_IP';
EOF

echo -e "\n${YELLOW}Étape 5: Test de connexion avec les nouvelles permissions...${NC}"
mysql -u "$DB_USER" -p"$DB_PASSWORD" -h 127.0.0.1 "$DB_NAME" <<EOF
SELECT 'Connexion réussie!' as status;
SELECT COUNT(*) as user_count FROM users;
SHOW TABLES;
EOF

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓✓✓ Test de connexion RÉUSSI ! ✓✓✓${NC}"
    echo -e "\n${BLUE}Les permissions sont maintenant correctement configurées.${NC}"
    echo -e "${YELLOW}Vous pouvez vous reconnecter dans DBeaver.${NC}"
    echo -e "\n${BLUE}IMPORTANT:${NC}"
    echo -e "${YELLOW}Assurez-vous d'être connecté à la base 'bot_fazer' dans DBeaver,${NC}"
    echo -e "${YELLOW}et utilisez 'users' (avec 's') et non 'user' (sans 's').${NC}"
else
    echo -e "\n${RED}✗ Erreur lors du test de connexion${NC}"
    exit 1
fi
