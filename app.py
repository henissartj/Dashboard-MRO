import os
import io
import zipfile
import datetime as dt
import json
from urllib.parse import urlencode, parse_qs
from flask import request, Response

import numpy as np
from scipy.integrate import solve_ivp

import dash
from dash import dcc, html, Input, Output, State, callback
from dash.exceptions import PreventUpdate

import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio


# ===========================
#   Modèle MRO
# ===========================

def MRO_equations(t, Y, m, gamma, k):
    x, dxdt = Y
    dxdtt = -(gamma / m) * dxdt - (k / m) * x
    return [dxdt, dxdtt]


def simulate_mro(
    m=1.0,
    gamma=0.15,
    k=1.0,
    x0=1.0,
    v0=0.0,
    t_start=0.0,
    t_end=30.0,
    t_points=3000,
):
    t_eval = np.linspace(t_start, t_end, t_points)
    sol = solve_ivp(
        MRO_equations,
        [t_start, t_end],
        [x0, v0],
        args=(m, gamma, k),
        t_eval=t_eval,
        method="RK45",
    )
    t = sol.t
    x = sol.y[0]
    v = sol.y[1]
    return t, x, v


def heatmap_max_amp(
    gammas,
    ks,
    m=1.0,
    x0=1.0,
    v0=0.0,
    t_end=30.0,
    t_points=2000,
):
    data = np.zeros((len(gammas), len(ks)))
    for i, g in enumerate(gammas):
        for j, kk in enumerate(ks):
            t, x, _ = simulate_mro(
                m=m,
                gamma=g,
                k=kk,
                x0=x0,
                v0=v0,
                t_start=0,
                t_end=t_end,
                t_points=t_points,
            )
            data[i, j] = np.max(np.abs(x))
    return data


# ===========================
#   App Dash
# ===========================

app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title="Laboratoire Éphévériste • Modèle de Résonance Ontogénétique",
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    ],
    assets_folder=os.path.join(os.path.dirname(__file__), "assets"),
    assets_url_path="assets",
    serve_locally=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": (
                "Visualisations interactives du Modèle de Résonance Ontogénétique (MRO) : "
                "x(t), espace des phases, heatmaps (γ,k), FFT, exports PNG/SVG/ZIP."
            ),
        },
        # Open Graph
        {
            "property": "og:title",
            "content": "Modèle de Résonance Ontogénétique (MRO) — Visualisations interactives",
        },
        {
            "property": "og:description",
            "content": "Explorez x(t), l’espace des phases, les heatmaps (γ,k) et la FFT. Exports PNG/SVG/ZIP. Projet open source.",
        },
        {"property": "og:type", "content": "website"},
        {"property": "og:url", "content": "https://epheverisme.art/"},
        {"property": "og:image", "content": "https://epheverisme.art/assets/og-image.png"},
        # Twitter
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:title", "content": "MRO — Visualisations interactives"},
        {
            "name": "twitter:description",
            "content": "x(t), espace des phases, heatmaps (γ,k), FFT, exports — open source",
        },
        {"name": "twitter:image", "content": "https://epheverisme.art/assets/og-image.png"},
    ],
)

server = app.server

# ===========================
#   Static SEO files at root
# ===========================

@server.route("/robots.txt")
def _robots_txt():
    # Serve the robots file from assets
    p = os.path.join(os.path.dirname(__file__), "assets", "robots.txt")
    if not os.path.exists(p):
        return "User-agent: *\nDisallow:", 200, {"Content-Type": "text/plain"}
    with open(p, "rb") as f:
        content = f.read()
    return content, 200, {"Content-Type": "text/plain"}


@server.route("/sitemap.xml")
def _sitemap_xml():
    try:
        base = request.url_root.rstrip("/")
        # Collect all registered Dash pages
        paths = sorted({
            page["path"]
            for page in dash.page_registry.values()
            if page.get("path") not in {"/casino"}
        })
        # Ensure root is present
        if "/" not in paths:
            paths = ["/"] + paths
        today = dt.date.today().isoformat()
        urls = [
            f"  <url>\n    <loc>{base}{path}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>{ '1.0' if path == '/' else '0.6' }</priority>\n  </url>"
            for path in paths
        ]
        xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
            + "\n".join(urls)
            + "\n</urlset>\n"
        )
        return Response(xml, mimetype="application/xml")
    except Exception:
        # Fallback to static file if available
        p = os.path.join(os.path.dirname(__file__), "assets", "sitemap.xml")
        if os.path.exists(p):
            with open(p, "rb") as f:
                content = f.read()
            return content, 200, {"Content-Type": "application/xml"}
        return "", 404, {"Content-Type": "application/xml"}


@server.route("/favicon.ico")
def _favicon():
    p = os.path.join(os.path.dirname(__file__), "assets", "favicon.ico")
    if not os.path.exists(p):
        return "", 404, {"Content-Type": "image/x-icon"}
    with open(p, "rb") as f:
        content = f.read()
    return content, 200, {"Content-Type": "image/x-icon"}

