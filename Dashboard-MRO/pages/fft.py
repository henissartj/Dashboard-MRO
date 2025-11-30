import numpy as np
from scipy.integrate import solve_ivp

import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.graph_objects as go

dash.register_page(
    __name__,
    path="/fft",
    name="FFT avancée",
)

# --- Modèle local (indépendant) ---
def MRO_equations(t, Y, m, gamma, k):
    x, dxdt = Y
    d2x = -(gamma / m) * dxdt - (k / m) * x
    return [dxdt, d2x]

def simulate_mro(m, gamma, k, x0, v0, t_end, t_points=4000):
    t_eval = np.linspace(0, t_end, t_points)
    sol = solve_ivp(
        MRO_equations,
        [0, t_end],
        [x0, v0],
        args=(m, gamma, k),
        t_eval=t_eval,
        method="RK45",
    )
    return sol.t, sol.y[0]


layout = html.Div(
    style={"maxWidth": "1100px", "margin": "0 auto", "padding": "24px"},
    children=[
        html.H1("Analyse spectrale avancée (FFT) du MRO"),
        dcc.Markdown(
            """
Cette page calcule la transformée de Fourier de x(t) pour une configuration donnée du MRO,
et extrait automatiquement :

- La **fréquence dominante** f\*  
- Un indicateur de **facteur de qualité (Q)**  
- Le **contraste pic / bruit**, lié à la stabilité de la résonance  
"""
        ),

        html.Hr(),

        html.Div(
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "14px"},
            children=[
                html.Div([
                    html.Label("m (masse)"),
                    dcc.Slider(id="fft-m", min=0.1, max=5, step=0.1, value=1.0,
                               tooltip={"placement": "bottom"}),
                    html.Div(id="fft-m-val", style={"fontSize": "0.8rem"}),
                ]),
                html.Div([
                    html.Label("γ (amortissement)"),
                    dcc.Slider(id="fft-gamma", min=0.0, max=0.5, step=0.005, value=0.05,
                               tooltip={"placement": "bottom"}),
                    html.Div(id="fft-gamma-val", style={"fontSize": "0.8rem"}),
                ]),
                html.Div([
                    html.Label("k (tension ontogénétique)"),
                    dcc.Slider(id="fft-k", min=0.1, max=5.0, step=0.05, value=1.5,
                               tooltip={"placement": "bottom"}),
                    html.Div(id="fft-k-val", style={"fontSize": "0.8rem"}),
                ]),
                html.Div([
                    html.Label("x(0)"),
                    dcc.Slider(id="fft-x0", min=-2, max=2, step=0.05, value=1.0,
                               tooltip={"placement": "bottom"}),
                    html.Div(id="fft-x0-val", style={"fontSize": "0.8rem"}),
                ]),
                html.Div([
                    html.Label("v(0) = dx/dt(0)"),
                    dcc.Slider(id="fft-v0", min=-2, max=2, step=0.05, value=0.0,
                               tooltip={"placement": "bottom"}),
                    html.Div(id="fft-v0-val", style={"fontSize": "0.8rem"}),
                ]),
                html.Div([
                    html.Label("Durée t_end"),
                    dcc.Slider(id="fft-tend", min=5, max=80, step=1, value=30,
                               tooltip={"placement": "bottom"}),
                    html.Div(id="fft-tend-val", style={"fontSize": "0.8rem"}),
                ]),
                html.Div([
                    html.Label("Résolution FFT (N = 2^p)"),
                    dcc.Slider(id="fft-npow", min=8, max=16, step=1, value=13,
                               tooltip={"placement": "bottom"}),
                    html.Div(id="fft-npow-val", style={"fontSize": "0.8rem"}),
                ]),
            ],
        ),

        html.Hr(),

        html.Div([
            html.H3("Spectre |FFT(x)|"),
            dcc.Loading(
                dcc.Graph(
                    id="fft-graph",
                    config={"toImageButtonOptions": {"format": "svg"}},
                )
            ),
        ]),

        html.Div(
            id="fft-metrics",
            style={
                "marginTop": "16px",
                "padding": "12px",
                "border": "1px solid #eee",
                "borderRadius": "8px",
                "background": "#fafafa",
                "fontSize": "0.9rem",
            },
        ),
    ],
)

# --- Petits labels sliders ---
@callback(Output("fft-m-val", "children"), Input("fft-m", "value"))
def _lbl_m(v): return f"m = {v:.3f}"

@callback(Output("fft-gamma-val", "children"), Input("fft-gamma", "value"))
def _lbl_g(v): return f"γ = {v:.3f}"

