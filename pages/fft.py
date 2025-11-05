import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.graph_objects as go
import numpy as np
from scipy.integrate import solve_ivp

dash.register_page(
    __name__,
    path="/fft",
    name="FFT avancée",
    order=30,
)

# --------- Modèle MRO minimal ---------
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

# --------- Helpers FFT ---------
def window_hann(n):
    return 0.5 - 0.5 * np.cos(2*np.pi*np.arange(n)/n)

def find_peaks_simple(y, min_prominence=0.0, max_peaks=8):
    idx = np.argsort(y)[::-1]
    idx = idx[idx > 0]  # remove DC
    if min_prominence > 0:
        idx = [i for i in idx if y[i] >= min_prominence]
    if len(idx) > max_peaks:
        idx = idx[:max_peaks]
    return np.array(idx, dtype=int)

def spectral_metrics(freqs, mag, peak_idx):
    f0 = freqs[peak_idx] if peak_idx is not None else 0.0
    a0 = mag[peak_idx] if peak_idx is not None else 0.0

    if peak_idx is not None and a0 > 0:
        half = a0 / np.sqrt(2)
        i_left = peak_idx
        while i_left > 1 and mag[i_left] > half:
            i_left -= 1
        i_right = peak_idx
        while i_right < len(mag)-1 and mag[i_right] > half:
            i_right += 1
        f_left = freqs[max(i_left, 0)]
        f_right = freqs[min(i_right, len(freqs)-1)]
        bw = max(f_right - f_left, 0.0)
    else:
        f_left = f_right = bw = 0.0

    centroid = (freqs * mag).sum() / mag.sum() if mag.sum() > 0 else 0.0
    return f0, a0, f_left, f_right, bw, centroid

def compute_thd(freqs, mag, f0, nharm=5, tol=0.03):
    if f0 <= 0:
        return 0.0, []
    a0 = mag[np.argmin(np.abs(freqs - f0))]
    harmonics = []
    thd_sum = 0.0
    for n in range(2, nharm+1):
        target = n * f0
        idx = np.argmin(np.abs(freqs - target))
        f_found = freqs[idx]
        if abs(f_found - target) / target <= tol:
            an = mag[idx]
            harmonics.append((n, f_found, an))
            thd_sum += an**2
    thd = np.sqrt(thd_sum) / a0 if a0 > 0 else 0.0
    return thd, harmonics

# --------- Layout ---------
layout = html.Div(
    style={"maxWidth": "1200px", "margin": "0 auto", "padding": "24px"},
    children=[
        html.H1("Analyse FFT avancée"),
        html.P("Fondamental, harmoniques, THD, SNR, bande passante −3 dB, centroid spectral. "
               "Fenêtre de Hann, rééchantillonnage régulier, zero-padding."),
        html.Div(style={"display": "grid", "gridTemplateColumns": "repeat(3,1fr)", "gap": "12px"}, children=[
            html.Div([
                html.Label("m"),
                dcc.Input(id="fft-m", type="number", value=1.0, step=0.1, style={"width": "100%"}),
                html.Label("γ"),
                dcc.Input(id="fft-gamma", type="number", value=0.15, step=0.01, style={"width": "100%"}),
                html.Label("k"),
                dcc.Input(id="fft-k", type="number", value=1.0, step=0.05, style={"width": "100%"}),
            ]),
            html.Div([
                html.Label("x(0)"),
                dcc.Input(id="fft-x0", type="number", value=1.0, step=0.05, style={"width": "100%"}),
                html.Label("v(0)"),
                dcc.Input(id="fft-v0", type="number", value=0.0, step=0.05, style={"width": "100%"}),
                html.Label("t_end"),
                dcc.Input(id="fft-tend", type="number", value=30, step=1, style={"width": "100%"}),
            ]),
            html.Div([
                html.Label("Taille FFT : N = 2^p"),
                dcc.Slider(id="fft-pow", min=9, max=16, step=1, value=13,
                           tooltip={"placement": "bottom"}),
                html.Div(id="fft-pow-val", style={"marginTop": "6px"}),
                html.Label("NHarm (THD)"),
                dcc.Slider(id="fft-nharm", min=3, max=10, step=1, value=5,
                           tooltip={"placement": "bottom"}),
                html.Div(id="fft-nharm-val", style={"marginTop": "6px"}),
            ]),
        ]),

        html.Div(style={"marginTop": "10px"}, children=[
            html.Button("Calculer FFT avancée", id="btn-fft-adv", n_clicks=0),
            html.Span(id="fft-warn", style={"marginLeft": "12px", "color": "#888"}),
        ]),

        html.Hr(),

        dcc.Loading(dcc.Graph(id="fft-adv-graph",
                              config={"toImageButtonOptions": {"format": "svg"}})),

        html.H3("Indicateurs spectraux"),
        html.Div(id="fft-metrics"),
    ]
)

