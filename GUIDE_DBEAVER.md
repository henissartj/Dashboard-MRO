# Guide de Configuration DBeaver - Base de Données bot_fazer

## Problème "Public Key Retrieval is not allowed"

Cette erreur est courante avec MySQL 8.0+ et DBeaver. Voici comment la résoudre :

### Solution 1 : Dans les Paramètres de Connexion DBeaver

1. Ouvrez DBeaver
2. Créez une nouvelle connexion MySQL ou modifiez une connexion existante
3. Dans l'onglet **"Paramètres"** (ou "Connection settings"), allez dans l'onglet **"Paramètres du pilote"** (Driver properties)
4. Cliquez sur **"Ajouter une propriété"** ou cherchez dans la liste
5. Ajoutez la propriété suivante :
   - **Nom** : `allowPublicKeyRetrieval`
   - **Valeur** : `true`
6. Cliquez sur **"OK"** ou **"Tester la connexion"**

### Solution 2 : Via l'URL de Connexion

1. Dans DBeaver, ouvrez les paramètres de votre connexion MySQL
2. Allez dans l'onglet **"Paramètres"**
3. Dans le champ **"URL"**, ajoutez à la fin : `&allowPublicKeyRetrieval=true`
4. L'URL complète devrait ressembler à :
   ```
   jdbc:mysql://45.80.148.228:3306/bot_fazer?allowPublicKeyRetrieval=true
   ```

### Solution 3 : Option Graphique (si disponible)

Certaines versions de DBeaver ont une case à cocher :
1. Dans les paramètres de connexion
2. Cherchez l'option **"Allow Public Key Retrieval"**
3. Cochez cette case

## Paramètres de Connexion Complets

| Paramètre | Valeur |
|-----------|--------|
| **Type de base de données** | MySQL |
| **Hôte** | `45.80.148.228` |
| **Port** | `3306` |
| **Base de données** | `bot_fazer` |
| **Utilisateur** | `dbeaver_user` |
| **Mot de passe** | (celui défini lors de la configuration) |
| **Propriété supplémentaire** | `allowPublicKeyRetrieval=true` |

## Sécurité - Accès Limité par IP

L'accès à la base de données est limité à votre IP spécifique pour des raisons de sécurité. Si votre IP change, vous devrez :

1. Exécuter à nouveau le script de configuration avec votre nouvelle IP
2. Ou modifier manuellement l'utilisateur MySQL :
   ```sql
   -- Se connecter à MySQL
   sudo mysql -u root
   
   -- Supprimer l'ancien accès
   DROP USER 'dbeaver_user'@'ANCIENNE_IP';
   
   -- Créer avec la nouvelle IP
   CREATE USER 'dbeaver_user'@'NOUVELLE_IP' IDENTIFIED BY 'votre_mot_de_passe';
   GRANT ALL PRIVILEGES ON `bot_fazer`.* TO 'dbeaver_user'@'NOUVELLE_IP';
   FLUSH PRIVILEGES;
   ```

## Vérification de la Connexion

Pour tester la connexion depuis votre terminal :

```bash
mysql -h 45.80.148.228 -u dbeaver_user -p bot_fazer
```

Entrez votre mot de passe lorsque demandé.

## Dépannage

### Erreur "Access denied"
- Vérifiez que votre IP correspond à celle configurée
- Vérifiez le mot de passe
- Vérifiez que le pare-feu autorise votre IP

### Erreur "Can't connect to MySQL server"
- Vérifiez que MySQL écoute sur toutes les interfaces : `sudo netstat -tlnp | grep 3306`
- Vérifiez que le pare-feu est configuré correctement
- Vérifiez que le service MySQL est démarré : `sudo systemctl status mysql`

### Erreur "Public Key Retrieval is not allowed"
- Suivez les solutions ci-dessus pour ajouter `allowPublicKeyRetrieval=true`

## Tables Principales de la Base bot_fazer

Une fois connecté, vous devriez voir des tables comme :
- `users` - Informations des utilisateurs Discord
- `transactions` - Historique des transactions
- `user_luxury` - Objets de luxe des utilisateurs
- Et d'autres tables selon votre configuration