# Static assets (explicit, fallback)
from flask import send_from_directory

@server.route('/assets/<path:filename>')
def _assets(filename):
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    try:
        return send_from_directory(assets_dir, filename)
    except Exception:
        return "", 404

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8050)
    args = parser.parse_args()

    app.run(debug=True, host="0.0.0.0", port=args.port)


# ===========================
#   index_string (SEO)
# ===========================

app.index_string = """
<!DOCTYPE html>
<html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard MRO — Modèle de Résonance Ontogénétique</title>

        <!-- SEO -->
        <meta name="description" content="Modèle de Résonance Ontogénétique (MRO) — simulateur scientifique et visuel interactif explorant la dissipation constructive et la mémoire dynamique.">
        <meta name="author" content="Jules Henissart-Miquel">
        <meta name="keywords" content="MRO, résonance ontogénétique, dissipation constructive, système dynamique, attracteur, plasticité, ontogenèse, éphévérisme, neuro-esthétique">
        <meta name="robots" content="index, follow">

        <!-- Canonical (set by script below) -->
        <link id="canonical-link" rel="canonical" href="https://epheverisme.art/">

        <!-- Open Graph -->
        <meta property="og:title" content="Dashboard MRO — Modèle de Résonance Ontogénétique">
        <meta property="og:type" content="website">
        <meta property="og:url" content="https://epheverisme.art">
        <meta property="og:image" content="https://epheverisme.art/assets/logo.png">
        <meta property="og:description" content="Exploration interactive des équations du MRO et de la dissipation constructive.">

        <!-- Twitter -->
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:title" content="Dashboard MRO">
        <meta name="twitter:description" content="Exploration scientifique et esthétique du Modèle de Résonance Ontogénétique.">

        <!-- JSON-LD -->
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Dataset",
          "name": "Modèle de Résonance Ontogénétique (MRO)",
          "description": "Simulateur scientifique du MRO développé par Jules Henissart-Miquel, explorant la dissipation constructive et la plasticité ontogénétique.",
          "author": {
            "@type": "Person",
            "name": "Jules Henissart-Miquel",
            "url": "https://epheverisme.art/jules",
            "identifier": "https://orcid.org/0009-0007-1822-5741"
          },
          "license": "https://opensource.org/licenses/MIT",
          "url": "https://epheverisme.art",
          "citation": "10.22541/au.176175046.68446609/v1"
        }
        </script>

        <!-- JSON-LD Organization -->
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Laboratoire Éphévériste",
          "url": "https://epheverisme.art",
          "logo": {
            "@type": "ImageObject",
            "url": "https://epheverisme.art/assets/logo.png"
          },
          "sameAs": [
            "https://orcid.org/0009-0007-1822-5741",
            "https://github.com/henissartj/Dashboard-MRO",
            "https://github.com/henissartj",
            "https://www.linkedin.com/in/henissartmiqueljules/",
            "https://scholar.google.com/citations?user=_20OPpsAAAAJ&hl=fr"
          ]
        }
        </script>

        <!-- JSON-LD WebSite + SearchAction -->
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "WebSite",
          "url": "https://epheverisme.art",
          "name": "Laboratoire Éphévériste — MRO",
          "potentialAction": {
            "@type": "SearchAction",
            "target": "https://epheverisme.art/search?q={search_term_string}",
            "query-input": "required name=search_term_string"
          }
        }
        </script>

        {%metas%}
        {%favicon%}
        {%css%}

        <!-- Canonical et Breadcrumbs sont désormais gérés côté serveur via Dash -->

        <!-- Suppression de l’injection client WebPage/BreadcrumbList (géré côté serveur) -->
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
    </html>
"""

# ===========================
#   Plotly theme (scientific, lab-like)
# ===========================

pio.templates["mro_lab"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="system-ui, -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif", size=14, color="#111827"),
        paper_bgcolor="#f7f7f8",
        plot_bgcolor="#ffffff",
        xaxis=dict(gridcolor="#e5e7eb", zerolinecolor="#e5e7eb", linecolor="#9ca3af", ticks="outside"),
        yaxis=dict(gridcolor="#e5e7eb", zerolinecolor="#e5e7eb", linecolor="#9ca3af", ticks="outside"),
        colorway=[
            "#0d6efd",  # primary
            "#16a085",
            "#8e44ad",
            "#e67e22",
            "#2c3e50",
            "#d35400",
        ],
        legend=dict(bgcolor="#ffffff", bordercolor="#e5e7eb", borderwidth=1),
        margin=dict(l=60, r=30, t=50, b=60),
    )
)
pio.templates.default = "mro_lab"


# ===========================
#   Global layout with navbar/footer
# ===========================

