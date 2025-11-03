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

## Analogie (masse–ressort–freins)
- \(k\) est le ressort (tension de rappel)
- \(\gamma\) est le frein (dissipation)
- \(m\) est l’inertie (lenteur au changement)

## Conseils d’exploration
- Jouez avec \( \gamma \) pour voir la transition oscillant → non-oscillant.
- Comparez plusieurs réglages avec “Comparaison multi-paramètres”.
- Observez l’effet de \(t_{\text{end}}\) sur la FFT (résolution spectrale).

"""

layout = html.Div([
    dcc.Markdown(md, mathjax=True),
], style={"maxWidth": "900px", "margin": "0 auto", "padding": "24px"})

