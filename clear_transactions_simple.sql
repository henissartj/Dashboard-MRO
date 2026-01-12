-- Script SQL simple pour vider la table transactions
-- Usage: sudo mysql -u root bot_fazer < clear_transactions_simple.sql

USE bot_fazer;

-- Afficher le nombre de transactions avant
SELECT COUNT(*) as 'Transactions avant suppression' FROM transactions;

-- Vider la table (TRUNCATE est plus rapide que DELETE)
TRUNCATE TABLE transactions;

-- Vérifier que la table est vide
SELECT COUNT(*) as 'Transactions après suppression' FROM transactions;

-- Réinitialiser l'auto-increment si nécessaire (optionnel)
-- ALTER TABLE transactions AUTO_INCREMENT = 1;
