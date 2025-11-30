import dash
from dash import dcc, html

dash.register_page(
    __name__,
    path="/repository",
    name="Code source (GitHub)",
    order=80,
)

GITHUB_URL = "https://github.com/henissartj/Dashboard-MRO"

layout = html.Div(
    style={"maxWidth": "800px", "margin": "0 auto", "padding": "32px"},
    children=[
        html.H1("Code source du Dashboard MRO", style={"marginBottom": "16px"}),
        html.P(
            """
Ce tableau de bord est intégralement disponible en accès public sur GitHub.
Le dépôt rassemble le code du simulateur MRO, les visualisations, la structure
multi-pages, ainsi que la documentation technique et scientifique associée.
            """,
            style={"fontSize": "1.05rem", "lineHeight": "1.6"},
        ),
        html.P(
            "Vous pouvez consulter, auditer ou cloner le code à des fins de recherche, "
            "tout en respectant la licence en vigueur.",
            style={"fontSize": "1.05rem", "lineHeight": "1.6"},
        ),
        html.Div(
            style={"marginTop": "24px"},
            children=html.A(
                "Ouvrir le dépôt GitHub Dashboard-MRO",
                href=GITHUB_URL,
                target="_blank",
                rel="noopener noreferrer",
                style={
                    "display": "inline-block",
                    "padding": "10px 18px",
                    "borderRadius": "8px",
                    "border": "1px solid #0d6efd",
                    "color": "#0d6efd",
                    "textDecoration": "none",
                    "fontWeight": "600",
                },
            ),
        ),
    ],
)