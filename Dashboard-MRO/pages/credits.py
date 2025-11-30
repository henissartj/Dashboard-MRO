import dash
from dash import dcc, html

dash.register_page(
    __name__,
    path="/credits",
    name="Crédits",
    order=99,  # apparait en dernier dans la nav
)

# --- Métadonnées ---
AUTHOR_NAME = "Jules Henissart-Miquel"
ORCID_URL   = "https://orcid.org/0009-0007-1822-5741"
DOI_URL     = "https://doi.org/10.22541/au.176175046.68446609/v1"
TECHRXIV_URL= "https://www.techrxiv.org/users/983368/articles/1353037/mod%C3%A8le-de-r%C3%A9sonance-ontog%C3%A9n%C3%A9tique-mro-th%C3%A9orisation-d-une-fr%C3%A9quence-du-commencement-dans-les-syst%C3%A8mes-vivants-et-symboliques"
GITHUB_URL  = "https://github.com/henissartj/Dashboard-MRO"

# BibTeX minimal (tu peux l’ajuster quand tu auras la référence finale de ton dépôt/article)
BIBTEX = r"""@article{HenissartMiquel_MRO_2025,
  author  = {Jules Henissart-Miquel},
  title   = {Modèle de Résonance Ontogénétique (MRO)},
  year    = {2025},
  doi     = {10.22541/au.176175046.68446609/v1},
  url     = {https://doi.org/10.22541/au.176175046.68446609/v1},
  howpublished = {\url{https://epheverisme.art}}
}
"""

def small_badge(label, href, title=None):
    return html.A(
        label,
        href=href,
        target="_blank",
        rel="noopener",
        title=title or label,
        style={
            "display": "inline-block",
            "padding": "4px 8px",
            "fontSize": "0.9rem",
            "border": "1px solid #d0d7de",
            "borderRadius": "6px",
            "textDecoration": "none",
            "marginRight": "8px",
            "color": "#0969da",
            "background": "#f6f8fa",
        },
    )

def mono_box(children):
    return html.Div(
        children,
        style={
            "border": "1px solid #e5e7eb",
            "borderRadius": "8px",
            "background": "#fafafa",
            "padding": "12px 14px",
            "fontFamily": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
            "whiteSpace": "pre-wrap",
            "overflowX": "auto",
        },
    )

layout = html.Div(
    style={"maxWidth": "880px", "margin": "0 auto", "padding": "28px 24px"},
    children=[
        # Titre + auteur
        html.H1("Crédits & À propos", style={"marginBottom": "6px"}),
        html.Div(
            [
                html.Span(AUTHOR_NAME, style={"fontWeight": 600}),
                html.Span(" • "),
                small_badge("ORCID", ORCID_URL, title="Profil ORCID"),
            ],
            style={"marginBottom": "10px"},
        ),

        # Badges liens rapides
        html.Div(
            [
                small_badge("Article (DOI)", DOI_URL, title="Lien DOI"),
                small_badge("Preprint TechRxiv", TECHRXIV_URL),
                small_badge("Dépôt GitHub (open source)", GITHUB_URL),
                dcc.Link(
                    "Accueil",
                    href="/",
                    style={
                        "display": "inline-block",
                        "padding": "4px 8px",
                        "fontSize": "0.9rem",
                        "border": "1px solid #d0d7de",
                        "borderRadius": "6px",
                        "textDecoration": "none",
                        "marginRight": "8px",
                        "color": "#0969da",
                        "background": "#f6f8fa",
                    },
                ),
                dcc.Link(
                    "FFT",
                    href="/fft",
                    style={
                        "display": "inline-block",
                        "padding": "4px 8px",
                        "fontSize": "0.9rem",
                        "border": "1px solid #d0d7de",
                        "borderRadius": "6px",
                        "textDecoration": "none",
                        "marginRight": "8px",
                        "color": "#0969da",
                        "background": "#f6f8fa",
                    },
                ),
                dcc.Link(
                    "Explications",
                    href="/docs",
                    style={
                        "display": "inline-block",
                        "padding": "4px 8px",
                        "fontSize": "0.9rem",
                        "border": "1px solid #d0d7de",
                        "borderRadius": "6px",
                        "textDecoration": "none",
                        "marginRight": "8px",
                        "color": "#0969da",
                        "background": "#f6f8fa",
                    },
                ),
            ],
            style={"marginBottom": "22px"},
        ),

        html.Hr(),

        # Résumé scientifique court
        html.H2("Résumé"),
        dcc.Markdown(
            """
Ce site présente des visualisations interactives du **Modèle de Résonance Ontogénétique (MRO)**, incluant :
- évolution temporelle \(x(t)\),
- trajectoires en espace des phases \((x, \\dot{x})\),
- cartographie d'amplitude maximale en fonction de \(\gamma\) et \(k\),
- analyse fréquentielle (FFT).

L’objectif est de **rendre reproductibles** et **explorables** les dynamiques décrites dans l’article associé.
            """,
            mathjax=True,
        ),

        html.Hr(),

        # Référence + DOI
        html.H2("Référence & DOI"),
        html.P(
            [
                "Veuillez citer : ",
                html.A(
                    "Henissart-Miquel (MRO), DOI",
                    href=DOI_URL,
                    target="_blank",
                    rel="noopener",
                    style={"textDecoration": "none", "color": "#0969da"},
                ),
                ".",
            ]
        ),
        mono_box(
            "Henissart-Miquel, J. (2025). Modèle de Résonance Ontogénétique (MRO). "
            "https://doi.org/10.22541/au.176175046.68446609/v1"
        ),

        html.Div(style={"height": "10px"}),

        html.P("BibTeX :"),
        html.Div(
            dcc.Textarea(
                value=BIBTEX.strip(),
                readOnly=True,
                style={
                    "width": "100%",
                    "height": "180px",
                    "fontFamily": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
                    "fontSize": "0.9rem",
                    "background": "#fafafa",
                    "border": "1px solid #e5e7eb",
                    "borderRadius": "8px",
                    "padding": "10px 12px",
                },
            )
        ),

        html.Hr(),

        # Ouverture / licence
        html.H2("Ouverture & Licence"),
        dcc.Markdown(
            f"""
Le code est **open source** : consultez le dépôt GitHub [{GITHUB_URL}]({GITHUB_URL}).
Les issues et pull requests sont bienvenues.

> **Licence** : voir `LICENSE` dans le dépôt GitHub.
            """,
            link_target="_blank",
        ),

        html.Hr(),

        # Mentions
        html.H2("Mentions"),
        dcc.Markdown(
            """
- Visualisations générées avec **Dash/Plotly**, calculs numériques **NumPy/SciPy**.
- Exports (PNG/SVG/ZIP) pour faciliter le partage et la reproductibilité.
- Les paramètres de simulation affichés contrôlent directement les équations différentielles du MRO.
            """
        ),
    ],
)
