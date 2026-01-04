import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import pymysql
import os
import plotly.express as px
import plotly.graph_objects as go
import random
import datetime

dash.register_page(
    __name__,
    path="/casino",
    title="Casino Dashboard • Éphévérisme",
    name="Casino"
)

# Configuration DB
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "botfazer")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "bot_fazer")

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def get_data():
    try:
        conn = get_connection()
        
        # 1. Global Stats
        with conn.cursor() as cursor:
            # Total Supply (Balance + Bank)
            cursor.execute("SELECT SUM(balance) as total_balance, SUM(bank) as total_bank, COUNT(*) as user_count FROM users")
            stats = cursor.fetchone()
            
            # Transactions last 24h
            cursor.execute("""
                SELECT COUNT(*) as tx_count, SUM(amount) as tx_volume 
                FROM transactions 
                WHERE created_at >= NOW() - INTERVAL 24 HOUR
            """)
            tx_stats = cursor.fetchone()
            
            # 2. Leaderboard
            cursor.execute("""
                SELECT user_id, balance, bank, (balance + bank) as total 
                FROM users 
                ORDER BY total DESC 
                LIMIT 20
            """)
            leaderboard = cursor.fetchall()
            
            # 3. Transaction History (Last 100)
            cursor.execute("""
                SELECT id, type, requester_id, amount, account, status, created_at 
                FROM transactions 
                ORDER BY created_at DESC 
                LIMIT 100
            """)
            history = cursor.fetchall()

            # 4. Daily Volume (Last 30 days) for Graph
            cursor.execute("""
                SELECT DATE(created_at) as date, SUM(amount) as volume, COUNT(*) as count
                FROM transactions
                WHERE created_at >= NOW() - INTERVAL 30 DAY
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            """)
            daily_volume = cursor.fetchall()

        conn.close()
        
        return {
            "stats": stats,
            "tx_stats": tx_stats,
            "leaderboard": pd.DataFrame(leaderboard),
            "history": pd.DataFrame(history),
            "daily_volume": pd.DataFrame(daily_volume)
        }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

# --- Layout ---

def layout():
    data = get_data()
    
    # Custom Coin Icon
    coin_icon = html.Img(src="/assets/images/fcoin.png", style={"height": "1.2em", "verticalAlign": "middle", "marginLeft": "5px"})
    
    # Header with 3D Coin
    header = dbc.Row([
        dbc.Col([
            html.H1("Économie Fcoins", className="display-5 fw-bold"),
            html.P("Statistiques en temps réel de l'économie Fcoins.", className="text-muted"),
        ], width=8),
        dbc.Col([
            html.Img(src="/assets/images/fcoin_3d.png", className="img-fluid", style={"maxHeight": "120px", "float": "right"})
        ], width=4)
    ], className="mb-5 align-items-center")

    # Cards Container for Real-time Updates
    cards_container = html.Div(id="live-stats-container")

    # --- Live Crypto Graph Section ---
    crypto_section = html.Div([
        html.H3("Marché Fcoin", className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Prix Actuel", className="text-muted"),
                        html.H2(id="live-price-display", className="fw-bold text-success"),
                        html.Div(id="live-price-conversions", className="text-muted small mt-2")
                    ])
                ], className="h-100 shadow-sm")
            ], width=12, lg=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(id="live-crypto-graph", config={"displayModeBar": False}, style={"height": "300px"})
                    ])
                ], className="shadow-sm")
            ], width=12, lg=9)
        ]),
        dcc.Interval(id="price-interval", interval=2000, n_intervals=0), # 2 seconds
        dcc.Interval(id="stats-interval", interval=5000, n_intervals=0), # 5 seconds for stats
        dcc.Store(id="price-store", data={"history": [], "current": 1.25}) # Initial price $1.25
    ], className="mb-5")

    # Volume Graph (Static History) - Initially Hidden if no data
    if not data or data["daily_volume"].empty:
        vol_graph = html.Div()
    else:
        fig = px.bar(data["daily_volume"], x='date', y='volume', title="Volume des transactions (30 jours)",
                     labels={'volume': 'Montant (Fcoins)', 'date': 'Date'})
        fig.update_layout(template="plotly_white")
        vol_graph = dcc.Graph(figure=fig, className="mb-5 shadow-sm border rounded")

    # Leaderboard Table - Initial Load
    if not data:
        lb_table = html.Div("Chargement...")
        hist_table = html.Div("Chargement...")
    else:
        lb_table = dash_table.DataTable(
            data=data["leaderboard"].to_dict('records'),
            columns=[
                {'name': 'User ID', 'id': 'user_id'},
                {'name': 'Solde', 'id': 'balance', 'type': 'numeric', 'format': {'specifier': ','}},
                {'name': 'Banque', 'id': 'bank', 'type': 'numeric', 'format': {'specifier': ','}},
                {'name': 'Total', 'id': 'total', 'type': 'numeric', 'format': {'specifier': ','}},
            ],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            page_size=10
        )
        hist_table = dash_table.DataTable(
            data=data["history"].to_dict('records'),
            columns=[
                {'name': 'Type', 'id': 'type'},
                {'name': 'Montant', 'id': 'amount'},
                {'name': 'Status', 'id': 'status'},
                {'name': 'Date', 'id': 'created_at'},
            ],
            page_size=10,
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '0.9em'},
        )

    # Layout
    return html.Div([
        header,
        cards_container,
        crypto_section,
        html.H3("Évolution du Volume (Historique)", className="mb-3"),
        vol_graph,
        
        dbc.Row([
            dbc.Col([
                html.H3("Classement (Top 20)", className="mb-3"),
                html.Div(lb_table, className="shadow-sm border rounded p-3 bg-white")
            ], width=12, lg=6),
            
            dbc.Col([
                html.H3("Dernières Transactions", className="mb-3"),
                html.Div(hist_table, className="shadow-sm border rounded p-3 bg-white")
            ], width=12, lg=6)
        ])
        
    ], className="container-fluid py-4")


