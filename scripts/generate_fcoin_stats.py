import os
import json
from datetime import datetime
import pymysql
import urllib.request
import ssl

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", "bot_fazer")
DB_USER = os.getenv("DB_USER", "botfazer")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

APP_DIR = "/opt/mro_dash"
SITE_DIR = os.path.join(APP_DIR, "site")
DATA_DIR = os.path.join(SITE_DIR, "data")
FCOIN_JSON = os.path.join(DATA_DIR, "fcoin.json")
FX_SYMBOLS = ["EUR", "USD", "DZD", "MAD", "TND", "GBP"]

def fetch_rows():
    conn = pymysql.connect(host=DB_HOST, db=DB_NAME, user=DB_USER, password=DB_PASSWORD, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT price, created_at FROM crypto_history WHERE created_at >= NOW() - INTERVAL 1 DAY ORDER BY created_at ASC")
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows

def compute_stats(rows):
    if not rows:
        return None, None
    prices = [float(r[0]) for r in rows]
    dates = [r[1] for r in rows]
    first = prices[0]
    last = prices[-1]
    change_24h = last - first
    change_pct = (change_24h / first * 100) if first != 0 else 0.0
    stats = {
        "current": round(last, 4),
        "min": round(min(prices), 4),
        "max": round(max(prices), 4),
        "avg": round(sum(prices) / len(prices), 4),
        "change_24h": round(change_24h, 4),
        "change_24h_pct": round(change_pct, 2),
        "points": len(prices),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    series = [{"t": d.isoformat(), "v": round(float(p), 6)} for p, d in zip(prices, dates)]
    return stats, series

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def write_json(stats, series, fx):
    payload = {"stats": stats, "series": series, "fx": fx, "base_currency": "EUR"}
    with open(FCOIN_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

def fetch_fx():
    url = "https://api.exchangerate.host/latest?base=EUR&symbols=" + ",".join(FX_SYMBOLS)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rates = data.get("rates", {})
    except Exception:
        rates = {}
    if "EUR" not in rates:
        rates["EUR"] = 1.0
    defaults = {"USD": 1.08, "DZD": 145.0, "MAD": 10.8, "TND": 3.35, "GBP": 0.85}
    for k, v in defaults.items():
        rates[k] = rates.get(k, v)
    return rates

def main():
    ensure_dirs()
    rows = fetch_rows()
    stats, series = compute_stats(rows)
    if not stats:
        stats = {"current": 0, "min": 0, "max": 0, "avg": 0, "change_24h": 0, "change_24h_pct": 0, "points": 0, "updated_at": datetime.utcnow().isoformat() + "Z"}
        series = [{"t": datetime.utcnow().isoformat() + "Z", "v": 0}]
    fx = fetch_fx()
    write_json(stats, series, fx)

if __name__ == "__main__":
    main()
