import dash
from dash import dcc, html

dash.register_page(
    __name__,
    path="/jules",
    name="Auteur",
    order=82,
)

ORCID_URL = "https://orcid.org/0009-0007-1822-5741"
GITHUB_URL = "https://github.com/henissartj"
LINKEDIN_URL = "https://www.linkedin.com/in/henissartmiqueljules/"
SCHOLAR_URL = "https://scholar.google.com/citations?user=_20OPpsAAAAJ&hl=fr"

WORKS = [
    {
        "title": "Hypothèse de la Dissipation Constructive",
        "year": "2025",
        "type": "Preprint",
        "doi": "10.22541/au.176236369.96024564/v1",
    },
    {
        "title": "Modèle de Résonance Ontogénétique (MRO) : théorisation d'une fréquence du commencement dans les systèmes vivants et symboliques",
        "year": "2025",
        "type": "Preprint",
        "doi": "10.22541/au.176175046.68446609/v1",
    },
    {
        "title": "Neuro-esthétique de l’engagement total",
        "year": "2025",
        "type": "Preprint",
        "doi": "10.22541/au.176159681.10112647/v1",
    },
    {
        "title": "Théorie de l'Éphévérisme",
        "year": "2025",
        "type": "Preprint",
        "doi": "10.22541/au.176124949.95416749/v2",
    },
]

def external_link(label, href):
    return html.A(
        label,
        href=href,
        target="_blank",
        rel="noopener noreferrer",
        style={
            "display": "inline-block",
            "marginRight": "10px",
            "marginBottom": "6px",
            "padding": "6px 10px",
            "borderRadius": "8px",
            "border": "1px solid #ddd",
            "fontSize": "0.9rem",
            "textDecoration": "none",
            "color": "#0d6efd",
        },
    )

layout = html.Div(
    style={"maxWidth": "900px", "margin": "0 auto", "padding": "32px"},
    children=[
        html.H1("Jules Henissart-Miquel", style={"marginBottom": "4px"}),
        html.P(
            "Recherche indépendante — Modèle de Résonance Ontogénétique (MRO), "
            "dissipation constructive, esthétiques de la mémoire dynamique et théorie de l'Éphévérisme.",
            style={"fontSize": "1.05rem", "lineHeight": "1.6", "marginBottom": "16px"},
        ),

        html.H3("Contacts"),
        html.Ul([
            html.Li("Email : henissartj@gmail.com"),
            html.Li("Email : contact@epheverisme.art"),
        ]),

        html.H3("Identifiants & Profils", style={"marginTop": "20px"}),
        html.Div(
            children=[
                external_link("ORCID", ORCID_URL),
                external_link("GitHub", GITHUB_URL),
                external_link("LinkedIn", LINKEDIN_URL),
                external_link("Google Scholar", SCHOLAR_URL),
            ],
            style={"marginBottom": "20px"},
        ),

        html.H3("Travaux sélectionnés", style={"marginTop": "10px"}),
        html.Ul(
            [
                html.Li(
                    [
                        html.Span(f"{w['title']} — {w['type']} ({w['year']}) — "),
                        html.A(
                            f"DOI: {w['doi']}",
                            href=f"https://doi.org/{w['doi']}",
                            target="_blank",
                            rel="noopener noreferrer",
                            style={"color": "#0d6efd", "textDecoration": "none"},
                        ),
                    ]
                )
                for w in WORKS
            ],
            style={"lineHeight": "1.8"},
        ),
    ],
)