# --------- Callbacks ---------
@callback(Output("fft-pow-val", "children"), Input("fft-pow", "value"))
def _pow_lbl(p): return f"N = 2^{p} = {2**int(p)}"

@callback(Output("fft-nharm-val", "children"), Input("fft-nharm", "value"))
def _nharm_lbl(v): return f"Nombre d'harmoniques inclus dans THD : {int(v)}"

@callback(
    Output("fft-adv-graph", "figure"),
    Output("fft-metrics", "children"),
    Output("fft-warn", "children"),
    Input("btn-fft-adv", "n_clicks"),
    State("fft-m", "value"),
    State("fft-gamma", "value"),
    State("fft-k", "value"),
    State("fft-x0", "value"),
    State("fft-v0", "value"),
    State("fft-tend", "value"),
    State("fft-pow", "value"),
    State("fft-nharm", "value"),
    prevent_initial_call=True
)
def _fft_advanced(n, m, gamma, k, x0, v0, tend, p, nharm):
    # Simulation
    t, x, v = simulate_mro(m=float(m), gamma=float(gamma), k=float(k),
                           x0=float(x0), v0=float(v0), t_end=float(tend))

    # N = 2^p (zero-padding si N > len)
    N = int(2**int(p))
    t_uniform = np.linspace(t[0], t[-1], N)
    x_uniform = np.interp(t_uniform, t, x)

    # Fenêtre Hann
    w = window_hann(N)
    xw = x_uniform * w

    # FFT
    dt_s = (t_uniform[-1] - t_uniform[0]) / (N - 1 + 1e-12)
    X = np.fft.rfft(xw)
    freqs = np.fft.rfftfreq(N, d=dt_s)
    mag = np.abs(X)

    # Pic fondamental (hors DC)
    if len(mag) > 1:
        idx_sorted = np.argsort(mag)[::-1]
        idx_sorted = [i for i in idx_sorted if i > 0]
        peak_idx = idx_sorted[0] if idx_sorted else None
    else:
        peak_idx = None

    f0, a0, f_left, f_right, bw, centroid = spectral_metrics(freqs, mag, peak_idx)

    # THD
    thd, harmonics = compute_thd(freqs, mag, f0=f0, nharm=int(nharm))

    # SNR simple
    if peak_idx is not None:
        noise = np.mean(np.delete(mag, peak_idx))
        snr = (a0 / (noise + 1e-12)) if noise > 0 else float("inf")
    else:
        snr = 0.0

    # Graph
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=freqs, y=mag, mode="lines", name="|FFT(x)|"))
    if peak_idx is not None:
        fig.add_vline(x=f0, line_dash="dash",
                      annotation_text=f"f0 ≈ {f0:.3g}", annotation_position="top")
    peaks = find_peaks_simple(mag, max_peaks=5)
    for i, pidx in enumerate(peaks):
        fpi, api = freqs[pidx], mag[pidx]
        fig.add_annotation(x=fpi, y=api, text=f"p{i+1}", showarrow=True, arrowhead=2)

    fig.update_layout(
        title="Spectre |FFT(x)| (fenêtre Hann, rééchantillonnage régulier, zero-padding)",
        xaxis_title="Fréquence (a.u.)",
        yaxis_title="Amplitude spectrale",
        margin=dict(l=0, r=0, t=50, b=0)
    )

    harm_txt = ", ".join([f"{n}f0 @ {ff:.3g}" for (n, ff, an) in harmonics]) if harmonics else "—"
    warn = f"Δt = {dt_s:.3g}s ; N = {N} ; f0≈{f0:.4g} ; THD sur {int(nharm)} harm."

    metrics = html.Ul([
        html.Li(f"Fondamental f0 ≈ {f0:.6g} (amplitude {a0:.6g})"),
        html.Li(f"Bande passante −3 dB: [{f_left:.6g}, {f_right:.6g}] → BW ≈ {bw:.6g}"),
        html.Li(f"Centroid spectral ≈ {centroid:.6g}"),
        html.Li(f"THD ≈ {thd:.6g} (harmoniques: {harm_txt})"),
        html.Li(f"SNR ≈ {snr:.6g} (estimateur simple)"),
    ])

    return fig, metrics, warn