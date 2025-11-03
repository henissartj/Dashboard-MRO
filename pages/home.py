import dash
from dash import dcc, html
import dash_bootstrap_components as dbc  # <— pour les tooltips

dash.register_page(__name__, path="/")

intro_md = """
# Modèle de Résonance Ontogénétique (MRO)

Cette page présente des visualisations interactives du MRO :
- **Série temporelle** de x(t)
- **Espace des phases** (x, dx/dt)
- **Heatmap** du maximum d'amplitude en fonction de (γ, k)
- **Courbes multi-paramètres** pour comparer plusieurs réglages
- **Export PNG/SVG** via le bouton *Download plot* de la barre d’outils Plotly

Astuce : utilisez la molette et la sélection pour zoomer, double-clic pour reset.
"""

layout = html.Div(
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "24px"},
    children=[
        dcc.Markdown(intro_md),

        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}, children=[

            # m (masse)
            html.Div(children=[
                html.Label([
                    "m (masse)",
                    html.Span(" ⓘ", id="tip-m", style={"cursor": "help", "marginLeft": "6px"})
                ]),
                dcc.Slider(id="m", min=0.1, max=5, step=0.1, value=1.0,
                           tooltip={"placement": "bottom"}),
                html.Div(id="m-val"),
                # Tooltip
                dbc.Tooltip(
                    "Inertie du système : plus m est grand, plus x(t) réagit lentement aux variations (effet d'inertie).",
                    target="tip-m", placement="right"
                )
            ]),

            # gamma (amortissement)
            html.Div(children=[
                html.Label([
                    "γ (amortissement)",
                    html.Span(" ⓘ", id="tip-gamma", style={"cursor": "help", "marginLeft": "6px"})
                ]),
                dcc.Slider(id="gamma", min=0.0, max=2.0, step=0.01, value=0.15,
                           tooltip={"placement": "bottom"}),
                html.Div(id="gamma-val"),
                dbc.Tooltip(
                    "Dissipation d'énergie : augmente la perte d'amplitude. "
                    "Sous-amorti si γ² < 4 m k ; critique si γ² = 4 m k ; sur-amorti sinon.",
                    target="tip-gamma", placement="right"
                )
            ]),

            # k (tension ontogénétique)
            html.Div(children=[
                html.Label([
                    "k (tension ontogénétique)",
                    html.Span(" ⓘ", id="tip-k", style={"cursor": "help", "marginLeft": "6px"})
                ]),
                dcc.Slider(id="k", min=0.0, max=5.0, step=0.05, value=1.0,
                           tooltip={"placement": "bottom"}),
                html.Div(id="k-val"),
                dbc.Tooltip(
                    "Force de rappel vers l'équilibre : plus k est grand, plus la 'tension' vers la cohérence est forte (fréquence naturelle ↑).",
                    target="tip-k", placement="right"
                )
            ]),

            # x0
            html.Div(children=[
                html.Label([
                    "x(0)",
                    html.Span(" ⓘ", id="tip-x0", style={"cursor": "help", "marginLeft": "6px"})
                ]),
                dcc.Slider(id="x0", min=-2.0, max=2.0, step=0.05, value=1.0,
                           tooltip={"placement": "bottom"}),
                html.Div(id="x0-val"),
                dbc.Tooltip(
                    "Amplitude initiale : état de départ du système au temps t=0.",
                    target="tip-x0", placement="right"
                )
            ]),

            # v0
            html.Div(children=[
                html.Label([
                    "v(0) = dx/dt(0)",
                    html.Span(" ⓘ", id="tip-v0", style={"cursor": "help", "marginLeft": "6px"})
                ]),
                dcc.Slider(id="v0", min=-2.0, max=2.0, step=0.05, value=0.0,
                           tooltip={"placement": "bottom"}),
                html.Div(id="v0-val"),
                dbc.Tooltip(
                    "Vitesse initiale : si non nulle, peut provoquer un dépassement initial même en régime non oscillant.",
                    target="tip-v0", placement="right"
                )
            ]),

            # t_end
            html.Div(children=[
                html.Label([
                    "Durée (t_end)",
                    html.Span(" ⓘ", id="tip-tend", style={"cursor": "help", "marginLeft": "6px"})
                ]),
                dcc.Slider(id="tend", min=5, max=120, step=1, value=30,
                           tooltip={"placement": "bottom"}),
                html.Div(id="tend-val"),
                dbc.Tooltip(
                    "Fenêtre d'observation/simulation. Plus la durée est longue, plus on voit l'amortissement et la FFT gagne en résolution.",
                    target="tip-tend", placement="right"
                )
            ]),
        ]),

        html.Hr(),

        html.Div(children=[
            html.H3("Série temporelle x(t)"),
            dcc.Loading(dcc.Graph(id="time-series", config={"toImageButtonOptions": {"format": "svg"}}))
        ]),

        html.Div(style={"height": "16px"}),

        html.Div(children=[
            html.H3("Espace des phases (x, dx/dt)"),
            dcc.Loading(dcc.Graph(id="phase-space", config={"toImageButtonOptions": {"format": "svg"}}))
        ]),

        html.Div(style={"height": "16px"}),

        html.Div(children=[
            html.H3("Heatmap du maximum d’amplitude selon (γ, k)"),
            html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"}, children=[
                html.Div([
                    html.Label("γ min / γ max / pas"),
                    dcc.Input(id="g-min", type="number", value=0.0, step=0.05, style={"width": "30%"}),
                    dcc.Input(id="g-max", type="number", value=1.0, step=0.05, style={"width": "30%"}),
                    dcc.Input(id="g-step", type="number", value=0.1, step=0.05, style={"width": "30%"}),
                ]),
                html.Div([
                    html.Label("k min / k max / pas"),
                    dcc.Input(id="k-min", type="number", value=0.0, step=0.1, style={"width": "30%"}),
                    dcc.Input(id="k-max", type="number", value=3.0, step=0.1, style={"width": "30%"}),
                    dcc.Input(id="k-step", type="number", value=0.2, step=0.1, style={"width": "30%"}),
                ]),
            ]),
            html.Div(style={"marginTop": "8px"}, children=[
                html.Button("Calculer la heatmap", id="btn-heat", n_clicks=0)
            ]),
            dcc.Loading(dcc.Graph(id="heatmap", config={"toImageButtonOptions": {"format": "svg"}}))
        ]),

        html.Div(style={"height": "16px"}),

        html.Div(children=[
            html.H3("Comparaison multi-paramètres"),
            html.P("Ajoute des presets et trace-les ensemble (utile pour présenter au public)."),
            html.Div(style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)", "gap": "8px"}, children=[
                dcc.Input(id="preset-m", type="number", placeholder="m", value=1.0, step=0.1),
                dcc.Input(id="preset-g", type="number", placeholder="γ", value=0.15, step=0.01),
                dcc.Input(id="preset-k", type="number", placeholder="k", value=1.0, step=0.05),
                html.Button("Ajouter preset", id="add-preset", n_clicks=0),
            ]),
            dcc.Store(id="presets-store", data=[]),
            html.Div(id="presets-list"),
            dcc.Loading(dcc.Graph(id="multi-series", config={"toImageButtonOptions": {"format": "svg"}}))
        ]),

        html.Hr(),

        html.Div(style={"marginTop": "16px", "display": "flex", "gap": "8px"}, children=[
            html.Button("Exporter toutes les figures (PNG)", id="btn-export-png", n_clicks=0),
            html.Button("Exporter toutes les figures (SVG)", id="btn-export-svg", n_clicks=0),
            html.Button("Télécharger ZIP (PNG+SVG HD)", id="btn-export-zip", n_clicks=0),
            dcc.Store(id="export-done"),
            dcc.Download(id="download-zip"),
        ]),

        html.Hr(),

        dcc.Markdown("""
### Notes pour le public
- **Zoom/Export** : barre d’outils en haut à droite de chaque graphique.
- **Interactivité** : passez la souris pour lire les valeurs, double-clic pour réinitialiser.
- **Reproductibilité** : les paramètres affichés contrôlent les équations différentielles sous-jacentes.
        """)
    ]
)
