import dash
from dash import dcc, html, Input, Output, State

# Page de recherche simple pour activer SearchAction schema
dash.register_page(
    __name__,
    path="/search",
    name="Recherche",
    order=70,
)

def page_index(p):
    # Map affichage convivial
    m = {
        "/": "Simulations MRO",
        "/fft": "FFT",
        "/docs": "Explications",
        "/heatmap3d": "Heatmap 3D",
        "/experiences": "Tests & Expériences",
        "/epheverisme": "Éphévérisme",
        "/jules": "Auteur",
        "/repository": "Code source (GitHub)",
        "/credits": "Crédits",
    }
    return m.get(p, p)

PAGES = sorted({page["path"] for page in dash.page_registry.values()})

layout = html.Div(
    style={"maxWidth": "900px", "margin": "0 auto", "padding": "24px"},
    children=[
        html.H1("Recherche dans le laboratoire"),
        html.P("Tapez un mot-clé pour filtrer les pages du site."),
        dcc.Input(id="search-q", type="text", placeholder="ex: FFT, explications, auteur…", style={"width":"100%","padding":"10px"}),
        html.Div(id="search-results", style={"marginTop":"16px"}),
    ],
)

@dash.callback(Output("search-results", "children"), Input("search-q", "value"))
def filter_pages(q):
    items = []
    q = (q or "").strip().lower()
    for p in PAGES:
        label = page_index(p)
        hay = (label + " " + p).lower()
        if not q or q in hay:
            items.append(html.Div(
                [dcc.Link(label, href=p, style={"textDecoration":"none","color":"#0d6efd"})],
                style={"padding":"8px 0","borderBottom":"1px solid #eee"}
            ))
    if not items:
        return html.Div("Aucun résultat.", style={"color":"#6b7280"})
    return items

