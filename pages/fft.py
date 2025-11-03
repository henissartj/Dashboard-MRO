import dash
from dash import dcc, html

dash.register_page(__name__, path="/fft")

layout = html.Div([
    html.H2("Analyse fréquentielle (FFT)"),
    html.P("Spectre de |FFT(x)| en fonction de la fréquence (Hz arbitraires)"),
    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"}, children=[
        html.Div([
            html.Label("Fenêtre temporelle (t_end)"),
            dcc.Slider(id="fft-tend", min=5, max=120, step=1, value=30),
            html.Div(id="fft-tend-val"),
        ]),
        html.Div([
            html.Label("Zéro-padding (puissance de 2)"),
            dcc.Slider(id="fft-npow", min=8, max=16, step=1, value=12,
                       marks=None, tooltip={"placement": "bottom"}),
            html.Div(id="fft-npow-val"),
        ]),
    ]),
    html.Hr(),
    dcc.Loading(dcc.Graph(id="fft-graph", config={"toImageButtonOptions": {"format": "svg"}}))
])

