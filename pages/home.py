import dash
from dash import dcc, html

dash.register_page(
    __name__,
    path="/",
    title="MRO • Laboratoire Éphévérisme",
    name="Accueil"
)

intro_md = """
# Modèle de Résonance Ontogénétique (MRO)

Cette interface permet d’explorer le MRO à travers :
- **La série temporelle** de x(t)
- **L’espace des phases** (x, dx/dt)
- **Une heatmap** du maximum d'amplitude selon (γ, k)
- **Des comparaisons multi-paramètres**
- **Des exports PNG/SVG/ZIP** pour documenter vos analyses.
"""

layout = html.Div(
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "24px"},
    children=[
        # Pour snapshots via l'URL (utilisé par app.py)
        dcc.Location(id="mro-url", refresh=False),

        # --- Intro ---
        dcc.Markdown(intro_md),

        # Hint
        html.Div(
            "Survolez les icônes ⓘ pour une explication des paramètres.",
            style={
                "fontSize": "0.85rem",
                "color": "#6b7280",
                "marginTop": "4px",
                "marginBottom": "16px",
            },
        ),

        # --- Équation synchronisée ---
        html.Div(
            [
                html.Div("Équation instantanée", style={"fontWeight": 600}),
                html.Div(
                    id="equation-display",
                    style={
                        "marginTop": "4px",
                        "padding": "8px 10px",
                        "borderRadius": "6px",
                        "backgroundColor": "#f9fafb",
                        "border": "1px solid #e5e7eb",
                        "fontFamily": "monospace",
                        "fontSize": "0.9rem",
                        "color": "#111827",
                    },
                ),
            ],
            style={"marginBottom": "18px"},
        ),

        # --- Sliders principaux ---
        html.Div(
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "16px",
            },
            children=[
                html.Div([
                    html.Label([
                        "m (masse) ",
                        html.Span(
                            "ⓘ",
                            title="Masse effective : plus m est grand, plus le système réagit lentement.",
                            style={"cursor": "help", "color": "#9ca3af", "fontSize": "0.8rem"},
                        ),
                    ]),
                    dcc.Slider(
                        id="m",
                        min=0.1, max=5, step=0.1, value=1.0,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="m-val"),
                ]),

                html.Div([
                    html.Label([
                        "γ (amortissement) ",
                        html.Span(
                            "ⓘ",
                            title="Contrôle la dissipation : plus γ est grand, plus les oscillations se calment vite.",
                            style={"cursor": "help", "color": "#9ca3af", "fontSize": "0.8rem"},
                        ),
                    ]),
                    dcc.Slider(
                        id="gamma",
                        min=0.0, max=2.0, step=0.01, value=0.15,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="gamma-val"),
                ]),

                html.Div([
                    html.Label([
                        "k (tension ontogénétique) ",
                        html.Span(
                            "ⓘ",
                            title="Rigidité / contrainte : structure la fréquence naturelle du système.",
                            style={"cursor": "help", "color": "#9ca3af", "fontSize": "0.8rem"},
                        ),
                    ]),
                    dcc.Slider(
                        id="k",
                        min=0.0, max=5.0, step=0.05, value=1.0,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="k-val"),
                ]),

                html.Div([
                    html.Label([
                        "x(0) ",
                        html.Span(
                            "ⓘ",
                            title="Condition initiale de position : état de départ du système.",
                            style={"cursor": "help", "color": "#9ca3af", "fontSize": "0.8rem"},
                        ),
                    ]),
                    dcc.Slider(
                        id="x0",
                        min=-2.0, max=2.0, step=0.05, value=1.0,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="x0-val"),
                ]),

                html.Div([
                    html.Label([
                        "v(0) = dx/dt(0) ",
                        html.Span(
                            "ⓘ",
                            title="Vitesse initiale : impulsion de départ du système.",
                            style={"cursor": "help", "color": "#9ca3af", "fontSize": "0.8rem"},
                        ),
                    ]),
                    dcc.Slider(
                        id="v0",
                        min=-2.0, max=2.0, step=0.05, value=0.0,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="v0-val"),
                ]),

                html.Div([
                    html.Label([
                        "Durée (t_end) ",
                        html.Span(
                            "ⓘ",
                            title="Fenêtre temporelle simulée : plus elle est longue, plus on observe la dynamique globale.",
                            style={"cursor": "help", "color": "#9ca3af", "fontSize": "0.8rem"},
                        ),
                    ]),
                    dcc.Slider(
                        id="tend",
                        min=5, max=120, step=1, value=30,
                        tooltip={"placement": "bottom"},
                    ),
                    html.Div(id="tend-val"),
                ]),
            ],
        ),

        html.Hr(),

        # --- x(t) + annotations & dessin ---
        html.Div([
            html.H3("Série temporelle x(t)"),
            html.Div(
                "Saisissez un texte, cliquez sur la courbe pour annoter, ou utilisez les outils de dessin (ligne, forme, crayon) dans la barre Plotly.",
                style={"fontSize": "0.8rem", "color": "#6b7280", "marginBottom": "6px"},
            ),

            # Champ texte annotation
            html.Div(
                style={
                    "display": "flex",
                    "gap": "8px",
                    "alignItems": "center",
                    "marginBottom": "8px",
                    "flexWrap": "wrap",
                },
                children=[
                    dcc.Input(
                        id="annot-label",
                        type="text",
                        placeholder="Texte de l’annotation",
                        style={
                            "width": "240px",
                            "padding": "4px 6px",
                            "fontSize": "0.85rem",
                        },
                    ),
                    html.Div(
                        "Puis cliquez sur un point de la courbe x(t).",
                        style={"fontSize": "0.8rem", "color": "#6b7280"},
                    ),
                ],
            ),

            # Stores pour annotations et dessins
            dcc.Store(id="ts-annotations", data=[]),
            dcc.Store(id="ts-shapes", data=[]),

            # Liste des annotations textuelles
            html.Ul(id="annot-list", style={"fontSize": "0.8rem", "color": "#374151"}),

            # Graph avec outils de dessin activés
            dcc.Loading(
                dcc.Graph(
                    id="time-series",
                    config={
                        "toImageButtonOptions": {"format": "svg"},
                        "modeBarButtonsToAdd": [
                            "drawline",
                            "drawopenpath",
                            "drawrect",
                            "drawcircle",
                            "eraseshape",
                        ],
                        "displaylogo": False,
                    },
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

        # --- Multi-séries ---
        html.Div([
            html.H3("Comparaison multi-paramètres"),
            html.P("Ajoutez des presets et comparez les réponses temporelles."),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(4,1fr)",
                    "gap": "8px",
                    "marginBottom": "8px",
                },
                children=[
                    dcc.Input(id="preset-m", type="number", placeholder="m", value=1.0, step=0.1),
                    dcc.Input(id="preset-g", type="number", placeholder="γ", value=0.15, step=0.01),
                    dcc.Input(id="preset-k", type="number", placeholder="k", value=1.0, step=0.05),
                    html.Button(
                        "Ajouter preset",
                        id="add-preset",
                        n_clicks=0,
                        style={
                            "padding": "6px 10px",
                            "borderRadius": "4px",
                            "border": "1px solid #ccc",
                            "backgroundColor": "#ffffff",
                            "cursor": "pointer",
                        },
                    ),
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
                    style={
                        "padding": "6px 10px",
                        "borderRadius": "4px",
                        "border": "1px solid #ccc",
                        "backgroundColor": "#ffffff",
                        "cursor": "pointer",
                    },
                ),
                html.Button(
                    "Exporter toutes les figures (SVG)",
                    id="btn-export-svg",
                    n_clicks=0,
                    style={
                        "padding": "6px 10px",
                        "borderRadius": "4px",
                        "border": "1px solid #ccc",
                        "backgroundColor": "#ffffff",
                        "cursor": "pointer",
                    },
                ),
                html.Button(
                    "Télécharger ZIP (PNG+SVG HD)",
                    id="btn-export-zip",
                    n_clicks=0,
                    style={
                        "padding": "6px 10px",
                        "borderRadius": "4px",
                        "border": "1px solid #ccc",
                        "backgroundColor": "#ffffff",
                        "cursor": "pointer",
                    },
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
                html.Div(
                    "Lien de snapshot (partage de cette configuration) :",
                    style={"fontSize": "0.9rem", "marginBottom": "4px"},
                ),
                html.Button(
                    "📎 Générer un lien",
                    id="share-link-btn",
                    n_clicks=0,
                    style={
                        "padding": "4px 10px",
                        "borderRadius": "4px",
                        "border": "1px solid #ccc",
                        "backgroundColor": "#ffffff",
                        "cursor": "pointer",
                        "marginBottom": "6px",
                    },
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
- Utilisez ce laboratoire comme outil d’exploration scientifique.
- Les exports et snapshots facilitent la documentation et le partage de vos résultats.
            """
        ),
    ],
)