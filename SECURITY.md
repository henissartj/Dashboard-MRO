# Security Policy

Le projet **Dashboard-MRO** est distribué sous licence MIT et proposé à des fins scientifiques, pédagogiques et expérimentales. Bien que le code ne traite aucune donnée sensible et ne collecte aucune information utilisateur, certaines vulnérabilités (ex. dépendances Python, exécutions serveur, configuration Dash) peuvent représenter un risque lorsqu’il est déployé publiquement.

Merci de suivre les règles ci-dessous si vous identifiez un problème de sécurité.

---

## 📌 Versions supportées

Le projet n’a pas de cycle de versions complexe. En pratique :

| Version          | Support |
|------------------|---------|
| `v1.x` (actuelle) | ✅ Actif |
| `v0.x` (anciennes) | ❌ Non supportées |
| Versions modifiées par des tiers | ❌ Hors périmètre |

Les correctifs de sécurité ne sont appliqués **que** à la branche `vps`.

---

## 🔒 Surface d’exposition potentielle

Le projet **ne gère aucune authentification** et **n’écrit aucun état utilisateur**.  
Les seules surfaces théoriques sont :

- dépendances Python (Dash, Plotly, Flask)
- librairies de rendu client
- configuration Nginx/Gunicorn de déploiement
- scripts ZIP/Export

---

## 🚨 Signaler une vulnérabilité

Merci de **ne pas** ouvrir d’Issue publique.

**Contact privé recommandé :**

- Via l’onglet “Security Advisory” sur GitHub
- Par e-mail (si présent dans le profil GitHub)
- Via message GitHub privé (preferred)

Décrivez :

1. La nature du problème
2. La méthode de reproduction
3. L’impact potentiel
4. Les plateformes concernées
5. Une éventuelle solution proposée

---

## ⏱️ Délai de réponse

Expectations réalistes :

- Réponse initiale : **2–7 jours**
- Analyse interne : **1–2 semaines**
- Correctif (si confirmé) : **variable** selon complexité

---

## ✅ Processus interne

Lorsqu’une vulnérabilité est confirmée :

- correction appliquée dans une branche privée
- validation locale
- publication patchée en `vps`
- mise à jour du CHANGELOG
- badge de version mis à jour

---

## ❌ Ce qui n’est pas considéré comme une vulnérabilité

- suggestions de fonctionnalité
- demandes d’optimisation non sécuritaire
- attaque nécessitant accès root local
- abus de navigateur volontaire
- modifications utilisateur non officielles

---

## ⚠️ Avertissement légal

Toute tentative d’exploitation destructrice, de déni de service, de compromission serveur ou de découverte volontaire d’accès non autorisés **constitue une activité illégale** et pourra entraîner un signalement.

---

## 💬 Remerciements

Toutes les contributions responsables (même discrètes) sont notées dans les Release Notes de sécurité.

Merci d’aider à maintenir un outil scientifique propre, fiable et reproductible.
