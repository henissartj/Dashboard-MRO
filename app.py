import ast
import os
import pymysql
from dotenv import load_dotenv

from flask import Flask, jsonify, send_from_directory

load_dotenv()

app = Flask(__name__, static_folder="site/assets", static_url_path="/assets")


@app.route("/")
def home():
    # Serve index.html if exists, else fallback
    index_path = os.path.join(os.path.dirname(__file__), "site", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Index not found", 404



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


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