def _navbar():
    # Build navigation links from registered pages
    pages = list(dash.page_registry.values())
    # Sort by explicit order if available, else by name
    def _order(p):
        v = p.get("order", None)
        try:
            return int(v) if v is not None else 50
        except (TypeError, ValueError):
            return 50
    # Stable sort by order, then by name/path for consistency
    pages = sorted(pages, key=lambda p: ( _order(p), (p.get("name") or p.get("path") or "") ))

    links = [
        dcc.Link(
            p.get("name", p["path"]).strip() or p["path"],
            href=p["path"],
            className="nav-link",
        )
        for p in pages
    ]

    brand = dcc.Link(
        "Laboratoire MRO",
        href="/",
        className="nav-brand",
    )

    return html.Nav(
        [
            html.Div([brand], className="nav-left"),
            html.Div(links, className="nav-right"),
        ],
        className="navbar",
    )


def _footer():
    return html.Footer(
        [
            html.Div("© Laboratoire Éphévérisme — MRO", className="footer-text"),
        ],
        className="site-footer",
    )


app.layout = html.Div(
    [
        dcc.Location(id="router"),
        _navbar(),
        html.Main(dash.page_container, className="page-container"),
        _footer(),
    ],
    className="site-wrapper",
)


# ===========================
#   Dev server (local run)
# ===========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8050"))
    app.run(host="0.0.0.0", port=port, debug=True)


# ===========================
#   Styles Navbar (clair)
# ===========================

NAV_STYLE = {
    "position": "sticky",
    "top": 0,
    "zIndex": 1000,
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "space-between",
    "padding": "10px 24px",
    "backgroundColor": "#ffffff",
    "borderBottom": "1px solid #e5e7eb",
}

NAV_BRAND_STYLE = {
    "display": "flex",
    "alignItems": "center",
    "gap": "10px",
    "color": "#111827",
}

NAV_LINKS_CONTAINER_STYLE = {
    "display": "flex",
    "alignItems": "center",
    "gap": "16px",
    "flexWrap": "wrap",
}

NAV_LINK_STYLE = {
    "color": "#4b5563",
    "textDecoration": "none",
    "fontSize": "0.92rem",
    "padding": "4px 0",
    "borderBottom": "2px solid transparent",
}

NAV_LINK_ACTIVE = {
    "color": "#111827",
    "fontWeight": 600,
    "borderBottom": "2px solid #2563eb",  # bleu discret
}


# ===========================
#   Layout global
# ===========================

app.layout = html.Div(
    style={"backgroundColor": "#f5f5f5", "minHeight": "100vh"},
    children=[
        dcc.Location(id="url", refresh=False),

        # --- NAVBAR ---
        html.Nav(
            style=NAV_STYLE,
            children=[
                # Logo + titre
                html.Div(
                    style=NAV_BRAND_STYLE,
                    children=[
                        html.Img(
                            src="/assets/logo.png",
                            alt="Logo",
                            style={"height": "34px"},
                        ),
                        html.Div(
                            children=[
                                html.Div(
                                    "Laboratoire Éphévériste",
                                    style={"fontSize": "1rem", "fontWeight": 600},
                                ),
                                html.Div(
                                    "Modèle de Résonance Ontogénétique (MRO)",
                                    style={
                                        "fontSize": "0.72rem",
                                        "color": "#6b7280",
                                    },
                                ),
                            ]
                        ),
                    ],
                ),
                # Liens
                html.Div(
                    id="nav-links",
                    style=NAV_LINKS_CONTAINER_STYLE,
                    children=[
                        dcc.Link("Simulations MRO", href="/", id="nav-home", style=NAV_LINK_STYLE),
                        dcc.Link("FFT", href="/fft", id="nav-fft", style=NAV_LINK_STYLE),
                        dcc.Link("Explications", href="/docs", id="nav-docs", style=NAV_LINK_STYLE),
                        dcc.Link("Heatmap 3D", href="/heatmap3d", id="nav-hm3d", style=NAV_LINK_STYLE),
                        dcc.Link("Tests & Expériences", href="/experiences", id="nav-exp", style=NAV_LINK_STYLE),
                        dcc.Link("Éphévérisme", href="/epheverisme", id="nav-eph", style=NAV_LINK_STYLE),
                        dcc.Link("Auteur", href="/jules", id="nav-jules", style=NAV_LINK_STYLE),
                        dcc.Link("GitHub", href="/repository", id="nav-git", style=NAV_LINK_STYLE),
                        dcc.Link("Crédits", href="/credits", id="nav-credits", style=NAV_LINK_STYLE),
                    ],
                ),
            ],
        ),

        # --- CONTENU DES PAGES ---
        html.Div(
            dash.page_container,
            style={
                "padding": "24px",
                "maxWidth": "1200px",
                "margin": "0 auto",
            },
        ),
        # Conteneurs cachés pour JSON-LD et meta dynamiques
        html.Div(id="structured-jsonld", style={"display": "none"}),
        html.Div(id="dynamic-meta", style={"display": "none"}),
    ],
)


# ===========================
#   Navbar active (highlight)
# ===========================

