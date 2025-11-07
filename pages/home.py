import dash
from dash import dcc, html

dash.register_page(__name__, path="/", name="MRO")

intro_md = """
# Modèle de Résonance Ontogénétique (MRO)

Visualisation interactive du modèle :
- **Série temporelle** x(t)
- **Espace des phases** (x, dx/dt)
- **Heatmap** du maximum d'amplitude selon (γ, k)
- **Comparaison multi-paramètres**
- **Exports** PNG/SVG/ZIP
- **Snapshots** partageables par lien

Astuce : utilisez le zoom, la molette, le pan, double-clic pour réinitialiser.
"""

layout = html.Div(
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "24px"},
    children=[
        # Pour encoder/décoder les paramètres dans l'URL
        dcc.Location(id="mro-url", refresh=False),

        dcc.Markdown(intro_md),

        # --- Sliders principaux ---
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"},
            children=[
                html.Div([
                    html.Label("m (masse) ⓘ"),
                    dcc.Slider(
                        id="m", min=0.1, max=5, step=0.1, value=1.0,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="m-val"),
                ]),
                html.Div([
                    html.Label("γ (amortissement) ⓘ"),
                    dcc.Slider(
                        id="gamma", min=0.0, max=2.0, step=0.01, value=0.15,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="gamma-val"),
                ]),
                html.Div([
                    html.Label("k (tension ontogénétique) ⓘ"),
                    dcc.Slider(
                        id="k", min=0.0, max=5.0, step=0.05, value=1.0,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="k-val"),
                ]),
                html.Div([
                    html.Label("x(0) ⓘ"),
                    dcc.Slider(
                        id="x0", min=-2.0, max=2.0, step=0.05, value=1.0,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="x0-val"),
                ]),
                html.Div([
                    html.Label("v(0) = dx/dt(0) ⓘ"),
                    dcc.Slider(
                        id="v0", min=-2.0, max=2.0, step=0.05, value=0.0,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="v0-val"),
                ]),
                html.Div([
                    html.Label("Durée (t_end) ⓘ"),
                    dcc.Slider(
                        id="tend", min=5, max=120, step=1, value=30,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="tend-val"),
                ]),
            ],
        ),

        html.Hr(),

        # --- x(t) ---
        html.Div([
            html.H3("Série temporelle x(t)"),
            dcc.Loading(
                dcc.Graph(
                    id="time-series",
                    config={"toImageButtonOptions": {"format": "svg"}},
                )
            ),
        ]),

        html.Div(style={"height": "16px"}),

        # --- Phase space ---
        html.Div([
            html.H3("Espace des phases (x, dx/dt)"),
            dcc.Loading(
                dcc.Graph(
                    id="phase-space",
                    config={"toImageButtonOptions": {"format": "svg"}},
                )
            ),
        ]),

        html.Div(style={"height": "16px"}),

        # --- Heatmap ---
        html.Div([
            html.H3("Heatmap du maximum d’amplitude selon (γ, k)"),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "12px",
                },
                children=[
                    html.Div([
                        html.Label("γ min / γ max / pas"),
                        dcc.Input(
                            id="g-min", type="number",
                            value=0.0, step=0.05,
                            style={"width": "30%"},
                        ),
                        dcc.Input(
                            id="g-max", type="number",
                            value=1.0, step=0.05,
                            style={"width": "30%"},
                        ),
                        dcc.Input(
                            id="g-step", type="number",
                            value=0.1, step=0.05,
                            style={"width": "30%"},
                        ),
                    ]),
                    html.Div([
                        html.Label("k min / k max / pas"),
                        dcc.Input(
                            id="k-min", type="number",
                            value=0.0, step=0.1,
                            style={"width": "30%"},
                        ),
                        dcc.Input(
                            id="k-max", type="number",
                            value=3.0, step=0.1,
                            style={"width": "30%"},
                        ),
                        dcc.Input(
                            id="k-step", type="number",
                            value=0.2, step=0.1,
                            style={"width": "30%"},
                        ),
                    ]),
                ],
            ),
            html.Div(
                style={"marginTop": "8px"},
                children=[
                    html.Button(
                        "Calculer la heatmap",
                        id="btn-heat", n_clicks=0,
                    )
                ],
            ),
            dcc.Loading(
                dcc.Graph(
                    id="heatmap",
                    config={"toImageButtonOptions": {"format": "svg"}},
                )
            ),
        ]),

        html.Div(style={"height": "16px"}),

        # --- Multi-séries (optionnel si callbacks côté app.py) ---
        html.Div([
            html.H3("Comparaison multi-paramètres"),
            html.P("Ajoutez des presets et comparez les réponses temporelles."),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(4,1fr)",
                    "gap": "8px",
                },
                children=[
                    dcc.Input(id="preset-m", type="number", placeholder="m", value=1.0, step=0.1),
                    dcc.Input(id="preset-g", type="number", placeholder="γ", value=0.15, step=0.01),
                    dcc.Input(id="preset-k", type="number", placeholder="k", value=1.0, step=0.05),
                    html.Button("Ajouter preset", id="add-preset", n_clicks=0),
                ],
            ),
            dcc.Store(id="presets-store", data=[]),
            html.Div(id="presets-list"),
            dcc.Loading(
                dcc.Graph(
                    id="multi-series",
                    config={"toImageButtonOptions": {"format": "svg"}},
                )
            ),
        ]),

        html.Hr(),

        # --- Exports + snapshot ---
        html.Div(
            style={
                "marginTop": "8px",
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "8px",
                "alignItems": "center",
            },
            children=[
                html.Button(
                    "Exporter toutes les figures (PNG)",
                    id="btn-export-png",
                    n_clicks=0,
                ),
                html.Button(
                    "Exporter toutes les figures (SVG)",
                    id="btn-export-svg",
                    n_clicks=0,
                ),
                html.Button(
                    "Télécharger ZIP (PNG+SVG HD)",
                    id="btn-export-zip",
                    n_clicks=0,
                ),
                dcc.Store(id="export-done"),
                dcc.Download(id="download-zip"),
            ],
        ),

        html.Div(style={"height": "8px"}),

        # --- Snapshot partageable ---
        html.Div(
            style={
                "marginTop": "8px",
                "padding": "10px",
                "border": "1px solid #eee",
                "borderRadius": "8px",
                "background": "#fafafa",
            },
            children=[
                html.Div("Lien de snapshot (partage de cette configuration) :",
                         style={"fontSize": "0.9rem", "marginBottom": "4px"}),
                html.Button(
                    "📎 Générer un lien",
                    id="share-link-btn",
                    n_clicks=0,
                    style={"marginRight": "8px"},
                ),
                dcc.Input(
                    id="share-link-output",
                    type="text",
                    readOnly=True,
                    style={
                        "width": "100%",
                        "fontSize": "0.8rem",
                        "padding": "6px",
                        "fontFamily": "monospace",
                    },
                ),
            ],
        ),

        html.Hr(),

        dcc.Markdown(
            """
### Notes
- Utiliser ce tableau de bord comme laboratoire : explorer, annoter, exporter.
- Les snapshots permettent de partager des régimes précis du MRO.
            """
        ),
    ],
)