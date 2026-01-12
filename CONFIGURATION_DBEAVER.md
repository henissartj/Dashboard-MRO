# Guide de Configuration - Accès DBeaver à la Base de Données Discord Bot

## Vue d'ensemble

Ce guide explique comment configurer l'accès à distance à votre base de données SQL depuis DBeaver sur votre VPS.

## Étapes de Configuration

### 1. Identifier le Type de Base de Données

Vérifiez quel système de base de données vous utilisez :
- **MySQL/MariaDB** : `mysql --version` ou `mariadb --version`
- **PostgreSQL** : `psql --version`
- **SQLite** : Ne nécessite pas de configuration réseau (fichier local)

### 2. Configuration MySQL/MariaDB pour Accès Distant

#### 2.1. Vérifier la Configuration MySQL

```bash
# Vérifier si MySQL écoute sur toutes les interfaces
sudo netstat -tlnp | grep mysql
# ou
sudo ss -tlnp | grep mysql
```

#### 2.2. Modifier la Configuration MySQL

Éditez le fichier de configuration MySQL :
```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
# ou pour MariaDB
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Modifiez la ligne `bind-address` :
```ini
# Changer de :
bind-address = 127.0.0.1

# À :
bind-address = 0.0.0.0
```

#### 2.3. Créer un Utilisateur avec Accès Distant

Connectez-vous à MySQL :
```bash
sudo mysql -u root -p
```

Exécutez les commandes suivantes :
```sql
-- Créer un utilisateur pour l'accès distant (remplacez 'username' et 'password')
CREATE USER 'dbeaver_user'@'%' IDENTIFIED BY 'votre_mot_de_passe_securise';

-- Accorder tous les privilèges sur la base de données Discord
GRANT ALL PRIVILEGES ON nom_de_votre_base.* TO 'dbeaver_user'@'%';

-- Ou accorder tous les privilèges sur toutes les bases (moins sécurisé)
-- GRANT ALL PRIVILEGES ON *.* TO 'dbeaver_user'@'%';

-- Appliquer les changements
FLUSH PRIVILEGES;

-- Vérifier les utilisateurs créés
SELECT user, host FROM mysql.user;

-- Quitter
EXIT;
```

#### 2.4. Configurer le Pare-feu

Autorisez le port MySQL (3306 par défaut) :
```bash
# UFW
sudo ufw allow 3306/tcp

# Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-service=mysql
sudo firewall-cmd --reload

# iptables
sudo iptables -A INPUT -p tcp --dport 3306 -j ACCEPT
```

#### 2.5. Redémarrer MySQL

```bash
sudo systemctl restart mysql
# ou
sudo systemctl restart mariadb
```

### 3. Configuration PostgreSQL pour Accès Distant

#### 3.1. Modifier postgresql.conf

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Modifiez la ligne :
```ini
listen_addresses = '*'
```

#### 3.2. Modifier pg_hba.conf

```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Ajoutez une ligne pour autoriser les connexions distantes :
```
host    all             all             0.0.0.0/0               md5
```

#### 3.3. Créer un Utilisateur PostgreSQL

```bash
sudo -u postgres psql
```

```sql
-- Créer un utilisateur
CREATE USER dbeaver_user WITH PASSWORD 'votre_mot_de_passe_securise';

-- Accorder les privilèges
GRANT ALL PRIVILEGES ON DATABASE nom_de_votre_base TO dbeaver_user;

-- Quitter
\q
```

#### 3.4. Configurer le Pare-feu

```bash
# UFW
sudo ufw allow 5432/tcp

# Firewalld
sudo firewall-cmd --permanent --add-service=postgresql
sudo firewall-cmd --reload
```

#### 3.5. Redémarrer PostgreSQL

```bash
sudo systemctl restart postgresql
```

### 4. Configuration dans DBeaver

#### 4.1. Créer une Nouvelle Connexion

1. Ouvrez DBeaver
2. Cliquez sur "Nouvelle Connexion" (icône prise)
3. Sélectionnez votre type de base de données (MySQL ou PostgreSQL)

#### 4.2. Paramètres de Connexion

**Pour MySQL/MariaDB :**
- **Hôte** : L'adresse IP publique de votre VPS
- **Port** : 3306 (par défaut)
- **Base de données** : Le nom de votre base de données Discord
- **Nom d'utilisateur** : dbeaver_user (ou celui que vous avez créé)
- **Mot de passe** : Le mot de passe que vous avez défini

**Pour PostgreSQL :**
- **Hôte** : L'adresse IP publique de votre VPS
- **Port** : 5432 (par défaut)
- **Base de données** : Le nom de votre base de données Discord
- **Nom d'utilisateur** : dbeaver_user
- **Mot de passe** : Le mot de passe que vous avez défini

#### 4.3. Tester la Connexion

Cliquez sur "Tester la connexion" pour vérifier que tout fonctionne.

### 5. Sécurité Recommandée

#### 5.1. Utiliser un VPN (Recommandé)

Pour une sécurité maximale, utilisez un VPN au lieu d'exposer directement le port de la base de données.

#### 5.2. Limiter l'Accès par IP

Au lieu de `'%'`, limitez l'accès à votre IP spécifique :
```sql
CREATE USER 'dbeaver_user'@'VOTRE_IP_PUBLIQUE' IDENTIFIED BY 'mot_de_passe';
```

#### 5.3. Utiliser SSL/TLS

Configurez SSL pour chiffrer les connexions :
- MySQL : Activez SSL dans la configuration
- PostgreSQL : Configurez SSL dans postgresql.conf

#### 5.4. Changer le Port par Défaut

Modifiez le port par défaut pour réduire les attaques automatisées :
- MySQL : Modifiez `port = 3306` dans mysqld.cnf
- PostgreSQL : Modifiez `port = 5432` dans postgresql.conf

### 6. Vérification et Dépannage

#### Vérifier que le Service Écoute Correctement

```bash
# MySQL
sudo netstat -tlnp | grep 3306

# PostgreSQL
sudo netstat -tlnp | grep 5432
```

#### Vérifier les Logs en Cas d'Erreur

```bash
# MySQL
sudo tail -f /var/log/mysql/error.log

# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*.log
```

#### Tester la Connexion depuis le Terminal

```bash
# MySQL
mysql -h VOTRE_IP_VPS -u dbeaver_user -p

# PostgreSQL
psql -h VOTRE_IP_VPS -U dbeaver_user -d nom_de_votre_base
```

## Notes Importantes

- **Sécurité** : Exposer une base de données sur Internet présente des risques. Utilisez des mots de passe forts et considérez l'utilisation d'un VPN.
- **Performance** : Les connexions distantes peuvent être plus lentes que les connexions locales.
- **Backup** : Assurez-vous d'avoir des sauvegardes régulières de votre base de données.
