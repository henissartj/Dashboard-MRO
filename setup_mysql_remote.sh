#!/bin/bash

# Script spécifique pour configurer l'accès distant MySQL pour la base "bot_fazer"

set -e

DB_NAME="bot_fazer"
DB_USER="dbeaver_user"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Configuration MySQL pour DBeaver ===${NC}\n"
echo -e "${YELLOW}Base de données: $DB_NAME${NC}\n"

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

# Trouver le fichier de configuration MySQL
MYSQL_CONF=""
if [ -f "/etc/mysql/mysql.conf.d/mysqld.cnf" ]; then
    MYSQL_CONF="/etc/mysql/mysql.conf.d/mysqld.cnf"
elif [ -f "/etc/mysql/mariadb.conf.d/50-server.cnf" ]; then
    MYSQL_CONF="/etc/mysql/mariadb.conf.d/50-server.cnf"
elif [ -f "/etc/my.cnf" ]; then
    MYSQL_CONF="/etc/my.cnf"
fi

if [ -z "$MYSQL_CONF" ]; then
    echo -e "${RED}Erreur: Fichier de configuration MySQL non trouvé${NC}"
    echo -e "${YELLOW}Recherche dans les emplacements standards...${NC}"
    find /etc -name "mysqld.cnf" -o -name "50-server.cnf" 2>/dev/null | head -1
    exit 1
fi

echo -e "${GREEN}✓ Fichier de configuration trouvé: $MYSQL_CONF${NC}"

# Sauvegarder la configuration
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
cp "$MYSQL_CONF" "${MYSQL_CONF}.backup.$BACKUP_DATE"
echo -e "${GREEN}✓ Configuration sauvegardée${NC}"

# Modifier bind-address
echo -e "${YELLOW}Configuration de bind-address...${NC}"
if grep -q "^bind-address" "$MYSQL_CONF"; then
    sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' "$MYSQL_CONF"
    echo -e "${GREEN}✓ bind-address modifié en 0.0.0.0${NC}"
else
    # Chercher dans la section [mysqld]
    if grep -q "^\[mysqld\]" "$MYSQL_CONF"; then
        sed -i '/^\[mysqld\]/a bind-address = 0.0.0.0' "$MYSQL_CONF"
    else
        echo "" >> "$MYSQL_CONF"
        echo "[mysqld]" >> "$MYSQL_CONF"
        echo "bind-address = 0.0.0.0" >> "$MYSQL_CONF"
    fi
    echo -e "${GREEN}✓ bind-address ajouté (0.0.0.0)${NC}"
fi

# Vérifier que la base de données existe
echo -e "${YELLOW}Vérification de la base de données...${NC}"
DB_EXISTS=$(mysql -u root -e "SHOW DATABASES LIKE '$DB_NAME';" 2>/dev/null | grep -c "$DB_NAME" || echo "0")
if [ "$DB_EXISTS" = "0" ]; then
    echo -e "${RED}⚠️  Attention: La base de données '$DB_NAME' n'existe pas encore${NC}"
    read -p "Voulez-vous continuer quand même ? (o/n): " CONTINUE
    if [ "$CONTINUE" != "o" ] && [ "$CONTINUE" != "O" ]; then
        echo "Annulation..."
        exit 1
    fi
else
    echo -e "${GREEN}✓ Base de données '$DB_NAME' trouvée${NC}"
fi

# Créer l'utilisateur MySQL
echo -e "${YELLOW}Création de l'utilisateur MySQL...${NC}"
mysql -u root <<EOF
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
SELECT user, host FROM mysql.user WHERE user = '$DB_USER';
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Utilisateur créé avec succès${NC}"
else
    echo -e "${RED}✗ Erreur lors de la création de l'utilisateur${NC}"
    exit 1
fi

# Configurer le pare-feu
echo -e "${YELLOW}Configuration du pare-feu...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 3306/tcp
    echo -e "${GREEN}✓ Port 3306 autorisé dans UFW${NC}"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=mysql
    firewall-cmd --reload
    echo -e "${GREEN}✓ Port MySQL autorisé dans firewalld${NC}"
else
    echo -e "${YELLOW}⚠ Aucun pare-feu géré détecté, configurez manuellement${NC}"
fi

# Redémarrer MySQL
echo -e "${YELLOW}Redémarrage de MySQL...${NC}"
if systemctl is-active --quiet mysql 2>/dev/null; then
    systemctl restart mysql
    SERVICE_NAME="mysql"
elif systemctl is-active --quiet mariadb 2>/dev/null; then
    systemctl restart mariadb
    SERVICE_NAME="mariadb"
else
    echo -e "${RED}✗ Service MySQL/MariaDB non trouvé${NC}"
    exit 1
fi

sleep 2

if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ $SERVICE_NAME redémarré avec succès${NC}"
else
    echo -e "${RED}✗ Erreur lors du redémarrage de $SERVICE_NAME${NC}"
    exit 1
fi

# Vérifier que MySQL écoute sur toutes les interfaces
echo -e "${YELLOW}Vérification de l'écoute...${NC}"
LISTENING=$(netstat -tlnp 2>/dev/null | grep 3306 || ss -tlnp 2>/dev/null | grep 3306)
if echo "$LISTENING" | grep -q "0.0.0.0:3306\|:::3306"; then
    echo -e "${GREEN}✓ MySQL écoute sur toutes les interfaces${NC}"
    echo "  $LISTENING"
else
    echo -e "${YELLOW}⚠ MySQL pourrait ne pas écouter sur toutes les interfaces${NC}"
    echo "  $LISTENING"
fi

# Afficher les informations de connexion
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "\n${GREEN}=== Configuration terminée avec succès ! ===${NC}\n"
echo -e "${YELLOW}Informations pour DBeaver:${NC}"
echo -e "  Hôte: ${GREEN}$SERVER_IP${NC}"
echo -e "  Port: ${GREEN}3306${NC}"
echo -e "  Base de données: ${GREEN}$DB_NAME${NC}"
echo -e "  Utilisateur: ${GREEN}$DB_USER${NC}"
echo -e "  Mot de passe: ${GREEN}[celui que vous avez défini]${NC}"
echo -e "\n${YELLOW}Vérification:${NC}"
echo -e "  Pour tester: mysql -h $SERVER_IP -u $DB_USER -p $DB_NAME"
echo -e "\n${YELLOW}⚠️  Note de sécurité:${NC}"
echo -e "  L'accès est ouvert à toutes les IPs (%)"
echo -e "  Pour plus de sécurité, limitez l'accès à votre IP spécifique"
