import dash
from dash import dcc, html

dash.register_page(__name__, path="/docs")

md = r"""
# Documentation — Modèle de Résonance Ontogénétique (MRO)

## Idée de base
Le MRO modélise une grandeur \(x(t)\) soumise à une **tension ontogénétique** \(k\) et un **amortissement** \(\gamma\). Le comportement est celui d’un oscillateur amorti homogène :
\[
\ddot x + \frac{\gamma}{m} \dot x + \frac{k}{m} x = 0
\]

## Paramètres
- \(m\) : inertie du système (réactivité globale)
- \(\gamma\) : dissipation (vitesse d’extinction des oscillations)
- \(k\) : tension/rappel ontogénétique (structure la fréquence naturelle)
- \(x(0)\), \(\dot x(0)\) : conditions initiales
- \(t_{end}\) : durée de simulation

## Régimes dynamiques
- **Sous-amorti** : \( \gamma^2 < 4mk \) → oscillations décroissantes
- **Critique** : \( \gamma^2 = 4mk \) → retour le plus rapide sans oscillation
- **Sur-amorti** : \( \gamma^2 > 4mk \) → retour monotone, plus lent

## Outils du tableau de bord
- **x(t)** : série temporelle et annotations (clic pour annoter, outils de dessin)
- **Espace des phases** \((x, \dot x)\) : trajectoire vers l’équilibre
- **Énergie** : \(E_{kin} = \tfrac{1}{2} m \dot x^2\), \(E_{pot} = \tfrac{1}{2} k x^2\), \(E_{tot} = E_{kin}+E_{pot}\)
- **Accélération** : \(\ddot x = -\tfrac{\gamma}{m}\,\dot x - \tfrac{k}{m} x\)
- **Heatmap (γ, k)** : amplitude maximale \(\max |x(t)|\) sur le plan des paramètres
- **FFT** : empreinte fréquentielle résiduelle
- **Exports** : PNG/SVG/ZIP des figures et comparaisons

## Conseils de lecture
- Commencer par **x(t)** pour situer la dynamique générale
- Examiner l’**espace des phases** pour la forme de la trajectoire
- Utiliser la **FFT** pour repérer d’éventuelles fréquences dominantes
- Explorer la **heatmap** pour cartographier les effets de \(\gamma\) et \(k\)

## Liens utiles
- [Simulations](/)
- [FFT](/fft)
- [Heatmap 3D](/heatmap3d)
- [Crédits](/credits)
- [Code source](/repository)
"""

layout = html.Div([
    dcc.Markdown(md, mathjax=True),
], style={"maxWidth": "900px", "margin": "0 auto", "padding": "24px"})
