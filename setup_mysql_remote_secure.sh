#!/bin/bash

# Script pour configurer l'accès distant MySQL avec limitation par IP

set -e

DB_NAME="bot_fazer"
DB_USER="dbeaver_user"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Configuration MySQL sécurisée pour DBeaver ===${NC}\n"
echo -e "${YELLOW}Base de données: $DB_NAME${NC}\n"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Erreur: Ce script doit être exécuté avec sudo${NC}"
    exit 1
fi

# Demander l'IP de l'utilisateur
echo -e "${BLUE}Pour des raisons de sécurité, l'accès sera limité à votre IP spécifique.${NC}"
read -p "Votre adresse IP publique (ou appuyez sur Entrée pour auto-détection): " USER_IP

if [ -z "$USER_IP" ]; then
    echo -e "${YELLOW}Détection automatique de votre IP...${NC}"
    USER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "")
    if [ -z "$USER_IP" ]; then
        echo -e "${RED}Impossible de détecter votre IP automatiquement${NC}"
        read -p "Veuillez entrer votre adresse IP publique: " USER_IP
        if [ -z "$USER_IP" ]; then
            echo -e "${RED}Erreur: IP requise${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}IP détectée: $USER_IP${NC}"
    fi
fi

# Valider le format IP (basique)
if ! [[ $USER_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo -e "${RED}Format d'IP invalide: $USER_IP${NC}"
    exit 1
fi

echo -e "${GREEN}✓ IP configurée: $USER_IP${NC}\n"

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

# Créer l'utilisateur MySQL avec limitation IP
echo -e "${YELLOW}Création de l'utilisateur MySQL (accès limité à $USER_IP)...${NC}"
mysql -u root <<EOF
-- Supprimer l'utilisateur s'il existe déjà avec %
DROP USER IF EXISTS '$DB_USER'@'%';

-- Créer l'utilisateur avec accès limité à votre IP
CREATE USER '$DB_USER'@'$USER_IP' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'$USER_IP';
FLUSH PRIVILEGES;

-- Afficher les utilisateurs créés
SELECT user, host FROM mysql.user WHERE user = '$DB_USER';
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Utilisateur créé avec succès (accès limité à $USER_IP)${NC}"
else
    echo -e "${RED}✗ Erreur lors de la création de l'utilisateur${NC}"
    exit 1
fi

# Configurer le pare-feu (optionnel, mais recommandé)
echo -e "${YELLOW}Configuration du pare-feu...${NC}"
if command -v ufw &> /dev/null; then
    # Autoriser uniquement depuis votre IP
    ufw allow from $USER_IP to any port 3306 proto tcp
    echo -e "${GREEN}✓ Port 3306 autorisé uniquement depuis $USER_IP dans UFW${NC}"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-rich-rule="rule family='ipv4' source address='$USER_IP' port port='3306' protocol='tcp' accept"
    firewall-cmd --reload
    echo -e "${GREEN}✓ Port MySQL autorisé uniquement depuis $USER_IP dans firewalld${NC}"
else
    echo -e "${YELLOW}⚠ Aucun pare-feu géré détecté${NC}"
    echo -e "${YELLOW}  Configurez manuellement pour autoriser uniquement $USER_IP sur le port 3306${NC}"
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
echo -e "\n${BLUE}⚠️  IMPORTANT - Configuration DBeaver:${NC}"
echo -e "  Dans DBeaver, allez dans l'onglet 'Paramètres du pilote'"
echo -e "  Ajoutez cette propriété: ${GREEN}allowPublicKeyRetrieval=true${NC}"
echo -e "  Ou cochez l'option 'Allow Public Key Retrieval' si disponible"
echo -e "\n${YELLOW}Vérification:${NC}"
echo -e "  Pour tester: mysql -h $SERVER_IP -u $DB_USER -p $DB_NAME"
echo -e "\n${GREEN}✓ Sécurité: Accès limité uniquement à votre IP ($USER_IP)${NC}"
