import dash
from dash import dcc, html

# Page accessible via /experiences
dash.register_page(
    __name__,
    path="/experiences",
    name="Tests & Expériences",
    order=90,
)

EXTERNAL_URL = "https://sites.google.com/view/recherches-sur-le-mro/accueil"

layout = html.Div(
    style={"maxWidth": "900px", "margin": "0 auto", "padding": "24px"},
    children=[
        # Redirection immédiate (HTML meta refresh)
        html.Meta(httpEquiv="refresh", content=f"0; url={EXTERNAL_URL}"),

        html.H1("Tests & Expériences"),
        html.P(
            "Redirection automatique vers l’espace dédié aux tests et expériences du MRO."
        ),
        html.P(
            "Si la redirection ne démarre pas automatiquement, utilisez le bouton ci-dessous."
        ),
        html.A(
            "Accéder aux tests & expériences",
            href=EXTERNAL_URL,
            target="_blank",
            rel="noopener",
            style={
                "display": "inline-block",
                "padding": "10px 14px",
                "borderRadius": "8px",
                "border": "1px solid #ddd",
                "textDecoration": "none",
            },
        ),
        # Filet de sécurité : dcc.Location pour forcer le navigateur à changer d’URL si le meta est bloqué
        dcc.Location(href=EXTERNAL_URL, id="redirect-experiences"),
    ]
)
