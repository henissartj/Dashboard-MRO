import numpy as np
from scipy.integrate import solve_ivp

import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import plotly.graph_objects as go
import plotly.express as px
import textwrap
import io, zipfile, datetime as dt
import plotly.io as pio

# ---------- Modèle MRO ----------
def MRO_equations(t, Y, m, gamma, k):
    x, dxdt = Y
    dxdtt = -(gamma/m)*dxdt - (k/m)*x
    return [dxdt, dxdtt]

def simulate_mro(m=1.0, gamma=0.15, k=1.0, x0=1.0, v0=0.0,
                 t_start=0.0, t_end=30.0, t_points=3000):
    t_eval = np.linspace(t_start, t_end, t_points)
    sol = solve_ivp(
        MRO_equations,
        [t_start, t_end],
        [x0, v0],
        args=(m, gamma, k),
        t_eval=t_eval,
        method='RK45'
    )
    t = sol.t
    x = sol.y[0]
    v = sol.y[1]
    return t, x, v

def heatmap_max_amp(gammas, ks, m=1.0, x0=1.0, v0=0.0, t_end=30.0, t_points=2000):
    # Carte du max |x(t)| sur la période pour un balayage (gamma, k)
    data = np.zeros((len(gammas), len(ks)))
    for i, g in enumerate(gammas):
        for j, kk in enumerate(ks):
            t, x, _ = simulate_mro(m=m, gamma=g, k=kk, x0=x0, v0=v0,
                                   t_start=0, t_end=t_end, t_points=t_points)
            data[i, j] = np.max(np.abs(x))
    return data

# ---------- App Dash ----------
app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title="MRO • Ontogenetic Resonance Model",
    external_stylesheets=[ "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"]
)
server = app.server


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

app.layout = html.Div(
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "24px"},
    children=[

        # --- barre de navigation ---
        html.Div([
            dcc.Link("Accueil", href="/", style={"marginRight": "20px"}),
            dcc.Link("FFT", href="/fft", style={"marginRight": "20px"}),
            dcc.Link("Explications", href="/docs", style={"marginRight": "20px"}),
            dcc.Link("Crédits", href="/credits", style={"marginRight": "20px"}),  # <— AJOUT
        ],
        style={
            "padding": "15px",
            "background": "#eee",
            "borderBottom": "1px solid #ccc",
            "marginBottom": "20px",
        }),

        # --- container de page ---
        dash.page_container
    ]
) 

# ---------- Callbacks d’affichage des valeurs sliders ----------
@callback(Output("m-val", "children"), Input("m", "value"))
def show_m(v): return f"m = {v:.2f}"

@callback(Output("gamma-val", "children"), Input("gamma", "value"))
def show_g(v): return f"γ = {v:.3f}"

@callback(Output("k-val", "children"), Input("k", "value"))
def show_k(v): return f"k = {v:.2f}"

@callback(Output("x0-val", "children"), Input("x0", "value"))
def show_x0(v): return f"x(0) = {v:.2f}"

@callback(Output("v0-val", "children"), Input("v0", "value"))
def show_v0(v): return f"v(0) = {v:.2f}"

@callback(Output("tend-val", "children"), Input("tend", "value"))
def show_tend(v): return f"t_end = {v:.0f}"

# ---------- Callback : time series & phase space ----------
@callback(
    Output("time-series", "figure"),
    Output("phase-space", "figure"),
    Input("m", "value"),
    Input("gamma", "value"),
    Input("k", "value"),
    Input("x0", "value"),
    Input("v0", "value"),
    Input("tend", "value"),
)
def update_core_plots(m, gamma, k, x0, v0, tend):
    t, x, v = simulate_mro(m=m, gamma=gamma, k=k, x0=x0, v0=v0, t_end=tend)
    # Série temporelle
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=t, y=x, mode="lines", name="x(t) - oscillation amortie"))
    fig_ts.update_layout(xaxis_title="Temps", yaxis_title="Amplitude x(t)", title="x(t)")
    # Espace des phases
    fig_ph = go.Figure()
    fig_ph.add_trace(go.Scatter(x=x, y=v, mode="lines", name="Trajectoire"))
    fig_ph.update_layout(xaxis_title="x", yaxis_title="dx/dt", title="Espace des phases")
    return fig_ts, fig_ph

