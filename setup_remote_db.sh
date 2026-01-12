#!/bin/bash

# Script de configuration pour l'accès distant à la base de données
# Usage: sudo ./setup_remote_db.sh [mysql|postgresql]

set -e

DB_TYPE=${1:-mysql}
DB_NAME=""
DB_USER="dbeaver_user"
DB_PASSWORD=""

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Configuration de l'accès distant à la base de données ===${NC}\n"

# Vérifier que le script est exécuté en tant que root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Erreur: Ce script doit être exécuté avec sudo${NC}"
    exit 1
fi

# Détecter le type de base de données si non spécifié
if [ -z "$1" ]; then
    if command -v mysql &> /dev/null; then
        DB_TYPE="mysql"
        echo -e "${GREEN}MySQL/MariaDB détecté${NC}"
    elif command -v psql &> /dev/null; then
        DB_TYPE="postgresql"
        echo -e "${GREEN}PostgreSQL détecté${NC}"
    else
        echo -e "${RED}Erreur: Aucune base de données SQL détectée${NC}"
        exit 1
    fi
fi

# Demander le nom de la base de données
read -p "Nom de la base de données Discord: " DB_NAME
if [ -z "$DB_NAME" ]; then
    echo -e "${RED}Erreur: Le nom de la base de données est requis${NC}"
    exit 1
fi

# Demander le mot de passe
read -sp "Mot de passe pour l'utilisateur $DB_USER: " DB_PASSWORD
echo ""
if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Erreur: Le mot de passe est requis${NC}"
    exit 1
fi

if [ "$DB_TYPE" = "mysql" ]; then
    echo -e "\n${YELLOW}Configuration de MySQL/MariaDB...${NC}"
    
    # Trouver le fichier de configuration
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
    
    # Sauvegarder la configuration
    cp "$MYSQL_CONF" "${MYSQL_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}Configuration sauvegardée${NC}"
    
    # Modifier bind-address
    if grep -q "^bind-address" "$MYSQL_CONF"; then
        sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' "$MYSQL_CONF"
    else
        echo "bind-address = 0.0.0.0" >> "$MYSQL_CONF"
    fi
    echo -e "${GREEN}bind-address configuré sur 0.0.0.0${NC}"
    
    # Créer l'utilisateur MySQL
    echo -e "${YELLOW}Création de l'utilisateur MySQL...${NC}"
    mysql -u root <<EOF
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
EOF
    
    echo -e "${GREEN}Utilisateur MySQL créé${NC}"
    
    # Configurer le pare-feu
    if command -v ufw &> /dev/null; then
        ufw allow 3306/tcp
        echo -e "${GREEN}Port 3306 autorisé dans UFW${NC}"
    fi
    
    # Redémarrer MySQL
    if systemctl is-active --quiet mysql; then
        systemctl restart mysql
    elif systemctl is-active --quiet mariadb; then
        systemctl restart mariadb
    fi
    echo -e "${GREEN}MySQL redémarré${NC}"
    
    echo -e "\n${GREEN}=== Configuration MySQL terminée ===${NC}"
    echo -e "Port: ${YELLOW}3306${NC}"
    echo -e "Utilisateur: ${YELLOW}$DB_USER${NC}"
    echo -e "Base de données: ${YELLOW}$DB_NAME${NC}"
    
elif [ "$DB_TYPE" = "postgresql" ]; then
    echo -e "\n${YELLOW}Configuration de PostgreSQL...${NC}"
    
    # Trouver le répertoire de configuration PostgreSQL
    PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
    PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
    PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    
    if [ ! -f "$PG_CONF" ]; then
        echo -e "${RED}Erreur: Fichier de configuration PostgreSQL non trouvé${NC}"
        exit 1
    fi
    
    # Sauvegarder les configurations
    cp "$PG_CONF" "${PG_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$PG_HBA" "${PG_HBA}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}Configurations sauvegardées${NC}"
    
    # Modifier postgresql.conf
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
    if ! grep -q "^listen_addresses" "$PG_CONF"; then
        echo "listen_addresses = '*'" >> "$PG_CONF"
    fi
    echo -e "${GREEN}listen_addresses configuré${NC}"
    
    # Modifier pg_hba.conf
    if ! grep -q "host.*all.*all.*0.0.0.0/0.*md5" "$PG_HBA"; then
        echo "host    all             all             0.0.0.0/0               md5" >> "$PG_HBA"
    fi
    echo -e "${GREEN}pg_hba.conf mis à jour${NC}"
    
    # Créer l'utilisateur PostgreSQL
    echo -e "${YELLOW}Création de l'utilisateur PostgreSQL...${NC}"
    sudo -u postgres psql <<EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\q
EOF
    
    echo -e "${GREEN}Utilisateur PostgreSQL créé${NC}"
    
    # Configurer le pare-feu
    if command -v ufw &> /dev/null; then
        ufw allow 5432/tcp
        echo -e "${GREEN}Port 5432 autorisé dans UFW${NC}"
    fi
    
    # Redémarrer PostgreSQL
    systemctl restart postgresql
    echo -e "${GREEN}PostgreSQL redémarré${NC}"
    
    echo -e "\n${GREEN}=== Configuration PostgreSQL terminée ===${NC}"
    echo -e "Port: ${YELLOW}5432${NC}"
    echo -e "Utilisateur: ${YELLOW}$DB_USER${NC}"
    echo -e "Base de données: ${YELLOW}$DB_NAME${NC}"
fi

# Obtenir l'adresse IP du serveur
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "\n${GREEN}=== Informations de Connexion DBeaver ===${NC}"
echo -e "Hôte: ${YELLOW}$SERVER_IP${NC}"
if [ "$DB_TYPE" = "mysql" ]; then
    echo -e "Port: ${YELLOW}3306${NC}"
else
    echo -e "Port: ${YELLOW}5432${NC}"
fi
echo -e "Base de données: ${YELLOW}$DB_NAME${NC}"
echo -e "Utilisateur: ${YELLOW}$DB_USER${NC}"
echo -e "\n${YELLOW}⚠️  Attention: Assurez-vous que votre pare-feu autorise les connexions entrantes${NC}"
echo -e "${YELLOW}⚠️  Pour plus de sécurité, considérez l'utilisation d'un VPN${NC}"
