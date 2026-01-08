import os
import asyncio
from datetime import datetime, timedelta
from flask import Flask, Response, render_template_string, jsonify
import aiomysql
import plotly.graph_objs as go

app = Flask(__name__)

_pool = None

async def get_pool():
    global _pool
    if _pool:
        return _pool
    host = os.getenv("DB_HOST", "127.0.0.1")
    db = os.getenv("DB_NAME", "bot_fazer")
    user = os.getenv("DB_USER", "botfazer")
    pwd = os.getenv("DB_PASSWORD", "")
    _pool = await aiomysql.create_pool(host=host, db=db, user=user, password=pwd, autocommit=True, minsize=1, maxsize=5)
    return _pool

HOME_HTML = """
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Bot de Fazer</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif; margin: 0; color: #e7e9ea; background: #0f1115; }
      header { background: #1a1f29; padding: 24px; border-bottom: 1px solid #2a2f3a; }
      .container { max-width: 920px; margin: 0 auto; padding: 24px; }
      a.button { display: inline-block; background: #3b82f6; color: white; padding: 12px 16px; border-radius: 8px; text-decoration: none; font-weight: 600; }
      a.button:hover { background: #2563eb; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
      .card { background: #151922; border: 1px solid #2a2f3a; border-radius: 10px; padding: 16px; }
      h1 { margin: 0 0 8px; font-size: 28px; }
      h2 { margin-top: 0; font-size: 20px; }
      ul { margin: 0; padding-left: 20px; }
      footer { border-top: 1px solid #2a2f3a; margin-top: 32px; padding-top: 16px; color: #9aa0a6; }
      .tag { display:inline-block; padding: 4px 8px; border-radius: 999px; background:#223; border:1px solid #334; color:#9aa0a6; font-size:12px; margin-right:8px; }
    </style>
  </head>
  <body>
    <header>
      <div class="container">
        <h1>Bot de Fazer</h1>
        <p>Économie, jeux et fun pour votre serveur Discord.</p>
        <a class="button" href="https://discord.com/oauth2/authorize?client_id=1448011692867977266&permissions=8&integration_type=0&scope=bot" target="_blank" rel="noopener">Inviter le bot</a>
        <span class="tag">HTTPS prêt via proxy</span>
        <span class="tag">Fcoin en direct</span>
      </div>
    </header>
    <main class="container">
      <div class="grid">
        <div class="card">
          <h2>Commandes populaires</h2>
          <ul>
            <li>+balance — Voir votre solde</li>
            <li>+send @user montant — Envoyer de l'argent</li>
            <li>+facture @user montant [motif] — Créer une facture</li>
            <li>+payfacture id — Payer une facture reçue</li>
            <li>+work — Travailler légalement</li>
            <li>+immo — Immobilier (acheter/vendre)</li>
            <li>+luxury — Boutique de luxe</li>
            <li>+fcoin — Cours du Fcoin</li>
            <li>+course / +bet — Courses de chevaux</li>
          </ul>
        </div>
        <div class="card">
          <h2>Dernières mises à jour</h2>
          <ul>
            <li>Suppression complète de l'ancien site epheverisme.art</li>
            <li>Factures: paiement met l'embed en vert et ajoute bouton Ticket</li>
            <li>Pas de cap à 1M hors jeux (factures, virements, banques)</li>
            <li>Stabilité: édition de messages via followup sur interactions</li>
          </ul>
        </div>
      </div>
      <div class="card" style="margin-top:24px">
        <h2>Fcoin en direct</h2>
        <p>Consultez le graphique et les stats: <a href="/fcoin">/fcoin</a></p>
      </div>
      <footer>
        Domaine: botdefazer.duckdns.org — Configurez le proxy HTTPS (voir instructions).
      </footer>
    </main>
  </body>
</html>
"""

@app.get("/")
async def home():
    return Response(HOME_HTML, mimetype="text/html")

@app.get("/fcoin")
async def fcoin():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT price, created_at FROM crypto_history ORDER BY created_at DESC LIMIT 200")
                rows = await cur.fetchall()
        if not rows:
            return jsonify({"error": "Pas de données Fcoin"}), 503
        rows = list(reversed(rows))
        prices = [float(r[0]) for r in rows]
        dates = [r[1] for r in rows]
        last = prices[-1]
        first_24h = prices[0]
        change_24h = last - first_24h
        change_pct = (change_24h / first_24h * 100) if first_24h != 0 else 0.0
        stats = {
            "current": round(last, 4),
            "min": round(min(prices), 4),
            "max": round(max(prices), 4),
            "avg": round(sum(prices)/len(prices), 4),
            "change_24h": round(change_24h, 4),
            "change_24h_pct": round(change_pct, 2),
            "points": len(prices),
        }
        fig = go.Figure(data=go.Scatter(x=dates, y=prices, mode='lines', line=dict(color='#22c55e', width=2)))
        fig.update_layout(
            title="Cours du Fcoin (24h)",
            paper_bgcolor="#0f1115", plot_bgcolor="#0f1115",
            font=dict(color="#e7e9ea"),
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(gridcolor="#222", showgrid=False),
            yaxis=dict(gridcolor="#222", showgrid=True)
        )
        html_chart = fig.to_html(include_plotlyjs="cdn", full_html=False)
        PAGE = f"""
        <!doctype html>
        <html lang="fr">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Fcoin — Bot de Fazer</title>
            <style>
              body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, sans-serif; margin:0; background:#0f1115; color:#e7e9ea; }}
              .container {{ max-width: 920px; margin: 0 auto; padding: 24px; }}
              .card {{ background:#151922; border:1px solid #2a2f3a; border-radius:10px; padding:16px; }}
              .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
              .stat {{ font-size: 14px; color:#9aa0a6; }}
              .green {{ color:#22c55e; }}
              .red {{ color:#ef4444; }}
              a {{ color:#60a5fa; }}
            </style>
          </head>
          <body>
            <main class="container">
              <h1>Fcoin — Cours et Statistiques</h1>
              <div class="card">
                {html_chart}
              </div>
              <div class="grid" style="margin-top:16px">
                <div class="card">
                  <h2>Statistiques</h2>
                  <p class="stat">Prix actuel: <b class="{('green' if stats['change_24h']>=0 else 'red')}">{stats['current']}</b></p>
                  <p class="stat">Min/Max: {stats['min']} — {stats['max']}</p>
                  <p class="stat">Moyenne: {stats['avg']}</p>
                  <p class="stat">Variation 24h: {stats['change_24h']} ({stats['change_24h_pct']}%)</p>
                  <p class="stat">Points: {stats['points']}</p>
                </div>
                <div class="card">
                  <h2>Liens</h2>
                  <p><a href="/">Accueil</a> · <a href="https://discord.com/oauth2/authorize?client_id=1448011692867977266&permissions=8&integration_type=0&scope=bot" target="_blank" rel="noopener">Inviter le bot</a></p>
                </div>
              </div>
            </main>
          </body>
        </html>
        """
        return Response(PAGE, mimetype="text/html")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    # Flask 3 support async views; run via builtin for preview. Use gunicorn in prod.
    app.run(host="0.0.0.0", port=port, debug=True)