# ---------- Callback : Heatmap ----------
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
    if n == 0:
        # Heatmap par défaut légère
        gammas = np.arange(0.0, 1.01, 0.1)
        ks = np.arange(0.0, 3.01, 0.2)
    else:
        gammas = np.arange(float(gmin), float(gmax)+1e-9, float(gstep))
        ks = np.arange(float(kmin), float(kmax)+1e-9, float(kstep))
    Z = heatmap_max_amp(gammas, ks, m=1.0, x0=1.0, v0=0.0, t_end=float(tend), t_points=1000)
    fig = px.imshow(Z, x=ks, y=gammas, aspect="auto", origin="lower",
                    labels=dict(x="k", y="γ", color="max |x(t)|"),
                    title="Max |x(t)| selon (γ, k)")
    return fig

def _build_core_figs(m, gamma, k, x0, v0, tend, presets, heat_gmin, heat_gmax, heat_gstep, heat_kmin, heat_kmax, heat_kstep):
    # Série temporelle & phase
    t, x, v = simulate_mro(m=m, gamma=gamma, k=k, x0=x0, v0=v0, t_end=tend)
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(x=t, y=x, mode="lines", name="x(t) - oscillation amortie"))
    fig_ts.update_layout(xaxis_title="Temps", yaxis_title="Amplitude x(t)", title="x(t)")

    fig_ph = go.Figure()
    fig_ph.add_trace(go.Scatter(x=x, y=v, mode="lines", name="Trajectoire"))
    fig_ph.update_layout(xaxis_title="x", yaxis_title="dx/dt", title="Espace des phases")

    # Heatmap
    gammas = np.arange(float(heat_gmin), float(heat_gmax)+1e-9, float(heat_gstep))
    ks = np.arange(float(heat_kmin), float(heat_kmax)+1e-9, float(heat_kstep))
    Z = heatmap_max_amp(gammas, ks, m=1.0, x0=1.0, v0=0.0, t_end=float(tend), t_points=800)
    fig_heat = px.imshow(Z, x=ks, y=gammas, aspect="auto", origin="lower",
                         labels=dict(x="k", y="γ", color="max |x(t)|"),
                         title="Max |x(t)| selon (γ, k)")

    # Multi-series
    fig_multi = go.Figure()
    if presets:
        for i, d in enumerate(presets):
            tt, xx, vv = simulate_mro(m=d["m"], gamma=d["gamma"], k=d["k"], x0=x0, v0=v0, t_end=tend)
            fig_multi.add_trace(go.Scatter(x=tt, y=xx, mode="lines", name=f"Preset {i+1}"))
    fig_multi.update_layout(xaxis_title="Temps", yaxis_title="x(t)", title="Comparaison de séries")

    return {
        "time_series": fig_ts,
        "phase_space": fig_ph,
        "heatmap": fig_heat,
        "multi_series": fig_multi
    }

def _add_png_and_svg_to_zip(zf, fig, basename, width=2400, height=1400, scale=1):
    """Ajoute PNG + SVG au ZIP sans faire échouer tout l'export si un rendu plante."""
    # PNG
    try:
        png_bytes = pio.to_image(fig, format="png", width=width, height=height, scale=scale)
        zf.writestr(f"{basename}.png", png_bytes)
    except Exception as e:
        zf.writestr(f"{basename}_PNG_ERROR.txt", f"PNG render failed: {e!r}")

    # SVG
    try:
        svg_bytes = pio.to_image(fig, format="svg", width=width, height=height, scale=scale)
        zf.writestr(f"{basename}.svg", svg_bytes)
    except Exception as e:
        zf.writestr(f"{basename}_SVG_ERROR.txt", f"SVG render failed: {e!r}")

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
    prevent_initial_call=True
)
def export_zip(n, m, gamma, k, x0, v0, tend, presets, gmin, gmax, gstep, kmin, kmax, kstep):
    if not n:
        return dash.no_update
    # Construire les figures
    figs = _build_core_figs(m, gamma, k, x0, v0, tend, presets or [],
                            gmin, gmax, gstep, kmin, kmax, kstep)
    # Construire le ZIP en mémoire
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M")
        # Ajoute PNG + SVG pour chaque figure
        _add_png_and_svg_to_zip(zf, figs["time_series"], f"time_series_{ts}")
        _add_png_and_svg_to_zip(zf, figs["phase_space"], f"phase_space_{ts}")
        _add_png_and_svg_to_zip(zf, figs["heatmap"], f"heatmap_{ts}")
        _add_png_and_svg_to_zip(zf, figs["multi_series"], f"multi_series_{ts}")
        # README
        zf.writestr("README.txt",
                    "Exports MRO (PNG+SVG HD)\n"
                    f"Paramètres courants: m={m}, gamma={gamma}, k={k}, x0={x0}, v0={v0}, t_end={tend}\n"
                    f"Grille heatmap: gamma=[{gmin},{gmax}] step {gstep} ; k=[{kmin},{kmax}] step {kstep}\n")
    buf.seek(0)
    filename = f"mro_exports_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    return dcc.send_bytes(buf.getvalue(), filename)