@callback(
    [
        Output("nav-home", "style"),
        Output("nav-fft", "style"),
        Output("nav-docs", "style"),
        Output("nav-hm3d", "style"),
        Output("nav-exp", "style"),
        Output("nav-eph", "style"),
        Output("nav-jules", "style"),
        Output("nav-git", "style"),
        Output("nav-credits", "style"),
    ],
    Input("url", "pathname"),
)
def highlight_active(pathname):
    base = NAV_LINK_STYLE
    active = {**NAV_LINK_STYLE, **NAV_LINK_ACTIVE}

    def s(path):
        return active if pathname == path else base

    return [
        s("/"),
        s("/fft"),
        s("/docs"),
        s("/heatmap3d"),
        s("/experiences"),
        s("/epheverisme"),
        s("/jules"),
        s("/repository"),
        s("/credits"),
    ]


# ===========================
#   JSON-LD & Meta dynamiques (côté "serveur")
# ===========================

@callback(
    Output("structured-jsonld", "children"),
    Output("dynamic-meta", "children"),
    Input("url", "pathname"),
)
def inject_structured_data(pathname):
    # Base & canonical
    try:
        base = request.url_root.rstrip("/")
    except Exception:
        base = "https://epheverisme.art"
    path = pathname or "/"
    canonical = base + (path if path != "/" else "/")

    # Titres / descriptions par page
    titles = {
        "/": "Simulations MRO",
        "/docs": "Explications",
        "/fft": "FFT",
        "/heatmap3d": "Heatmap 3D",
        "/experiences": "Tests & Expériences",
        "/epheverisme": "Éphévérisme",
        "/jules": "Auteur",
        "/repository": "Code source (GitHub)",
        "/credits": "Crédits",
        "/search": "Recherche",
        "/pharmasim": "PharmaSim",
    }
    descs = {
        "/": "Visualisations interactives du Modèle de Résonance Ontogénétique",
        "/docs": "Explications du MRO et guide de lecture",
        "/fft": "Analyse fréquentielle des signaux MRO",
        "/heatmap3d": "Heatmap 3D des paramètres (m, γ, k)",
        "/experiences": "Tests et expériences externes du MRO",
        "/epheverisme": "Présentation de l’éphévérisme",
        "/jules": "Page auteur : Jules Henissart‑Miquel",
        "/repository": "Dépôt GitHub du projet",
        "/credits": "Crédits et mentions",
        "/search": "Recherche des pages du site",
        "/pharmasim": "Simulation PK/PD (recherche, noindex)",
    }
    title = titles.get(path, "Laboratoire Éphévériste — MRO")
    desc = descs.get(path, "Explorations MRO")

    # Breadcrumbs
    segments = [seg for seg in path.split("/") if seg]
    crumbs = [{"@type": "ListItem", "position": 1, "name": "Accueil", "item": base + "/"}]
    acc = ""
    labels = {
        "docs": "Explications",
        "fft": "FFT",
        "heatmap3d": "Heatmap 3D",
        "experiences": "Tests & Expériences",
        "epheverisme": "Éphévérisme",
        "jules": "Auteur",
        "repository": "Code source",
        "credits": "Crédits",
        "search": "Recherche",
        "pharmasim": "PharmaSim",
    }
    for i, seg in enumerate(segments):
        acc += "/" + seg
        crumbs.append({
            "@type": "ListItem",
            "position": i + 2,
            "name": labels.get(seg, seg),
            "item": base + acc,
        })

    # JSON-LD payload de base
    payload = [
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "url": canonical,
            "name": title,
            "description": desc,
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": crumbs,
        },
    ]

    # JSON-LD Person pour /jules
    if path == "/jules":
        payload.append({
            "@context": "https://schema.org",
            "@type": "Person",
            "name": "Jules Henissart‑Miquel",
            "url": base + "/jules",
            "sameAs": [
                "https://orcid.org/0009-0007-1822-5741",
                "https://github.com/henissartj",
                "https://www.linkedin.com/in/henissartmiqueljules/",
                "https://scholar.google.com/citations?user=_20OPpsAAAAJ&hl=fr"
            ]
        })

    # Éléments à injecter dans le DOM
    jsonld = html.Script(json.dumps(payload), type="application/ld+json")
    metas = [
        html.Link(rel="canonical", href=canonical),
        # Dash html.Meta ne supporte pas l'attribut "property" ;
        # on encode OG via name et un script assets convertira en property dans <head>.
        html.Meta(name="og:title", content=title),
        html.Meta(name="og:description", content=desc),
        html.Meta(name="og:url", content=canonical),
        html.Meta(name="og:type", content="website"),
        html.Meta(name="og:image", content=base + "/assets/og-image.png"),
        # Twitter utilise déjà name=*
        html.Meta(name="twitter:card", content="summary_large_image"),
        html.Meta(name="twitter:title", content=title),
        html.Meta(name="twitter:description", content=desc),
        html.Meta(name="twitter:image", content=base + "/assets/og-image.png"),
    ]

    # Noindex pour PharmaSim
    if path == "/pharmasim":
        metas.append(html.Meta(name="robots", content="noindex"))
    return jsonld, metas


