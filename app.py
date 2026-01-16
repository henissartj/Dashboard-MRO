import ast
import os
import requests
import pymysql
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
from urllib.parse import urlencode
from flask import Flask, jsonify, send_from_directory, request, session, redirect, url_for, render_template
from bot.cogs.economy import PROPERTIES_BASE, LUXURY_ITEMS_BASE

load_dotenv()

app = Flask(__name__, static_folder="site/assets", static_url_path="/assets")
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Discord OAuth2 Configuration
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://fazer.city/callback")
DISCORD_API_BASE_URL = "https://discord.com/api"
DISCORD_AUTHORIZATION_BASE_URL = f"{DISCORD_API_BASE_URL}/oauth2/authorize"
DISCORD_TOKEN_URL = f"{DISCORD_API_BASE_URL}/oauth2/token"

if "http://" in DISCORD_REDIRECT_URI:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

def token_updater(token):
    session["oauth2_token"] = token

def make_discord_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=DISCORD_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=DISCORD_REDIRECT_URI,
        auto_refresh_kwargs={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
        },
        auto_refresh_url=DISCORD_TOKEN_URL,
        token_updater=token_updater,
    )

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def home():
    # Serve index.html if exists, else fallback
    index_path = os.path.join(os.path.dirname(__file__), "site", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Index not found", 404


@app.route("/me")
def me():
    # Serve me.html for Fazer's personal landing page
    me_path = os.path.join(os.path.dirname(__file__), "site", "me.html")
    if os.path.exists(me_path):
        with open(me_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found", 404


@app.before_request
def log_request_info():
    app.logger.debug(f"Headers: {request.headers}")
    app.logger.debug(f"Body: {request.get_data()}")

@app.route("/test-legal")
def test_legal():
    return "Ceci est une page de test pour vérifier le serveur.", 200

@app.route("/legal")
@app.route("/mentions-legales")
def legal():
    path = os.path.join(os.path.dirname(__file__), "site", "legal.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found", 404

@app.route("/terms")
@app.route("/cgu")
def terms():
    path = os.path.join(os.path.dirname(__file__), "site", "terms.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found", 404

@app.route("/privacy")
@app.route("/confidentialite")
def privacy():
    path = os.path.join(os.path.dirname(__file__), "site", "privacy.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found", 404


@app.route("/maj")
def maj():
    path = os.path.join(os.path.dirname(__file__), "site", "maj", "index.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    path2 = os.path.join(os.path.dirname(__file__), "site", "maj.html")
    if os.path.exists(path2):
        with open(path2, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found", 404


@app.route("/login")
@app.route("/api/login")
def login():
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        return "Discord OAuth2 non configuré.", 500
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "prompt": "consent",
    }
    url = f"{DISCORD_AUTHORIZATION_BASE_URL}?{urlencode(params)}"
    return redirect(url)


@app.route("/callback")
@app.route("/api/callback")
def callback():
    if request.values.get("error"):
        return request.values["error"]
    try:
        code = request.args.get("code")
        if not code:
            return redirect(url_for("login"))
        data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
            "scope": "identify",
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        resp = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers)
        if resp.status_code != 200:
            return (
                f"Erreur Discord (token) [{resp.status_code}]: {resp.text}",
                500,
            )
        token = resp.json()
        session["oauth2_token"] = token
        access_token = token.get("access_token")
        if not access_token:
            return "Erreur lors de la connexion à Discord.", 500
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        user_info_resp = requests.get(
            f"{DISCORD_API_BASE_URL}/users/@me", headers=headers
        )
        if user_info_resp.status_code != 200:
            return (
                f"Erreur Discord (user) [{user_info_resp.status_code}]: {user_info_resp.text}",
                500,
            )
        user_info = user_info_resp.json()
        session["user"] = user_info
        return redirect(url_for("profile"))
    except Exception as e:
        print(f"OAuth Error: {e}")
        return "Erreur lors de la connexion à Discord.", 500


@app.route("/logout")
@app.route("/api/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/profile")
@app.route("/api/profile")
def profile():
    user_info = session.get("user")
    if not user_info:
        return redirect(url_for("login"))
    user_id = user_info.get("id")
    if not user_id:
        return redirect(url_for("login"))
    return redirect(f"/api/user/{user_id}")


@app.route("/images/<path:filename>")
def serve_images(filename):
    images_path = os.path.join(os.path.dirname(__file__), "site", "images")
    return send_from_directory(images_path, filename)


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if not base:
            return None
        return f"{base}.{node.attr}"
    return None


def _literal(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List | ast.Tuple):
        return [_literal(elt) for elt in node.elts]
    return None


def _extract_decorator_keywords(call: ast.Call) -> dict[str, object]:
    out: dict[str, object] = {}
    for kw in call.keywords:
        if not kw.arg:
            continue
        out[kw.arg] = _literal(kw.value)
    return out


def _command_kind_from_decorator_name(dname: str) -> str | None:
    if dname.endswith(".command") or dname == "command":
        if dname.startswith("app_commands.") or dname.endswith(
            "app_commands.command"
        ):
            return "slash"
        if dname.endswith("tree.command") or dname == "tree.command":
            return "slash"
        return "prefix"
    if dname.endswith(".group") or dname == "group":
        return "prefix"
    return None


def _extract_commands_from_file(file_path: str, repo_root: str) -> list[dict]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception:
        return []

    rel = os.path.relpath(file_path, repo_root)
    commands: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        doc = ast.get_docstring(node) or ""
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            dname = _dotted_name(deco.func)
            if not dname:
                continue
            kind = _command_kind_from_decorator_name(dname)
            if not kind:
                continue
            kws = _extract_decorator_keywords(deco)
            name = kws.get("name")
            if not isinstance(name, str) or not name.strip():
                name = node.name
            aliases = kws.get("aliases") or []
            if not isinstance(aliases, list):
                aliases = []
            aliases = [a for a in aliases if isinstance(a, str) and a.strip()]
            usage = kws.get("usage")
            if usage and not isinstance(usage, str):
                usage = None
            
            if name == "work":
                print(f"DEBUG: Found work command. kws: {kws}")
            
            description = kws.get("help")
            if not isinstance(description, str) or not description.strip():
                description = (
                    doc.strip().splitlines()[0]
                    if doc.strip()
                    else ""
                )
            
            # Determine category
            category = "Autre"
            if "cogs" in rel:
                category = os.path.splitext(os.path.basename(rel))[0].capitalize()
            elif "bot_de_fazer" in rel:
                category = "Général"

            commands.append(
                {
                    "name": name,
                    "type": kind,
                    "category": category,
                    "aliases": aliases,
                    "description": description,
                    "usage": usage,
                    "source": rel,
                    "line": getattr(node, "lineno", None),
                }
            )
            break
    return commands


@app.route("/api/commands")
def api_commands():
    repo_root = os.path.dirname(__file__)
    bot_root = os.path.join(repo_root, "bot")
    all_cmds: list[dict] = []
    for root, _dirs, files in os.walk(bot_root):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            if fn.startswith("."):
                continue
            file_path = os.path.join(root, fn)
            all_cmds.extend(_extract_commands_from_file(file_path, repo_root))

    def sort_key(c: dict):
        t = c.get("type", "")
        n = c.get("name", "")
        return (t, n)

    all_cmds.sort(key=sort_key)
    return jsonify({"count": len(all_cmds), "commands": all_cmds})


@app.route("/api/stats")
def api_stats():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "botfazer"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "bot_fazer"),
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM users")
                users = cur.fetchone()["count"]
                
                cur.execute("SELECT SUM(balance + bank) as total FROM users")
                row = cur.fetchone()
                money = int(row["total"]) if row and row["total"] else 0
                
        return jsonify({
            "users": users,
            "money": money,
            "servers": 2
        })
    except Exception as e:
        print(f"Stats Error: {e}")
        # Return dummy data on error to avoid breaking UI
        return jsonify({"users": 0, "money": 0, "servers": 2})


@app.route("/api/leaderboard")
def api_leaderboard():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "botfazer"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "bot_fazer"),
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn:
            with conn.cursor() as cur:
                # Top 5 Richest (balance + all banks)
                cur.execute("""
                    SELECT 
                        user_id, 
                        (balance + bank) as total,
                        'Citoyen' as role
                    FROM users 
                    ORDER BY total DESC 
                    LIMIT 3
                """)
                rows = cur.fetchall()
                
                # Mock names for privacy/demo if real names aren't in DB (assuming user ID based)
                # In a real scenario, you'd fetch Discord usernames via bot API
                leaderboard = []
                for row in rows:
                    leaderboard.append({
                        "id": str(row["user_id"]),
                        "balance": row["total"],
                        "name": f"User {str(row['user_id'])[-4:]}", # Masked name
                        "avatar": "https://cdn.discordapp.com/embed/avatars/0.png"
                    })
                    
        return jsonify(leaderboard)
    except Exception as e:
        print(f"Leaderboard Error: {e}")
        return jsonify([])


@app.route("/api/user/<user_id>")
@app.route("/u/<user_id>")
@app.route("/user/<user_id>")
def public_profile(user_id):
    # Fetch user data from DB
    user_data = get_user_data(user_id)
    
    # Determine if this is the logged-in user viewing their own profile
    is_owner = False
    logged_in_user = session.get("user")
    
    discord_user = None
    if logged_in_user and logged_in_user["id"] == str(user_id):
        is_owner = True
        discord_user = logged_in_user
    else:
        # Try to fetch from Discord API
        discord_user = get_discord_user_info(user_id)
    
    if discord_user:
        user_data["name"] = discord_user.get("global_name") or discord_user.get("username")
        avatar = discord_user.get("avatar")
        if avatar:
            ext = "gif" if avatar.startswith("a_") else "png"
            user_data["avatar"] = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.{ext}?size=256"
        else:
            user_data["avatar"] = "https://cdn.discordapp.com/embed/avatars/0.png"
    else:
        user_data["name"] = f"Citoyen {user_id}"
        user_data["avatar"] = "https://cdn.discordapp.com/embed/avatars/0.png"

    path = os.path.join(os.path.dirname(__file__), "site", "profile.html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            template = f.read()
            from flask import render_template_string
            return render_template_string(template, user=user_data, is_owner=is_owner, logged_in_user=logged_in_user)
            
    return "Profile template not found", 404


def get_discord_user_info(user_id):
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        return None
    headers = {"Authorization": f"Bot {token}"}
    try:
        resp = requests.get(f"https://discord.com/api/v10/users/{user_id}", headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Discord API Error: {e}")
    return None


def get_user_data(user_id):
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "botfazer"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "bot_fazer"),
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
                user_eco = cur.fetchone()
                
                if not user_eco:
                    return {
                        "id": user_id,
                        "exists": False,
                        "name": "Inconnu",
                        "balance": 0,
                        "bank": 0,
                        "inventory_count": 0,
                        "properties_count": 0,
                        "luxury_count": 0,
                        "games_played": 0,
                        "games_won": 0,
                        "games_lost": 0,
                        "win_rate": 0,
                        "amount_wagered": 0,
                        "amount_won": 0,
                        "rep": 0,
                        "commands_used": 0,
                        "total_wealth": 0
                    }
                
                cur.execute("SELECT COUNT(*) as count FROM inventory WHERE user_id=%s", (user_id,))
                inv_res = cur.fetchone()
                inv_count = inv_res["count"] if inv_res else 0

                cur.execute("SELECT * FROM user_stats WHERE user_id=%s", (user_id,))
                stats = cur.fetchone() or {}

                games_played = int(stats.get("games_played", 0))
                games_won = int(stats.get("games_won", 0))
                games_lost = int(stats.get("games_lost", 0))
                amount_wagered = int(stats.get("amount_wagered", 0))
                amount_won = int(stats.get("amount_won", 0))
                commands_used = int(stats.get("commands_used", 0))
                rep = int(stats.get("rep", 0))

                cur.execute(
                    "SELECT property_key, COUNT(*) as qty FROM user_properties WHERE user_id=%s GROUP BY property_key",
                    (user_id,),
                )
                prop_rows = cur.fetchall() or []

                properties_count = 0
                properties_total_value = 0
                properties_parts: list[str] = []
                properties_detailed: list[dict] = []
                for row in prop_rows:
                    key = row["property_key"]
                    qty = int(row["qty"])
                    properties_count += qty
                    base = PROPERTIES_BASE.get(key) or {}
                    price = int(base.get("base_price", 0))
                    properties_total_value += price * qty
                    name = base.get("name", key)
                    properties_parts.append(f"{name} x{qty}")
                    properties_detailed.append(
                        {
                            "key": key,
                            "name": name,
                            "qty": qty,
                            "unit_price": price,
                            "total_price": price * qty,
                        }
                    )

                properties_label = ", ".join(properties_parts[:3])
                if len(properties_parts) > 3:
                    properties_label += ", ..."

                cur.execute(
                    "SELECT c.name, c.level, cm.role FROM clan_members cm JOIN clans c ON cm.clan_id = c.id WHERE cm.user_id=%s",
                    (user_id,)
                )
                org_row = cur.fetchone()
                organization = None
                if org_row:
                    organization = {
                        "name": org_row["name"],
                        "level": org_row["level"],
                        "role": org_row["role"]
                    }

                cur.execute(
                    "SELECT item_key, serial_number FROM user_luxury WHERE user_id=%s ORDER BY purchase_date DESC",
                    (user_id,),
                )
                lux_rows = cur.fetchall() or []

                luxury_count = len(lux_rows)
                luxury_total_value = 0
                luxury_parts: list[str] = []
                luxury_detailed: list[dict] = []
                for row in lux_rows:
                    key = row["item_key"]
                    serial = row["serial_number"]
                    base = LUXURY_ITEMS_BASE.get(key) or {}
                    price = int(base.get("base_price", 0))
                    luxury_total_value += price
                    name = base.get("name", key)
                    label = f"{name}"
                    if serial:
                        label += f" #{serial}"
                    luxury_parts.append(label)
                    luxury_detailed.append(
                        {
                            "key": key,
                            "name": name,
                            "serial": serial,
                            "price": price,
                        }
                    )

                luxury_label = ", ".join(luxury_parts[:3])
                if len(luxury_parts) > 3:
                    luxury_label += ", ..."

                win_rate = 0
                if games_played > 0:
                    win_rate = round(games_won / games_played * 100)

                balance = int(user_eco.get("balance", 0))
                bank_main = int(user_eco.get("bank", 0))
                bank_2 = int(user_eco.get("bank_2", 0))
                bank_3 = int(user_eco.get("bank_3", 0))
                total_wealth = balance + bank_main + bank_2 + bank_3

                wealth_score = 0
                if total_wealth > 0:
                    wealth_score = min(100, total_wealth // 1_000_000 * 5)

                activity_score = min(100, games_played + commands_used * 2)
                luck_score = win_rate
                social_score = min(100, rep * 10)

                rank = "Citoyen"
                if total_wealth >= 50_000_000 or amount_won >= 50_000_000:
                    rank = "Magnat"
                elif total_wealth >= 10_000_000 or amount_won >= 10_000_000:
                    rank = "Flambeur"
                elif games_played >= 100:
                    rank = "Addict du Casino"
                
                return {
                    "id": user_id,
                    "exists": True,
                    "balance": balance,
                    "bank": bank_main,
                    "inventory_count": inv_count,
                    "properties_count": properties_count,
                    "luxury_count": luxury_count,
                    "games_played": games_played,
                    "games_won": games_won,
                    "games_lost": games_lost,
                    "win_rate": win_rate,
                    "amount_wagered": amount_wagered,
                    "amount_won": amount_won,
                    "rep": rep,
                    "commands_used": commands_used,
                    "total_wealth": total_wealth,
                    "wealth_score": wealth_score,
                    "activity_score": activity_score,
                    "luck_score": luck_score,
                    "social_score": social_score,
                    "rank": rank,
                    "properties_total_value": properties_total_value,
                    "luxury_total_value": luxury_total_value,
                    "properties_label": properties_label,
                    "luxury_label": luxury_label,
                    "properties_detailed": properties_detailed,
                    "luxury_detailed": luxury_detailed,
                    "organization": organization
                }
    except Exception as e:
        print(f"DB Error: {e}")
        return {
            "id": user_id,
            "exists": False, 
            "error": str(e),
            "balance": 0,
            "bank": 0,
            "inventory_count": 0,
            "properties_count": 0,
            "luxury_count": 0
        }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
