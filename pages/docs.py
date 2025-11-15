import dash
from dash import dcc, html

dash.register_page(__name__, path="/docs")

md = r"""
# Explications — Modèle de Résonance Ontogénétique (MRO)

## Idée de base
Le MRO modélise une grandeur \(x(t)\) soumise à une **tension ontogénétique** \(k\) et un **amortissement** \(\gamma\).
L'équation différentielle (homogène) utilisée ici est l’oscillateur amorti :
\[
\ddot x + \frac{\gamma}{m} \dot x + \frac{k}{m} x = 0
\]
- \(m\) : masse « métaphorique » (inertie du système)
- \(\gamma\) : amortissement (perte d'énergie / dissipation)
- \(k\) : tension / rappel ontogénétique (force vers un état de cohérence)

## Régimes dynamiques
- **Sous-amorti** : \( \gamma^2 < 4mk \) → oscillations décroissantes
- **Critique** : \( \gamma^2 = 4mk \) → retour le plus rapide sans oscillation
- **Sur-amorti** : \( \gamma^2 > 4mk \) → retour lent, sans oscillation

## Lecture publique
- Le graphe **x(t)** montre la mémoire dynamique du système et sa vitesse de stabilisation.
- L’**espace des phases** (x, dx/dt) visualise la trajectoire vers l’équilibre (spirale / ligne).
- La **heatmap** (γ, k) indique où l’amplitude maximale reste forte/faible.
- La **FFT** révèle les fréquences dominantes résiduelles.

## Schémas explicatifs (statiques)
Les deux schémas suivants illustrent le flux du modèle et la typologie des régimes.

"""

layout = html.Div([
    dcc.Markdown(md, mathjax=True),
    html.Div(style={"height": "16px"}),
    dcc.Markdown(r"""
## Sans schémas — explication textuelle

### Flux du modèle MRO
- Les paramètres d’entrée (m, γ, k) définissent l’inertie, la dissipation et la tension du système.
- L’oscillateur amorti transforme ces paramètres en une dynamique temporelle x(t).
- On lit ensuite trois sorties complémentaires :
  1. x(t) pour la stabilité et la mémoire dynamique,
  2. l’espace des phases (x, dx/dt) pour la trajectoire vers l’équilibre,
  3. la FFT pour repérer les fréquences résiduelles.

### Typologie des régimes
- Sous-amorti (γ² < 4mk) : oscillations décroissantes avant stabilisation.
- Critique (γ² = 4mk) : retour le plus rapide sans oscillation.
- Sur-amorti (γ² > 4mk) : retour monotone, plus lent.

### Conseils de lecture
- Commencer par x(t) pour situer la dynamique générale.
- Regarder l’espace des phases pour comprendre la forme de la trajectoire.
- Utiliser la FFT si vous cherchez une empreinte fréquentielle.
""", mathjax=True),
], style={"maxWidth": "900px", "margin": "0 auto", "padding": "24px"})