# ===========================
#   Callbacks : sliders labels
# ===========================

@callback(Output("m-val", "children"), Input("m", "value"))
def show_m(v):
    return f"m = {v:.2f}"


@callback(Output("gamma-val", "children"), Input("gamma", "value"))
def show_g(v):
    return f"γ = {v:.3f}"


@callback(Output("k-val", "children"), Input("k", "value"))
def show_k(v):
    return f"k = {v:.2f}"


@callback(Output("x0-val", "children"), Input("x0", "value"))
def show_x0(v):
    return f"x(0) = {v:.2f}"


@callback(Output("v0-val", "children"), Input("v0", "value"))
def show_v0(v):
    return f"v(0) = {v:.2f}"


@callback(Output("tend-val", "children"), Input("tend", "value"))
def show_tend(v):
    return f"t_end = {v:.0f}"

# ===========================
#   Callbacks : équations
# ===========================

@callback(
    Output("equation-display", "children"),
    Input("m", "value"),
    Input("gamma", "value"),
    Input("k", "value"),
)
def update_equation(m, gamma, k):
    if m is None or gamma is None or k is None:
        raise PreventUpdate
    return f"Équation : {m:.2f}·d²x/dt² + {gamma:.2f}·dx/dt + {k:.2f}·x = 0"

# ===========================
#   Callbacks : figures
# ===========================

@callback(
    Output("time-series", "figure"),
    Output("phase-space", "figure"),
    Output("energy-graph", "figure"),
    Output("acc-graph", "figure"),
    Input("m", "value"),
    Input("gamma", "value"),
    Input("k", "value"),
    Input("x0", "value"),
    Input("v0", "value"),
    Input("tend", "value"),
    Input("opts", "value"),
    State("ts-annotations", "data"),
    State("ts-shapes", "data"),
)
def update_core_plots(m, gamma, k, x0, v0, tend, opts, annotations, shapes):
    t, x, v = simulate_mro(m=m, gamma=gamma, k=k, x0=x0, v0=v0, t_end=tend)
    a = -(gamma / m) * v - (k / m) * x
    ek = 0.5 * m * (v ** 2)
    ep = 0.5 * k * (x ** 2)
    et = ek + ep

    # --- Série temporelle ---
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=t, y=x, mode="lines", name="x(t)"))
    fig_ts.update_layout(
        xaxis_title="Temps",
        yaxis_title="Amplitude x(t)",
        title="x(t)",
    )

    # Annotations texte (directement sur le graphe)
    if annotations:
        for ann in annotations:
            fig_ts.add_annotation(
                x=ann["x"],
                y=ann["y"],
                text=ann["label"],
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-25,
                font={"size": 10},
            )

    # Formes dessinées (shapes)
    if shapes:
        fig_ts.update_layout(shapes=shapes)

    # --- Espace des phases ---
    fig_ph = go.Figure()
    fig_ph.add_trace(go.Scatter(x=x, y=v, mode="lines", name="Trajectoire"))
    fig_ph.update_layout(
        xaxis_title="x",
        yaxis_title="dx/dt",
        title="Espace des phases",
    )
    fig_e = go.Figure()
    fig_e.add_trace(go.Scatter(x=t, y=ek, mode="lines", name="E_kin"))
    fig_e.add_trace(go.Scatter(x=t, y=ep, mode="lines", name="E_pot"))
    fig_e.add_trace(go.Scatter(x=t, y=et, mode="lines", name="E_tot"))
    fig_e.update_layout(
        xaxis_title="Temps",
        yaxis_title="Énergie",
        title="Énergie du système",
    )

    fig_a = go.Figure()
    fig_a.add_trace(go.Scatter(x=t, y=a, mode="lines", name="a(t)"))
    fig_a.update_layout(
        xaxis_title="Temps",
        yaxis_title="Accélération",
        title="a(t)",
    )

    if opts and ("grid" in opts):
        for fig in (fig_ts, fig_ph, fig_e, fig_a):
            fig.update_xaxes(showgrid=True)
            fig.update_yaxes(showgrid=True)

    return fig_ts, fig_ph, fig_e, fig_a

# Annotations

@callback(
    Output("ts-annotations", "data"),
    Output("annot-list", "children"),
    Input("time-series", "clickData"),
    State("annot-label", "value"),
    State("ts-annotations", "data"),
    prevent_initial_call=True,
)
def add_annotation(clickData, label, data):
    # Pas de texte ou pas de clic => on ne fait rien
    if not clickData or not label:
        raise PreventUpdate

    data = data or []

    point = clickData["points"][0]
    x = point.get("x")
    y = point.get("y")
    if x is None or y is None:
        raise PreventUpdate

    # Ajoute l'annotation
    data.append({"x": float(x), "y": float(y), "label": label})

    # Liste lisible sous le graphe
    items = [
        html.Li(f"{i+1}. t={ann['x']:.3f}, x={ann['y']:.3f} — {ann['label']}")
        for i, ann in enumerate(data)
    ]

    return data, items