@callback(Output("fft-k-val", "children"), Input("fft-k", "value"))
def _lbl_k(v): return f"k = {v:.3f}"

@callback(Output("fft-x0-val", "children"), Input("fft-x0", "value"))
def _lbl_x0(v): return f"x(0) = {v:.3f}"

@callback(Output("fft-v0-val", "children"), Input("fft-v0", "value"))
def _lbl_v0(v): return f"v(0) = {v:.3f}"

@callback(Output("fft-tend-val", "children"), Input("fft-tend", "value"))
def _lbl_tend(v): return f"t_end = {v:.1f}"

@callback(Output("fft-npow-val", "children"), Input("fft-npow", "value"))
def _lbl_npow(v): return f"N = 2^{int(v)} points"


# --- Callback principal FFT ---
@callback(
    Output("fft-graph", "figure"),
    Output("fft-metrics", "children"),
    Input("fft-m", "value"),
    Input("fft-gamma", "value"),
    Input("fft-k", "value"),
    Input("fft-x0", "value"),
    Input("fft-v0", "value"),
    Input("fft-tend", "value"),
    Input("fft-npow", "value"),
)
def _fft_analysis(m, gamma, k, x0, v0, t_end, npow):
    # Simule x(t)
    t, x = simulate_mro(m, gamma, k, x0, v0, t_end)

    # Taille FFT
    n = int(2 ** int(npow))
    if n < 16:
        n = 16

    # Échantillonnage uniforme
    t_uniform = np.linspace(t[0], t[-1], n)
    x_uniform = np.interp(t_uniform, t, x)
    dt = (t_uniform[-1] - t_uniform[0]) / (n - 1 + 1e-12)

    # FFT
    X = np.fft.rfft(x_uniform)
    freqs = np.fft.rfftfreq(n, d=dt)
    mag = np.abs(X)

    # Éviter le pic DC pour la recherche
    if len(mag) > 1:
        idx_peak = int(np.argmax(mag[1:])) + 1
        f_peak = float(freqs[idx_peak])
        a_peak = float(mag[idx_peak])
    else:
        f_peak, a_peak = 0.0, 0.0

    # Facteur de qualité (approx) : Q = f* / Δf (fenêtre autour du pic)
    # Approche simple : largeur où mag > a_peak/2
    if a_peak > 0:
        half = a_peak / 2.0
        above = mag >= half
        indices = np.where(above)[0]
        if len(indices) > 1:
            f_min = freqs[indices[0]]
            f_max = freqs[indices[-1]]
            bw = max(f_max - f_min, 1e-12)
            Q = float(f_peak / bw) if bw > 0 else float("inf")
        else:
            Q = float("inf")
    else:
        Q = 0.0

    # Contraste pic / "bruit" (médiane)
    if len(mag) > 4:
        bg = float(np.median(mag[2:]))
        contrast = float(a_peak / (bg + 1e-12)) if bg > 0 else float("inf")
    else:
        contrast = 0.0

    # Figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=freqs, y=mag, mode="lines", name="|FFT(x)|"))
    fig.update_layout(
        xaxis_title="Fréquence (u.a.)",
        yaxis_title="Amplitude spectrale",
        title="Spectre de x(t)",
    )
    if a_peak > 0:
        fig.add_vline(
            x=f_peak,
            line_dash="dash",
            annotation_text=f"f* ≈ {f_peak:.4f}",
            annotation_position="top",
        )

    # Texte métriques
    regime = []
    if Q > 50 and contrast > 20:
        regime.append("Résonance fortement structurée, pic stable (Q élevé).")
    elif Q > 10:
        regime.append("Résonance nette avec amortissement modéré.")
    else:
        regime.append("Spectre diffus, dissipation forte ou excitation peu sélective.")

    if gamma < 1e-3:
        regime.append("γ très faible : régime quasi-conservatif (peu réaliste biologiquement).")
    elif 1e-3 <= gamma <= 0.1:
        regime.append("γ dans une zone compatible avec une dissipation constructive.")
    else:
        regime.append("γ élevé : extinction rapide, mémoire oscillatoire courte.")

    metrics = html.Div([
        html.Strong(f"Fréquence dominante estimée f* ≈ {f_peak:.6f}"),
        html.Br(),
        html.Span(f"Facteur de qualité approximatif Q ≈ {Q:.2f}"),
        html.Br(),
        html.Span(f"Contraste pic / fond ≈ {contrast:.2f}"),
        html.Br(),
        html.Br(),
        html.Div("Interprétation :"),
        html.Ul([html.Li(m) for m in regime]),
    ])

    return fig, metrics