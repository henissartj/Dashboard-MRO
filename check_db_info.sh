#!/bin/bash

# Script pour vérifier les informations sur la base de données existante

echo "=== Vérification de la Base de Données ==="
echo ""

# Vérifier MySQL/MariaDB
if command -v mysql &> /dev/null; then
    echo "✓ MySQL/MariaDB est installé"
    echo ""
    
    echo "Vérification des bases de données MySQL..."
    echo "Pour voir les bases de données, exécutez: sudo mysql -e 'SHOW DATABASES;'"
    echo ""
    
    # Vérifier si MySQL écoute
    if netstat -tlnp 2>/dev/null | grep -q 3306 || ss -tlnp 2>/dev/null | grep -q 3306; then
        echo "✓ MySQL écoute sur le port 3306"
        LISTENING=$(netstat -tlnp 2>/dev/null | grep 3306 || ss -tlnp 2>/dev/null | grep 3306)
        echo "  Détails: $LISTENING"
    else
        echo "✗ MySQL n'écoute pas sur le port 3306"
    fi
    echo ""
    
    # Vérifier bind-address
    MYSQL_CONF=""
    if [ -f "/etc/mysql/mysql.conf.d/mysqld.cnf" ]; then
        MYSQL_CONF="/etc/mysql/mysql.conf.d/mysqld.cnf"
    elif [ -f "/etc/mysql/mariadb.conf.d/50-server.cnf" ]; then
        MYSQL_CONF="/etc/mysql/mariadb.conf.d/50-server.cnf"
    fi
    
    if [ -n "$MYSQL_CONF" ]; then
        BIND_ADDRESS=$(grep "^bind-address" "$MYSQL_CONF" 2>/dev/null | awk '{print $3}')
        if [ -z "$BIND_ADDRESS" ]; then
            BIND_ADDRESS="127.0.0.1 (par défaut)"
        fi
        echo "bind-address actuel: $BIND_ADDRESS"
        if [ "$BIND_ADDRESS" != "0.0.0.0" ]; then
            echo "  ⚠️  L'accès distant n'est pas activé"
        else
            echo "  ✓ L'accès distant est activé"
        fi
    fi
    echo ""
fi

# Vérifier PostgreSQL
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL est installé"
    echo ""
    
    echo "Vérification des bases de données PostgreSQL..."
    echo "Pour voir les bases de données, exécutez: sudo -u postgres psql -l"
    echo ""
    
    # Vérifier si PostgreSQL écoute
    if netstat -tlnp 2>/dev/null | grep -q 5432 || ss -tlnp 2>/dev/null | grep -q 5432; then
        echo "✓ PostgreSQL écoute sur le port 5432"
        LISTENING=$(netstat -tlnp 2>/dev/null | grep 5432 || ss -tlnp 2>/dev/null | grep 5432)
        echo "  Détails: $LISTENING"
    else
        echo "✗ PostgreSQL n'écoute pas sur le port 5432"
    fi
    echo ""
    
    # Vérifier listen_addresses
    PG_VERSION=$(psql --version 2>/dev/null | grep -oP '\d+' | head -1)
    if [ -n "$PG_VERSION" ]; then
        PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
        if [ -f "$PG_CONF" ]; then
            LISTEN_ADDR=$(grep "^listen_addresses" "$PG_CONF" 2>/dev/null | awk '{print $3}' | tr -d "'")
            if [ -z "$LISTEN_ADDR" ]; then
                LISTEN_ADDR="localhost (par défaut)"
            fi
            echo "listen_addresses actuel: $LISTEN_ADDR"
            if [ "$LISTEN_ADDR" != "*" ]; then
                echo "  ⚠️  L'accès distant n'est pas activé"
            else
                echo "  ✓ L'accès distant est activé"
            fi
        fi
    fi
    echo ""
fi

# Vérifier SQLite
if command -v sqlite3 &> /dev/null; then
    echo "✓ SQLite est installé"
    echo "  Note: SQLite est un fichier local, pas besoin de configuration réseau"
    echo ""
fi

# Vérifier le pare-feu
echo "=== Vérification du Pare-feu ==="
if command -v ufw &> /dev/null; then
    echo "UFW est actif"
    UFW_STATUS=$(ufw status | head -1)
    echo "  $UFW_STATUS"
    echo ""
    echo "Ports ouverts pour MySQL (3306):"
    ufw status | grep 3306 || echo "  Port 3306 non ouvert"
    echo ""
    echo "Ports ouverts pour PostgreSQL (5432):"
    ufw status | grep 5432 || echo "  Port 5432 non ouvert"
elif command -v firewall-cmd &> /dev/null; then
    echo "Firewalld est actif"
    firewall-cmd --list-services | grep -q mysql && echo "  ✓ MySQL autorisé" || echo "  ✗ MySQL non autorisé"
    firewall-cmd --list-services | grep -q postgresql && echo "  ✓ PostgreSQL autorisé" || echo "  ✗ PostgreSQL non autorisé"
else
    echo "Aucun pare-feu géré détecté (vérifiez iptables manuellement)"
fi

echo ""
echo "=== Adresse IP du Serveur ==="
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "IP locale: $SERVER_IP"

# Essayer d'obtenir l'IP publique
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "Non disponible")
echo "IP publique: $PUBLIC_IP"

echo ""
echo "=== Prochaines Étapes ==="
echo "1. Identifiez le nom de votre base de données Discord"
echo "2. Exécutez le script de configuration: sudo ./setup_remote_db.sh"
echo "3. Configurez DBeaver avec les informations fournies"
echo "4. Consultez CONFIGURATION_DBEAVER.md pour plus de détails"