# Callback des dessins

@callback(
    Output("ts-shapes", "data"),
    Input("time-series", "relayoutData"),
    prevent_initial_call=True,
)
def sync_drawn_shapes(relayoutData):
    if relayoutData and "shapes" in relayoutData:
        return relayoutData["shapes"]
    raise PreventUpdate




# (Supprimé) Callback heatmap 2D orphelin — géré dans pages/heatmap3d.py


# ===========================
#   Export ZIP helpers
# ===========================

def _build_core_figs(
    m,
    gamma,
    k,
    x0,
    v0,
    tend,
    presets,
    heat_gmin,
    heat_gmax,
    heat_gstep,
    heat_kmin,
    heat_kmax,
    heat_kstep,
):
    t, x, v = simulate_mro(m=m, gamma=gamma, k=k, x0=x0, v0=v0, t_end=tend)
    a = -(gamma / m) * v - (k / m) * x
    ek = 0.5 * m * (v ** 2)
    ep = 0.5 * k * (x ** 2)
    et = ek + ep

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=t, y=x, mode="lines", name="x(t)"))
    fig_ts.update_layout(
        xaxis_title="Temps",
        yaxis_title="Amplitude x(t)",
        title="x(t)",
    )

    fig_ph = go.Figure()
    fig_ph.add_trace(go.Scatter(x=x, y=v, mode="lines", name="Trajectoire"))
    fig_ph.update_layout(
        xaxis_title="x",
        yaxis_title="dx/dt",
        title="Espace des phases",
    )

    fig_e = go.Figure()
    fig_e.add_trace(go.Scatter(x=t, y=ek, mode="lines", name="E_kin"))
    fig_e.add_trace(go.Scatter(x=t, y=ep, mode="lines", name="E_pot"))
    fig_e.add_trace(go.Scatter(x=t, y=et, mode="lines", name="E_tot"))
    fig_e.update_layout(
        xaxis_title="Temps",
        yaxis_title="Énergie",
        title="Énergie du système",
    )

    fig_a = go.Figure()
    fig_a.add_trace(go.Scatter(x=t, y=a, mode="lines", name="a(t)"))
    fig_a.update_layout(
        xaxis_title="Temps",
        yaxis_title="Accélération",
        title="a(t)",
    )

    gammas = np.arange(float(heat_gmin), float(heat_gmax) + 1e-9, float(heat_gstep))
    ks = np.arange(float(heat_kmin), float(heat_kmax) + 1e-9, float(heat_kstep))
    Z = heatmap_max_amp(
        gammas,
        ks,
        m=1.0,
        x0=1.0,
        v0=0.0,
        t_end=float(tend),
        t_points=800,
    )
    fig_heat = px.imshow(
        Z,
        x=ks,
        y=gammas,
        aspect="auto",
        origin="lower",
        labels=dict(x="k", y="γ", color="max |x(t)|"),
        title="Max |x(t)| selon (γ, k)",
    )

    fig_multi = go.Figure()
    if presets:
        for i, d in enumerate(presets):
            tt, xx, vv = simulate_mro(
                m=d["m"],
                gamma=d["gamma"],
                k=d["k"],
                x0=x0,
                v0=v0,
                t_end=tend,
            )
            fig_multi.add_trace(
                go.Scatter(x=tt, y=xx, mode="lines", name=f"Preset {i+1}")
            )
    fig_multi.update_layout(
        xaxis_title="Temps",
        yaxis_title="x(t)",
        title="Comparaison de séries",
    )

    return {
        "time_series": fig_ts,
        "phase_space": fig_ph,
        "energy": fig_e,
        "acc": fig_a,
        "heatmap": fig_heat,
        "multi_series": fig_multi,
    }


def _add_png_and_svg_to_zip(zf, fig, basename, width=2400, height=1400, scale=1):
    try:
        png_bytes = pio.to_image(
            fig, format="png", width=width, height=height, scale=scale
        )
        zf.writestr(f"{basename}.png", png_bytes)
    except Exception as e:
        zf.writestr(
            f"{basename}_PNG_ERROR.txt",
            f"PNG render failed: {e!r}",
        )

    try:
        svg_bytes = pio.to_image(
            fig, format="svg", width=width, height=height, scale=scale
        )
        zf.writestr(f"{basename}.svg", svg_bytes)
    except Exception as e:
        zf.writestr(
            f"{basename}_SVG_ERROR.txt",
            f"SVG render failed: {e!r}",
        )


# ===========================
#   Export ZIP callback
# ===========================