# --- Callbacks ---

@callback(
    Output("live-stats-container", "children"),
    Input("stats-interval", "n_intervals")
)
def update_stats(n):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Total Supply
            cursor.execute("SELECT SUM(balance) as total_balance, SUM(bank) as total_bank, COUNT(*) as user_count FROM users")
            stats = cursor.fetchone()
            # Transactions last 24h
            cursor.execute("""
                SELECT COUNT(*) as tx_count, SUM(amount) as tx_volume 
                FROM transactions 
                WHERE created_at >= NOW() - INTERVAL 24 HOUR
            """)
            tx_stats = cursor.fetchone()
    except Exception:
        return html.Div("Erreur DB", className="text-danger")
    finally:
        conn.close()

    if not stats: return html.Div()

    def fmt(n):
        if n is None: return "0"
        return f"{int(n):,}".replace(",", " ")

    total_supply = (stats['total_balance'] or 0) + (stats['total_bank'] or 0)
    coin_icon = html.Img(src="/assets/images/fcoin.png", style={"height": "1.2em", "verticalAlign": "middle", "marginLeft": "5px"})

    return dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Masse Monétaire", className="card-title text-primary"),
                html.H2([f"{fmt(total_supply)}", coin_icon], className="card-text"),
                html.Small(f"En circulation (Comptes: {stats['user_count']})")
            ])
        ], className="mb-4 shadow-sm"), width=12, md=4),
        
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Volume 24h", className="card-title text-success"),
                html.H2([f"{fmt(tx_stats['tx_volume'])}", coin_icon], className="card-text"),
                html.Small(f"{tx_stats['tx_count']} transactions")
            ])
        ], className="mb-4 shadow-sm"), width=12, md=4),
        
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Banque Totale", className="card-title text-info"),
                html.H2([f"{fmt(stats['total_bank'])}", coin_icon], className="card-text"),
                html.Small("Stocké en banque")
            ])
        ], className="mb-4 shadow-sm"), width=12, md=4),
    ])

@callback(
    [Output("price-store", "data"),
     Output("live-price-display", "children"),
     Output("live-price-conversions", "children"),
     Output("live-crypto-graph", "figure")],
    Input("price-interval", "n_intervals"),
    State("price-store", "data")
)
def update_crypto_graph(n, data):
    # Fetch recent prices from DB
    history = []
    current_price = 1.25
    recent_credits = 0
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check for credits in the last 60 seconds (for status display)
            cursor.execute("""
                SELECT SUM(amount) as total
                FROM transactions 
                WHERE type = 'credit' 
                AND created_at >= NOW() - INTERVAL 1 MINUTE
            """)
            result = cursor.fetchone()
            recent_credits = result['total'] or 0

            # Fetch last 50 points from crypto_history
            cursor.execute("""
                SELECT price, DATE_FORMAT(created_at, '%H:%i:%s') as t 
                FROM crypto_history 
                ORDER BY created_at DESC 
                LIMIT 50
            """)
            rows = cursor.fetchall()
            # Rows are DESC, we need ASC for graph
            rows.reverse()
            history = [{"t": r['t'], "p": float(r['price'])} for r in rows]
            
            if history:
                current_price = history[-1]['p']
    except Exception:
        pass
    finally:
        conn.close()

    # Status logic
    status_text = ""
    status_color = "text-success"
    if recent_credits > 5000:
        status_text = "⚠️ INFLATION"
        status_color = "text-warning"
        if recent_credits > 50000:
            status_text = "📉 CRASH IMMINENT"
            status_color = "text-danger"

    # Conversions
    usd = current_price
    eur = usd * 0.92
    dzd = usd * 134.5
    
    price_display = [
        html.Span(f"${usd:.2f} ", className=status_color),
        html.Span(status_text, className="badge bg-dark ms-2 small", style={"fontSize": "0.5em"}) if status_text else None
    ]
    
    conv_display = [
        html.Div(f"€{eur:.2f} EUR"),
        html.Div(f"{dzd:.2f} DZD")
    ]
    
    # Build Graph
    times = [h["t"] for h in history]
    prices = [h["p"] for h in history]
    
    fig = go.Figure()
    
    line_color = '#00cc96'
    if recent_credits > 50000:
        line_color = '#EF553B' # Red for crash

    # Gradient filled area chart
    fig.add_trace(go.Scatter(
        x=times, 
        y=prices,
        mode='lines',
        fill='tozeroy',
        line=dict(color=line_color, width=2),
        name='Fcoin'
    ))
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(gridcolor='#f0f0f0'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified"
    )
    
    return {}, price_display, conv_display, fig
