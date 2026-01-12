#!/bin/bash

# Script pour vider la table transactions

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

echo -e "${YELLOW}=== Vider la table transactions ===${NC}\n"

if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Erreur: Ce script doit être exécuté avec sudo${NC}"
    exit 1
fi

# Demander confirmation
echo -e "${RED}⚠️  ATTENTION: Cette opération va supprimer TOUTES les données de la table 'transactions'${NC}"
echo -e "${YELLOW}Voulez-vous créer une sauvegarde avant de vider la table ? (o/n):${NC}"
read -p "> " BACKUP_CHOICE

if [ "$BACKUP_CHOICE" = "o" ] || [ "$BACKUP_CHOICE" = "O" ]; then
    BACKUP_FILE="/opt/mro_dash/backup_transactions_$(date +%Y%m%d_%H%M%S).sql"
    echo -e "${YELLOW}Création de la sauvegarde...${NC}"
    mysqldump -u root "$DB_NAME" transactions > "$BACKUP_FILE" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Sauvegarde créée: $BACKUP_FILE${NC}"
    else
        echo -e "${RED}✗ Erreur lors de la création de la sauvegarde${NC}"
        read -p "Continuer quand même ? (o/n): " CONTINUE
        if [ "$CONTINUE" != "o" ] && [ "$CONTINUE" != "O" ]; then
            echo "Annulation..."
            exit 0
        fi
    fi
fi

# Demander confirmation finale
echo -e "\n${RED}Êtes-vous sûr de vouloir vider la table 'transactions' ? (oui/non):${NC}"
read -p "> " CONFIRM

if [ "$CONFIRM" != "oui" ]; then
    echo -e "${YELLOW}Opération annulée.${NC}"
    exit 0
fi

# Compter les lignes avant suppression
echo -e "\n${YELLOW}Comptage des lignes avant suppression...${NC}"
COUNT_BEFORE=$(mysql -u root "$DB_NAME" -e "SELECT COUNT(*) as count FROM transactions;" 2>/dev/null | tail -1)
echo -e "${BLUE}Nombre de transactions avant: $COUNT_BEFORE${NC}"

# Vider la table
echo -e "\n${YELLOW}Vidage de la table transactions...${NC}"
mysql -u root "$DB_NAME" <<EOF
TRUNCATE TABLE transactions;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Table 'transactions' vidée avec succès${NC}"
    
    # Vérifier
    COUNT_AFTER=$(mysql -u root "$DB_NAME" -e "SELECT COUNT(*) as count FROM transactions;" 2>/dev/null | tail -1)
    echo -e "${BLUE}Nombre de transactions après: $COUNT_AFTER${NC}"
    
    if [ "$COUNT_AFTER" = "0" ]; then
        echo -e "\n${GREEN}✓✓✓ Table complètement vidée ✓✓✓${NC}"
    else
        echo -e "\n${YELLOW}⚠ La table n'est pas complètement vide (peut être normal selon la configuration)${NC}"
    fi
else
    echo -e "\n${RED}✗ Erreur lors du vidage de la table${NC}"
    exit 1
fi
