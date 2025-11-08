import os
import io
import zipfile
import datetime as dt
from urllib.parse import urlencode, parse_qs

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
#   index_string (SEO)
# ===========================

app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard MRO — Modèle de Résonance Ontogénétique</title>

        <!-- SEO -->
        <meta name="description" content="Modèle de Résonance Ontogénétique (MRO) — simulateur scientifique et visuel interactif explorant la dissipation constructive et la mémoire dynamique.">
        <meta name="author" content="Jules Henissart-Miquel">
        <meta name="keywords" content="MRO, résonance ontogénétique, dissipation constructive, système dynamique, attracteur, plasticité, ontogenèse, éphévérisme, neuro-esthétique">
        <meta name="robots" content="index, follow">

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

        {%metas%}
        {%favicon%}
        {%css%}
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
    Input("m", "value"),
    Input("gamma", "value"),
    Input("k", "value"),
    Input("x0", "value"),
    Input("v0", "value"),
    Input("tend", "value"),
    State("ts-annotations", "data"),
    State("ts-shapes", "data"),
)
def update_core_plots(m, gamma, k, x0, v0, tend, annotations, shapes):
    t, x, v = simulate_mro(m=m, gamma=gamma, k=k, x0=x0, v0=v0, t_end=tend)

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

    return fig_ts, fig_ph

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
    State("ts-shapes", "data"),
    prevent_initial_call=True,
)
def sync_drawn_shapes(relayoutData, current_shapes):
    if not relayoutData:
        raise PreventUpdate

    # Cas 1 : Plotly envoie tout le tableau de shapes
    if "shapes" in relayoutData:
        return relayoutData["shapes"]

    # Cas 2 : maj partielle type "shapes[0].x0", "shapes[1].path", etc.
    # On reconstruit à partir de l'état actuel
    shapes = list(current_shapes or [])

    # Ajout / modif individuelle
    # Exemple: {'shapes[0].x0': 1.2, 'shapes[0].x1': 2.3, ...}
    edited = {}
    for key, val in relayoutData.items():
        if key.startswith("shapes["):
            idx = int(key.split("[")[1].split("]")[0])
            prop = key.split(".", 1)[1] if "." in key else None
            if idx not in edited:
                edited[idx] = {}
            if prop:
                edited[idx][prop] = val

    for idx, updates in edited.items():
        # Étend la liste si besoin
        while len(shapes) <= idx:
            shapes.append({})
        shapes[idx].update(updates)

    # Cas 3 : effacement via eraseshape -> relayoutData contient des clefs vides
    # Si Plotly envoie 'shapes[2]': null, on peut filtrer:
    shapes = [s for s in shapes if s]  # nettoie les shapes vides

    return shapes or []




@callback(
    Output("heatmap", "figure"),
    Input("btn-heat", "n_clicks"),
    State("g-min", "value"),
    State("g-max", "value"),
    State("g-step", "value"),
    State("k-min", "value"),
    State("k-max", "value"),
    State("k-step", "value"),
    State("tend", "value"),
)
def update_heatmap(n, gmin, gmax, gstep, kmin, kmax, kstep, tend):
    if not n:
        gammas = np.arange(0.0, 1.01, 0.1)
        ks = np.arange(0.0, 3.01, 0.2)
    else:
        gammas = np.arange(float(gmin), float(gmax) + 1e-9, float(gstep))
        ks = np.arange(float(kmin), float(kmax) + 1e-9, float(kstep))

    Z = heatmap_max_amp(
        gammas,
        ks,
        m=1.0,
        x0=1.0,
        v0=0.0,
        t_end=float(tend),
        t_points=1000,
    )

    fig = px.imshow(
        Z,
        x=ks,
        y=gammas,
        aspect="auto",
        origin="lower",
        labels=dict(x="k", y="γ", color="max |x(t)|"),
        title="Max |x(t)| selon (γ, k)",
    )
    return fig


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
    data = data or []
    data.append({"m": float(m), "gamma": float(g), "k": float(k)})

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
    if data:
        for i, d in enumerate(data):
            t, x, v = simulate_mro(
                m=d["m"],
                gamma=d["gamma"],
                k=d["k"],
                x0=x0,
                v0=v0,
                t_end=tend,
            )
            fig.add_trace(
                go.Scatter(x=t, y=x, mode="lines", name=f"Preset {i+1}")
            )
    fig.update_layout(
        xaxis_title="Temps",
        yaxis_title="x(t)",
        title="Comparaison de séries",
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
    app.run_server(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8050)),
        debug=False,
    )