<p align="center">

  <!-- Version du dépôt -->
  <img alt="Latest Release" src="https://img.shields.io/github/v/release/henissartj/Dashboard-MRO?style=for-the-badge">

  <!-- Licence -->
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge">

  <!-- ORCID -->
  <img alt="ORCID" src="https://img.shields.io/badge/ORCID-0009--0007--1822--5741-A6CE39?style=for-the-badge&logo=orcid">

</p>

<p align="center">
  <img src="assets/screenshot_home.png" alt="Dashboard MRO — Accueil" width="860">
</p>

# Dashboard MRO – Modèle de Résonance Ontogénétique

**Visualisation, exploration et expérimentation interactive** autour du Modèle de Résonance Ontogénétique (MRO) :  
une hypothèse dynamique visant à modéliser la mémoire, la plasticité et l’émergence de forme dans les systèmes vivants et symboliques.

👉 Démo : https://epheverisme.art  
👉 Article TechRxiv : https://doi.org/10.22541/au.176175046.68446609/v1  
👉 Auteur : Jules Henissart-Miquel (ORCID : https://orcid.org/0009-0007-1822-5741)

---

## ✨ Objectifs du projet

Ce tableau de bord permet :

- de **simuler** des oscillations amorties (MRO),
- d’**explorer** l’influence des paramètres dynamiques,
- de **visualiser** les trajectoires en espace des phases,
- de **analyser** le spectre fréquentiel (FFT),
- de **cartographier** (heatmap) la dynamique selon `(γ, k)`,
- de **comparer** plusieurs configurations paramétriques,
- d’**exporter** automatiquement des figures scientifiques (PNG/SVG/ZIP),
- de **conduire** des tests reproductibles.

Il sert autant à la recherche conceptuelle qu’à la pédagogie numérique.

---

## 🧠 Concepts théoriques mobilisés

Le MRO propose un lien formel entre :

| Phénomène | Signature dynamique |
|----------|---------------------|
| **Information** | Contraction dans l’espace des phases |
| **Mémoire** | Déformation topologique progressive |
| **Plasticité** | Modulation paramétrique lente |
| **Ontogenèse** | Persistance structurelle de la résonance |
| **Dissipation constructive** | Inscription temporelle non triviale |

Le système illustre :
- la zone morte (γ → 0, aucune écriture),
- la zone dissipative (γ → ∞, extinction rapide),
- la **bande vivante** où l’histoire apparaît.

---

## 🧩 Fonctionnalités

### 🔭 Série temporelle `x(t)`
Visualisation de la décroissance amortie et comportement global dans le temps.

### 🌀 Espace des phases `(x, dx/dt)`
Permet d’identifier :
- attracteurs,
- spirales convergentes,
- stabilité orbitale.

### 🔥 Heatmap `(γ, k)`
Cartographie du maximum d’amplitude selon :
- tension ontogénétique,
- dissipation.

### 📊 Comparaison multi-paramètres
Ajout de presets et overlay de plusieurs séries.

### 🔈 FFT
Isolation de la fréquence dominante (signature spectrale).

### 📦 Export
- PNG HD,
- SVG,
- ZIP automatisé,
- README exploratoire embarqué.

---

## ⚙️ Installation (développement local)

```bash
git clone https://github.com/henissartj/Dashboard-MRO.git
cd Dashboard-MRO

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python app.py