@callback(
    Output("download-zip", "data"),
    Input("btn-export-zip", "n_clicks"),
    State("m", "value"),
    State("gamma", "value"),
    State("k", "value"),
    State("x0", "value"),
    State("v0", "value"),
    State("tend", "value"),
    State("presets-store", "data"),
    State("g-min", "value"),
    State("g-max", "value"),
    State("g-step", "value"),
    State("k-min", "value"),
    State("k-max", "value"),
    State("k-step", "value"),
    prevent_initial_call=True,
)
def export_zip(
    n,
    m,
    gamma,
    k,
    x0,
    v0,
    tend,
    presets,
    gmin,
    gmax,
    gstep,
    kmin,
    kmax,
    kstep,
):
    if not n:
        return dash.no_update

    figs = _build_core_figs(
        m,
        gamma,
        k,
        x0,
        v0,
        tend,
        presets or [],
        gmin,
        gmax,
        gstep,
        kmin,
        kmax,
        kstep,
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(
        buf,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zf:
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M")
        _add_png_and_svg_to_zip(zf, figs["time_series"], f"time_series_{ts}")
        _add_png_and_svg_to_zip(zf, figs["phase_space"], f"phase_space_{ts}")
        _add_png_and_svg_to_zip(zf, figs["energy"], f"energy_{ts}")
        _add_png_and_svg_to_zip(zf, figs["acc"], f"acc_{ts}")
        _add_png_and_svg_to_zip(zf, figs["heatmap"], f"heatmap_{ts}")
        _add_png_and_svg_to_zip(zf, figs["multi_series"], f"multi_series_{ts}")
        zf.writestr(
            "README.txt",
            (
                "Exports MRO (PNG+SVG HD)\n"
                f"Paramètres courants: m={m}, gamma={gamma}, k={k}, x0={x0}, v0={v0}, t_end={tend}\n"
                f"Grille heatmap: gamma=[{gmin},{gmax}] step {gstep} ; "
                f"k=[{kmin},{kmax}] step {kstep}\n"
            ),
        )

    buf.seek(0)
    filename = f"mro_exports_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    return dcc.send_bytes(buf.getvalue(), filename)


# ===========================
#   Export CSV / JSON
# ===========================

@callback(
    Output("download-csv", "data"),
    Input("btn-export-csv", "n_clicks"),
    State("m", "value"),
    State("gamma", "value"),
    State("k", "value"),
    State("x0", "value"),
    State("v0", "value"),
    State("tend", "value"),
    prevent_initial_call=True,
)
def export_csv(n, m, gamma, k, x0, v0, tend):
    if not n:
        return dash.no_update
    t, x, v = simulate_mro(m=m, gamma=gamma, k=k, x0=x0, v0=v0, t_end=tend)
    a = -(gamma / m) * v - (k / m) * x
    ek = 0.5 * m * (v ** 2)
    ep = 0.5 * k * (x ** 2)
    et = ek + ep
    sio = io.StringIO()
    sio.write("t,x,v,a,E_kin,E_pot,E_tot\n")
    for i in range(len(t)):
        sio.write(f"{t[i]},{x[i]},{v[i]},{a[i]},{ek[i]},{ep[i]},{et[i]}\n")
    sio.seek(0)
    fname = f"mro_data_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return dcc.send_string(sio.getvalue(), filename=fname)


@callback(
    Output("download-json", "data"),
    Input("btn-export-json", "n_clicks"),
    State("m", "value"),
    State("gamma", "value"),
    State("k", "value"),
    State("x0", "value"),
    State("v0", "value"),
    State("tend", "value"),
    prevent_initial_call=True,
)
def export_json(n, m, gamma, k, x0, v0, tend):
    if not n:
        return dash.no_update
    t, x, v = simulate_mro(m=m, gamma=gamma, k=k, x0=x0, v0=v0, t_end=tend)
    a = -(gamma / m) * v - (k / m) * x
    ek = 0.5 * m * (v ** 2)
    ep = 0.5 * k * (x ** 2)
    et = ek + ep
    payload = {
        "params": {"m": m, "gamma": gamma, "k": k, "x0": x0, "v0": v0, "t_end": tend},
        "series": {
            "t": list(map(float, t)),
            "x": list(map(float, x)),
            "v": list(map(float, v)),
            "a": list(map(float, a)),
            "E_kin": list(map(float, ek)),
            "E_pot": list(map(float, ep)),
            "E_tot": list(map(float, et)),
        },
    }
    fname = f"mro_data_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.json"
    return dcc.send_string(json.dumps(payload), filename=fname)


# ===========================
#   Presets multi-séries
# ===========================

@callback(
    Output("presets-store", "data"),
    Output("presets-list", "children"),
    Input("add-preset", "n_clicks"),
    State("preset-m", "value"),
    State("preset-g", "value"),
    State("preset-k", "value"),
    State("presets-store", "data"),
    prevent_initial_call=True,
)
def add_preset(n, m, g, k, data):
    if not n:
        raise PreventUpdate

    data = data or []
    try:
        m = float(m)
        g = float(g)
        k = float(k)
    except Exception:
        # Ignore invalid inputs
        raise PreventUpdate

    data.append({"m": m, "gamma": g, "k": k})

    chips = [
        html.Span(
            f"Preset {i+1}: m={d['m']}, γ={d['gamma']}, k={d['k']}",
            style={
                "padding": "6px 10px",
                "border": "1px solid #ddd",
                "borderRadius": "12px",
                "marginRight": "6px",
                "display": "inline-block",
            },
        )
        for i, d in enumerate(data)
    ]

    return data, html.Div(chips, style={"marginTop": "8px"})


@callback(
    Output("multi-series", "figure"),
    Input("presets-store", "data"),
    State("x0", "value"),
    State("v0", "value"),
    State("tend", "value"),
)
def update_multi(data, x0, v0, tend):
    fig = go.Figure()
    # Affiche au moins une grille vide pour UX
    fig.update_layout(
        xaxis_title="Temps",
        yaxis_title="x(t)",
        title="Comparaison de séries",
    )

    if not data:
        return fig

    # Boucle sur presets
    for i, d in enumerate(data):
        try:
            t, x, v = simulate_mro(
                m=float(d.get("m", 1.0)),
                gamma=float(d.get("gamma", 0.15)),
                k=float(d.get("k", 1.0)),
                x0=float(x0),
                v0=float(v0),
                t_end=float(tend),
            )
        except Exception:
            # Si un preset est invalide, on continue
            continue

        fig.add_trace(
            go.Scatter(x=t, y=x, mode="lines", name=f"Preset {i+1}")
        )

    return fig


# ===========================
#   Snapshots (URL)
# ===========================

@callback(
    Output("m", "value"),
    Output("gamma", "value"),
    Output("k", "value"),
    Output("x0", "value"),
    Output("v0", "value"),
    Output("tend", "value"),
    Input("mro-url", "search"),
    prevent_initial_call=False,
)
def load_params_from_url(search):
    if not search:
        raise PreventUpdate

    qs = parse_qs(search.lstrip("?"))

    def get(name, default, cast=float):
        try:
            return cast(qs.get(name, [default])[0])
        except Exception:
            return default

    m = get("m", 1.0)
    gamma = get("g", 0.15)
    k = get("k", 1.0)
    x0 = get("x0", 1.0)
    v0 = get("v0", 0.0)
    tend = get("t", 30.0, float)

    return m, gamma, k, x0, v0, tend


@callback(
    Output("share-link-output", "value"),
    Input("share-link-btn", "n_clicks"),
    State("m", "value"),
    State("gamma", "value"),
    State("k", "value"),
    State("x0", "value"),
    State("v0", "value"),
    State("tend", "value"),
    State("mro-url", "href"),
    prevent_initial_call=True,
)
def generate_snapshot_link(n, m, gamma, k, x0, v0, tend, href):
    if not n or not href:
        raise PreventUpdate

    base = href.split("?", 1)[0]
    params = {
        "m": round(m, 5),
        "g": round(gamma, 5),
        "k": round(k, 5),
        "x0": round(x0, 5),
        "v0": round(v0, 5),
        "t": round(tend, 5),
    }
    url = base + "?" + urlencode(params)
    return url


# ===========================
#   Export client (PNG / SVG)
# ===========================

app.clientside_callback(
    """
    function(n_png, n_svg) {
        const ctx = window.dash_clientside && window.dash_clientside.callback_context;
        if (!ctx || (!n_png && !n_svg)) {
            return window.dash_clientside.no_update;
        }

        const trig = ctx.triggered && ctx.triggered[0] && ctx.triggered[0].prop_id || "";
        const format = trig.includes("btn-export-svg") ? "svg" : "png";

        const graphs = Array.from(document.querySelectorAll('.js-plotly-plot'))
            .filter(g => g._fullLayout && g._fullData && g._fullData.length > 0);

        if (graphs.length === 0) {
            alert("Aucun graphique détecté — générez d’abord une figure avant d’exporter.");
            return window.dash_clientside.no_update;
        }

        graphs.forEach((g, idx) => {
            const title = (g._fullLayout && g._fullLayout.title && g._fullLayout.title.text)
                ? g._fullLayout.title.text
                : `figure_${idx + 1}`;
            const fname = title.replace(/[^a-z0-9-_]+/gi, '_').toLowerCase();

            Plotly.downloadImage(g, {
                format: format,
                filename: fname,
                width: g._fullLayout.width || 1200,
                height: g._fullLayout.height || 700,
                scale: 2
            }).catch(err => console.error("Erreur d’export :", err));
        });

        return Date.now();
    }
    """,
    Output("export-done", "data"),
    Input("btn-export-png", "n_clicks"),
    Input("btn-export-svg", "n_clicks"),
    prevent_initial_call=True,
)


# ===========================
#   Run
# ===========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8050)),
        debug=False,
    )