# ---------- Presets multi-series ----------
@callback(
    Output("presets-store", "data"),
    Output("presets-list", "children"),
    Input("add-preset", "n_clicks"),
    State("preset-m", "value"),
    State("preset-g", "value"),
    State("preset-k", "value"),
    State("presets-store", "data"),
    prevent_initial_call=True
)
def add_preset(n, m, g, k, data):
    data = data or []
    data.append({"m": float(m), "gamma": float(g), "k": float(k)})
    # Liste lisible
    chips = [html.Span(f"Preset {i+1}: m={d['m']}, γ={d['gamma']}, k={d['k']}",
                       style={"padding": "6px 10px", "border": "1px solid #ddd", "borderRadius": "12px",
                              "marginRight": "6px", "display": "inline-block"}) for i, d in enumerate(data)]
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
            t, x, v = simulate_mro(m=d["m"], gamma=d["gamma"], k=d["k"], x0=x0, v0=v0, t_end=tend)
            fig.add_trace(go.Scatter(x=t, y=x, mode="lines", name=f"Preset {i+1}"))
    fig.update_layout(xaxis_title="Temps", yaxis_title="x(t)", title="Comparaison de séries")
    return fig

# ---- Export client factorisé (PNG / SVG) ----
app.clientside_callback(
    """
    function(n_png, n_svg) {
        const ctx = window.dash_clientside && window.dash_clientside.callback_context;
        if (!ctx || (!n_png && !n_svg)) { return window.dash_clientside.no_update; }

        // Détermine quel bouton a déclenché
        const trig = ctx.triggered && ctx.triggered[0] && ctx.triggered[0].prop_id || "";
        let format = "png";
        if (trig.indexOf("btn-export-svg") !== -1) format = "svg";

        const graphs = document.querySelectorAll('.js-plotly-plot');
        graphs.forEach((g, idx) => {
            const title = (g._fullLayout && g._fullLayout.title && g._fullLayout.title.text) ? g._fullLayout.title.text : `figure_${idx+1}`;
            const fname = title.replace(/[^a-z0-9-_]+/gi, '_').toLowerCase();
            Plotly.downloadImage(g, {
                format: format,
                filename: fname,
                width: g._fullLayout.width || 1200,
                height: g._fullLayout.height || 700
            });
        });
        return Date.now();
    }
    """,
    Output("export-done", "data"),
    Input("btn-export-png", "n_clicks"),
    Input("btn-export-svg", "n_clicks"),
    prevent_initial_call=True
)

@callback(Output("fft-tend-val", "children"), Input("fft-tend", "value"))
def _fft_tend_lbl(v): return f"t_end (FFT) = {v:.0f}"

@callback(Output("fft-npow-val", "children"), Input("fft-npow", "value"))
def _fft_npow_lbl(v): return f"N = 2^{int(v)} points"

@callback(
    Output("fft-graph", "figure"),
    Input("fft-tend", "value"),
    Input("fft-npow", "value"),
    State("m", "value"),
    State("gamma", "value"),
    State("k", "value"),
    State("x0", "value"),
    State("v0", "value"),
)
def _fft_plot(tend_fft, npow, m, gamma, k, x0, v0):
    # Re-simule x(t) avec le t_end demandé pour la FFT
    t, x, v = simulate_mro(m=m, gamma=gamma, k=k, x0=x0, v0=v0, t_end=tend_fft)
    # FFT
    n = int(2**int(npow))
    # Interpolation/échantillonnage régulier sur la fenêtre
    t_uniform = np.linspace(t[0], t[-1], n)
    x_uniform = np.interp(t_uniform, t, x)
    dt_s = (t_uniform[-1] - t_uniform[0]) / (n - 1 + 1e-12)
    X = np.fft.rfft(x_uniform)
    freqs = np.fft.rfftfreq(n, d=dt_s)
    mag = np.abs(X)
    # Pic dominant (hors f=0)
    if len(mag) > 1:
        idx_peak = int(np.argmax(mag[1:])) + 1
        f_peak = freqs[idx_peak]
        y_peak = mag[idx_peak]
    else:
        f_peak, y_peak = 0.0, 0.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=freqs, y=mag, mode="lines", name="|FFT(x)|"))
    fig.update_layout(xaxis_title="Fréquence (a.u.)", yaxis_title="Amplitude spectrale", title="Spectre |FFT(x)|")
    if y_peak > 0:
        fig.add_vline(x=f_peak, line_dash="dash", annotation_text=f"f* ≈ {f_peak:.3g}", annotation_position="top")
    return fig


