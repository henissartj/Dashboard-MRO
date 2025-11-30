import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.graph_objects as go
import numpy as np
from scipy.integrate import solve_ivp

dash.register_page(
    __name__,
    path="/heatmap3d",
    name="Heatmap 3D",
    order=40,
)

# --------- Modèle MRO minimal ---------
def MRO_equations(t, Y, m, gamma, k):
    x, dxdt = Y
    dxdtt = -(gamma/m)*dxdt - (k/m)*x
    return [dxdt, dxdtt]

def simulate_mro(m=1.0, gamma=0.15, k=1.0, x0=1.0, v0=0.0,
                 t_start=0.0, t_end=30.0, t_points=1500):
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

def heatmap_max_amp(gammas, ks, m=1.0, x0=1.0, v0=0.0, t_end=30.0, t_points=800):
    Z = np.zeros((len(gammas), len(ks)))
    for i, g in enumerate(gammas):
        for j, kk in enumerate(ks):
            t, x, _ = simulate_mro(m=m, gamma=g, k=kk, x0=x0, v0=v0,
                                   t_start=0.0, t_end=t_end, t_points=t_points)
            Z[i, j] = np.max(np.abs(x))
    return Z

# --------- Layout ---------
layout = html.Div(
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "24px"},
    children=[
        html.H1("Heatmap 3D – Max |x(t)| sur (γ, k)"),
        html.P("Surface 3D du maximum d’amplitude |x(t)| en balayant (γ, k). Choisis m et la grille (résolution modérée = plus rapide)."),

        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}, children=[
            html.Div(children=[
                html.Label("m (masse)"),
                dcc.Slider(
                    id="hm-m",
                    min=0.1,
                    max=5.0,
                    step=0.1,
                    value=1.0,
                    updatemode="mouseup",
                    tooltip={"placement": "bottom"},
                ),
                html.Div(id="hm-m-val"),
            ]),
            html.Div(children=[
                html.Label("Durée t_end"),
                dcc.Slider(
                    id="hm-tend",
                    min=5,
                    max=120,
                    step=1,
                    value=30,
                    updatemode="mouseup",
                    tooltip={"placement": "bottom"},
                ),
                html.Div(id="hm-tend-val"),
            ]),
        ]),

        html.Div(style={"height": "8px"}),

        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"}, children=[
            html.Div(children=[
                html.Label("γ min / γ max / pas"),
                html.Div([
                    dcc.Input(id="hm-g-min", type="number", value=0.0, step=0.01, style={"width": "30%", "marginRight": "6px"}),
                    dcc.Input(id="hm-g-max", type="number", value=0.50, step=0.01, style={"width": "30%", "marginRight": "6px"}),
                    dcc.Input(id="hm-g-step", type="number", value=0.05, step=0.01, style={"width": "30%"}),
                ]),
            ]),
            html.Div(children=[
                html.Label("k min / k max / pas"),
                html.Div([
                    dcc.Input(id="hm-k-min", type="number", value=0.5, step=0.1, style={"width": "30%", "marginRight": "6px"}),
                    dcc.Input(id="hm-k-max", type="number", value=3.0, step=0.1, style={"width": "30%", "marginRight": "6px"}),
                    dcc.Input(id="hm-k-step", type="number", value=0.25, step=0.05, style={"width": "30%"}),
                ]),
            ]),
        ]),

        html.Div(style={"marginTop": "10px"}, children=[
            html.Button("Calculer la surface 3D", id="btn-heatmap3d", n_clicks=0),
            html.Span(id="hm-warn", style={"marginLeft": "12px", "color": "#888"}),
        ]),

        html.Div(style={"height": "16px"}),

        dcc.Loading(
            dcc.Graph(id="heatmap3d-graph",
                      config={"toImageButtonOptions": {"format": "svg"}}),
            type="dot"
        ),
    ]
)

# --------- Callbacks ---------
@callback(Output("hm-m-val", "children"), Input("hm-m", "value"))
def _show_m(v): return f"m = {v:.2f}"

@callback(Output("hm-tend-val", "children"), Input("hm-tend", "value"))
def _show_tend(v): return f"t_end = {v:.0f}"

@callback(
    Output("heatmap3d-graph", "figure"),
    Output("hm-warn", "children"),
    Input("btn-heatmap3d", "n_clicks"),
    State("hm-m", "value"),
    State("hm-tend", "value"),
    State("hm-g-min", "value"),
    State("hm-g-max", "value"),
    State("hm-g-step", "value"),
    State("hm-k-min", "value"),
    State("hm-k-max", "value"),
    State("hm-k-step", "value"),
    prevent_initial_call=True
)
def _compute_surface(n, m, t_end, gmin, gmax, gstep, kmin, kmax, kstep):
    gammas = np.arange(float(gmin), float(gmax) + 1e-12, float(gstep))
    ks = np.arange(float(kmin), float(kmax) + 1e-12, float(kstep))

    cells = len(gammas) * len(ks)
    warn = f"Résolution: {len(gammas)}×{len(ks)} = {cells} simulations."
    # Sécurité soft pour VPS
    if cells > 500:
        warn += " (Attention: grille lourde, ça peut prendre du temps.)"

    Z = heatmap_max_amp(gammas, ks, m=float(m), x0=1.0, v0=0.0, t_end=float(t_end), t_points=800)

    # Surface 3D : axes = (k, gamma, Z)
    K, G = np.meshgrid(ks, gammas)
    fig = go.Figure(data=[go.Surface(x=K, y=G, z=Z, coloraxis="coloraxis", showscale=True)])
    fig.update_layout(
        title="Max |x(t)| en fonction de (γ, k) – surface 3D",
        scene=dict(
            xaxis_title="k",
            yaxis_title="γ",
            zaxis_title="max |x(t)|",
        ),
        coloraxis=dict(colorscale="Viridis"),
        margin=dict(l=0, r=0, t=50, b=0)
    )
    return fig, warn
