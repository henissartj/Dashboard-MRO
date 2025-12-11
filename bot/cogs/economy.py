import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiomysql
import os
import datetime as dt
import secrets
import re
import asyncio

CURRENCY_EMOJI = ":monnaie:"
PROTECTION_ROLE_ID = 1448414767533527153

DDL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        balance BIGINT NOT NULL DEFAULT 0,
        bank BIGINT NOT NULL DEFAULT 0,
        last_daily TIMESTAMP NULL,
        last_weekly TIMESTAMP NULL,
        last_monthly TIMESTAMP NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory (
        user_id BIGINT NOT NULL,
        item VARCHAR(64) NOT NULL,
        qty INT NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, item)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS shop (
        item VARCHAR(64) PRIMARY KEY,
        buy_price BIGINT NOT NULL,
        sell_price BIGINT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id VARCHAR(16) PRIMARY KEY,
        type VARCHAR(16) NOT NULL,
        requester_id BIGINT NOT NULL,
        target_id BIGINT NOT NULL,
        amount BIGINT NOT NULL,
        account VARCHAR(8) NOT NULL,
        status VARCHAR(16) NOT NULL,
        taxed TINYINT NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
]


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pool: aiomysql.Pool | None = None
        self._last_prices: dict[int, int] = {}
        self._prev_prices: dict[int, int] = {}
        self._fmt_cache: dict[int, str] = {}
        self._mines_sessions: dict[int, dict] = {}
        self._slash_cds: dict[str, dict[int, float]] = {}

    async def _connect(self):
        if self.pool:
            return
        host = os.getenv("DB_HOST", "127.0.0.1")
        db = os.getenv("DB_NAME", "bot_fazer")
        user = os.getenv("DB_USER", "botfazer")
        pwd = os.getenv("DB_PASSWORD", "")
        self.pool = await aiomysql.create_pool(
            host=host, db=db, user=user, password=pwd, autocommit=True, minsize=1, maxsize=10
        )
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                for sql in DDL:
                    await cur.execute(sql)

    def _currency_emoji(self, ctx: commands.Context) -> str:
        try:
            if ctx.guild:
                e = discord.utils.get(ctx.guild.emojis, name="monnaie")
                if e:
                    return str(e)
        except Exception:
            pass
        return "🪙"

    def _bank_embed(self, ctx: commands.Context, title: str, description: str | None = None, color: discord.Color | int = discord.Color.blurple(), fields: list[tuple[str, str, bool]] | None = None, txn_id: str | None = None, actor: discord.Member | discord.User | None = None) -> discord.Embed:
        emb = discord.Embed(title=title, description=description or "", color=color)
        try:
            who = actor or ctx.author
            avatar = who.avatar.url if getattr(who, "avatar", None) else who.display_avatar.url if hasattr(who, "display_avatar") else who.default_avatar.url
            emb.set_author(name=getattr(who, "display_name", getattr(who, "name", str(who))), icon_url=avatar)
        except Exception:
            emb.set_author(name=getattr(actor or ctx.author, "display_name", getattr(actor or ctx.author, "name", "")))
        if fields:
            for name, value, inline in fields:
                emb.add_field(name=name, value=value, inline=inline)
        return emb

    def _txn_id(self) -> str:
        return secrets.token_hex(4)

    def _fmt_amount(self, n: int) -> str:
        if n in self._fmt_cache:
            return self._fmt_cache[n]
        out = f"{n:,}".replace(",", ".")
        self._fmt_cache[n] = out
        return out

    

    def _parse_bet_amount(self, raw: str, available: int) -> int:
        s = (raw or "").strip().lower()
        if not s:
            return 0
        if s in ("all", "tout"):
            return int(available)
        mult = 1
        if s.endswith("k"):
            mult = 1_000
            s = s[:-1]
        elif s.endswith("m"):
            mult = 1_000_000
            s = s[:-1]
        s = re.sub(r"[\.,_]", "", s)
        try:
            return int(s) * mult
        except Exception:
            return 0

    async def cog_load(self):
        try:
            await self._connect()
        except Exception:
            return
        # système de bourse retiré: plus de boucle marché
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COUNT(*) FROM shop")
                    cnt = (await cur.fetchone())[0]
                    if cnt == 0:
                        items = [
                            ("tacos", 100, 60),
                            ("scoot", 1500, 900),
                            ("monnaie-collector", 5000, 3500),
                        ]
                        await cur.executemany("INSERT INTO shop(item, buy_price, sell_price) VALUES(%s,%s,%s)", items)
                    await cur.execute(
                        "INSERT INTO shop(item, buy_price, sell_price) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE buy_price=VALUES(buy_price), sell_price=VALUES(sell_price)",
                        ("protection", 50000, 0),
                    )
                    # système d’entreprises retiré: pas de seed
        except Exception:
            pass

    async def _ensure_user(self, uid: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT IGNORE INTO users(user_id) VALUES(%s)", (uid,))

    # Bank commands
    @commands.command(name="balance", aliases=["bal"]) 
    async def balance(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._connect(); member = member or ctx.author; await self._ensure_user(member.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (member.id,))
                bal, bank = await cur.fetchone()
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title=f"Solde de {member.display_name}",
            color=discord.Color.gold(),
            fields=[
                ("Poche", f"{self._fmt_amount(bal)} {cur}", True),
                ("Banque", f"{self._fmt_amount(bank)} {cur}", True),
            ],
            actor=member,
        )
        await ctx.send(embed=emb)

    @commands.command(name="deposit", aliases=["dep"]) 
    async def deposit(self, ctx: commands.Context, amount: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (ctx.author.id,))
                bal, bank = await cur.fetchone()
                try:
                    amt = bal if amount.lower() in ("all", "tout") else int(amount)
                except Exception:
                    emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                if amt <= 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                if bal < amt:
                    emb = self._bank_embed(ctx, title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                bal -= amt; bank += amt
                await cur.execute("UPDATE users SET balance=%s, bank=%s WHERE user_id=%s", (bal, bank, ctx.author.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Dépôt",
            color=discord.Color.green(),
            fields=[
                ("Montant", f"{self._fmt_amount(amt)} {cur}", True),
                ("Opérateur", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
        )
        await ctx.send(embed=emb)

    @commands.command(name="withdraw", aliases=["with"]) 
    async def withdraw(self, ctx: commands.Context, amount: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (ctx.author.id,))
                bal, bank = await cur.fetchone()
                try:
                    amt = bank if amount.lower() in ("all", "tout") else int(amount)
                except Exception:
                    emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                if amt <= 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                if bank < amt:
                    emb = self._bank_embed(ctx, title="Erreur", description="Pas assez à la banque.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                bank -= amt; bal += amt
                await cur.execute("UPDATE users SET balance=%s, bank=%s WHERE user_id=%s", (bal, bank, ctx.author.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Retrait",
            color=discord.Color.blue(),
            fields=[
                ("Montant", f"{self._fmt_amount(amt)} {cur}", True),
                ("Opérateur", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
        )
        await ctx.send(embed=emb)

    @commands.command(name="send", aliases=["give"]) 
    async def send(self, ctx: commands.Context, member: discord.Member, amount: int):
        await self._connect(); await self._ensure_user(ctx.author.id); await self._ensure_user(member.id)
        if amount <= 0:
            emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await ctx.send(embed=emb)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < amount:
                    emb = self._bank_embed(ctx, title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amount, ctx.author.id))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, member.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Virement",
            color=discord.Color.purple(),
            fields=[
                ("De", ctx.author.mention, True),
                ("Vers", member.mention, True),
                ("Montant", f"{self._fmt_amount(amount)} {cur}", True),
            ],
            txn_id=self._txn_id(),
        )
        await ctx.send(embed=emb)

    @commands.command(name="leaderboard", aliases=["lb"]) 
    async def leaderboard(self, ctx: commands.Context):
        await self._connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT user_id, (balance+bank) AS total FROM users ORDER BY total DESC LIMIT 10")
                rows = await cur.fetchall()
        cur = self._currency_emoji(ctx)
        desc = "\n".join([f"<@{uid}> — {self._fmt_amount(total)} {cur}" for uid, total in rows]) or "Aucun joueur."
        emb = self._bank_embed(ctx, title="Classement Banque", description=desc, color=discord.Color.orange())
        await ctx.send(embed=emb)

    # Shop commands
    @commands.command(name="shop")
    async def shop(self, ctx: commands.Context, item_name: str | None = None):
        await self._connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if item_name:
                    await cur.execute("SELECT item, buy_price, sell_price FROM shop WHERE item=%s", (item_name,))
                    row = await cur.fetchone()
                    if not row:
                        emb = self._bank_embed(ctx, title="Erreur", description="Item introuvable.", color=discord.Color.red())
                        return await ctx.send(embed=emb)
                    item, buy, sell = row
                    cur = self._currency_emoji(ctx)
                    emb = self._bank_embed(
                        ctx,
                        title=f"Infos {item}",
                        color=discord.Color.teal(),
                        fields=[
                            ("Prix d’achat", f"{self._fmt_amount(buy)} {cur}", True),
                            ("Prix de vente", f"{self._fmt_amount(sell)} {cur}", True),
                        ],
                        actor=ctx.author,
                    )
                    return await ctx.send(embed=emb)
                await cur.execute("SELECT item, buy_price, sell_price FROM shop ORDER BY buy_price ASC")
                rows = await cur.fetchall()
        cur = self._currency_emoji(ctx)
        desc = "\n".join([f"{i} — buy {self._fmt_amount(bp)} / sell {self._fmt_amount(sp)} {cur}" for i, bp, sp in rows]) or "Shop vide."
        emb = self._bank_embed(ctx, title="Shop", description=desc, color=discord.Color.teal())
        await ctx.send(embed=emb)

    @commands.command(name="buy")
    async def buy(self, ctx: commands.Context, item_name: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT buy_price FROM shop WHERE item=%s", (item_name,))
                row = await cur.fetchone()
                if not row:
                    emb = self._bank_embed(ctx, title="Erreur", description="Item introuvable.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                price = row[0]
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < price:
                    emb = self._bank_embed(ctx, title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (price, ctx.author.id))
                if item_name == "protection":
                    try:
                        role = ctx.guild.get_role(PROTECTION_ROLE_ID) if ctx.guild else None
                        if role:
                            await ctx.author.add_roles(role, reason="Achat protection")
                    except Exception:
                        pass
                    await cur.execute("INSERT INTO inventory(user_id,item,qty) VALUES(%s,%s,1) ON DUPLICATE KEY UPDATE qty=1", (ctx.author.id, item_name))
                else:
                    await cur.execute("INSERT INTO inventory(user_id,item,qty) VALUES(%s,%s,1) ON DUPLICATE KEY UPDATE qty=qty+1", (ctx.author.id, item_name))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Achat",
            color=discord.Color.green(),
            fields=[
                ("Article", item_name, True),
                ("Prix", f"{self._fmt_amount(price)} {cur}", True),
                ("Acheteur", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
            actor=ctx.author,
        )
        await ctx.send(embed=emb)

    @commands.command(name="sell")
    async def sell(self, ctx: commands.Context, item_name: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if item_name == "protection":
                    return await ctx.send("La protection ne peut pas être vendue.")
                await cur.execute("SELECT sell_price FROM shop WHERE item=%s", (item_name,))
                row = await cur.fetchone()
                if not row:
                    emb = self._bank_embed(ctx, title="Erreur", description="Item introuvable.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                price = row[0]
                await cur.execute("SELECT qty FROM inventory WHERE user_id=%s AND item=%s", (ctx.author.id, item_name))
                r = await cur.fetchone()
                qty = r[0] if r else 0
                if qty <= 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Tu n’as pas cet item.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                await cur.execute("UPDATE inventory SET qty=qty-1 WHERE user_id=%s AND item=%s", (ctx.author.id, item_name))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (price, ctx.author.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Vente",
            color=discord.Color.orange(),
            fields=[
                ("Article", item_name, True),
                ("Prix", f"{price} {cur}", True),
                ("Vendeur", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
            actor=ctx.author,
        )
        await ctx.send(embed=emb)

    @commands.command(name="inventory", aliases=["inv"]) 
    async def inventory(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._connect(); member = member or ctx.author; await self._ensure_user(member.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT item, qty FROM inventory WHERE user_id=%s AND qty>0 ORDER BY item", (member.id,))
                rows = await cur.fetchall()
        desc = "\n".join([f"{i} ×{q}" for i, q in rows]) or "Inventaire vide."
        emb = self._bank_embed(ctx, title=f"Inventaire de {member.display_name}", description=desc, color=discord.Color.blurple(), actor=member)
        await ctx.send(embed=emb)

    # Economy commands
    @commands.command(name="daily") 
    async def daily(self, ctx: commands.Context):
        await self._connect(); await self._ensure_user(ctx.author.id)
        reward = 200
        now = dt.datetime.now()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT last_daily FROM users WHERE user_id=%s", (ctx.author.id,))
                row = await cur.fetchone()
                last = row[0] if row else None
                if last and last.date() == now.date():
                    emb = self._bank_embed(ctx, title="Crédit quotidien", color=discord.Color.red(), fields=[("Statut", "Déjà collecté aujourd'hui", False), ("Dernière", last.strftime("%Y-%m-%d %H:%M:%S"), False)])
                    return await ctx.send(embed=emb)
                await cur.execute("UPDATE users SET balance=balance+%s, last_daily=NOW() WHERE user_id=%s", (reward, ctx.author.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Crédit quotidien",
            color=discord.Color.green(),
            fields=[
                ("Montant", f"+{reward} {cur}", True),
                ("Bénéficiaire", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
            actor=ctx.author,
        )
        await ctx.send(embed=emb)

    @commands.command(name="weekly") 
    async def weekly(self, ctx: commands.Context):
        await self._connect(); await self._ensure_user(ctx.author.id)
        reward = 1000
        now = dt.datetime.now()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT last_weekly FROM users WHERE user_id=%s", (ctx.author.id,))
                row = await cur.fetchone()
                last = row[0] if row else None
                if last and (last.isocalendar()[0], last.isocalendar()[1]) == (now.isocalendar()[0], now.isocalendar()[1]):
                    emb = self._bank_embed(ctx, title="Crédit hebdomadaire", color=discord.Color.red(), fields=[("Statut", "Déjà collecté cette semaine", False), ("Dernière", last.strftime("%Y-%m-%d %H:%M:%S"), False)])
                    return await ctx.send(embed=emb)
                await cur.execute("UPDATE users SET balance=balance+%s, last_weekly=NOW() WHERE user_id=%s", (reward, ctx.author.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Crédit hebdomadaire",
            color=discord.Color.green(),
            fields=[
                ("Montant", f"+{reward} {cur}", True),
                ("Bénéficiaire", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
            actor=ctx.author,
        )
        await ctx.send(embed=emb)

    @commands.command(name="monthly") 
    async def monthly(self, ctx: commands.Context):
        await self._connect(); await self._ensure_user(ctx.author.id)
        reward = 5000
        now = dt.datetime.now()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT last_monthly FROM users WHERE user_id=%s", (ctx.author.id,))
                row = await cur.fetchone()
                last = row[0] if row else None
                if last and (last.year, last.month) == (now.year, now.month):
                    emb = self._bank_embed(ctx, title="Crédit mensuel", color=discord.Color.red(), fields=[("Statut", "Déjà collecté ce mois", False), ("Dernière", last.strftime("%Y-%m-%d %H:%M:%S"), False)])
                    return await ctx.send(embed=emb)
                await cur.execute("UPDATE users SET balance=balance+%s, last_monthly=NOW() WHERE user_id=%s", (reward, ctx.author.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Crédit mensuel",
            color=discord.Color.green(),
            fields=[
                ("Montant", f"+{reward} {cur}", True),
                ("Bénéficiaire", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
            actor=ctx.author,
        )
        await ctx.send(embed=emb)

    # Admin commands
    @commands.command(name="add_money", aliases=["addmoney", "$addmoney"]) 
    @commands.has_permissions(administrator=True)
    async def add_money(self, ctx: commands.Context, member: discord.Member, amount: int, mode: str | None = None):
        await self._connect(); await self._ensure_user(member.id)
        col = "bank" if (mode or "").lower() == "bank" else "balance"
        if col not in ("balance", "bank"):
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Compte invalide.", color=discord.Color.red()))
        txid = self._txn_id()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (txid, "credit", ctx.author.id, member.id, amount, col, "pending"),
                )
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Crédit admin (en attente)",
            color=discord.Color.orange(),
            fields=[
                ("Cible", member.mention, True),
                ("Montant", f"+{amount} {cur}", True),
                ("Compte", col, True),
            ],
            txn_id=txid,
        )
        await ctx.send(embed=emb, view=AdminTransactionView(self, txid))

    @commands.command(name="accept")
    async def accept(self, ctx: commands.Context, txid: str):
        await self._connect()
        if ctx.author.id != 1443339902623154207:
            return await ctx.send("Non autorisé.")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT target_id, amount, account, status FROM transactions WHERE id=%s", (txid,))
                row = await cur.fetchone()
                if not row: return await ctx.send("Transaction introuvable.")
                target_id, amount, col, status = row
                if status != "pending":
                    return await ctx.send("Déjà traitée.")
                if col not in ("balance", "bank"):
                    return await ctx.send("Transaction invalide.")
                await cur.execute(f"UPDATE users SET {col}={col}+%s WHERE user_id=%s", (amount, target_id))
                await cur.execute("UPDATE transactions SET status='accepted' WHERE id=%s", (txid,))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(ctx, title="Transaction acceptée", color=discord.Color.green(), fields=[("ID", txid, True), ("Montant", f"+{amount} {cur}", True)], txn_id=txid)
        await ctx.send(embed=emb)

    @commands.command(name="refuse")
    async def refuse(self, ctx: commands.Context, txid: str):
        await self._connect()
        if ctx.author.id != 1443339902623154207:
            return await ctx.send("Non autorisé.")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT status FROM transactions WHERE id=%s", (txid,))
                row = await cur.fetchone()
                if not row: return await ctx.send("Transaction introuvable.")
                status = row[0]
                if status != "pending":
                    return await ctx.send("Déjà traitée.")
                await cur.execute("UPDATE transactions SET status='refused' WHERE id=%s", (txid,))
        emb = self._bank_embed(ctx, title="Transaction refusée", color=discord.Color.red(), fields=[("ID", txid, True)], txn_id=txid)
        await ctx.send(embed=emb)

    @commands.command(name="tax")
    async def tax(self, ctx: commands.Context, txid: str):
        await self._connect()
        if ctx.author.id != 1443339902623154207:
            return await ctx.send("Non autorisé.")
        TAX_RATE = 0.05
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT target_id, amount, account, status, taxed FROM transactions WHERE id=%s", (txid,))
                row = await cur.fetchone()
                if not row: return await ctx.send("Transaction introuvable.")
                target_id, amount, col, status, taxed = row
                if col not in ("balance", "bank"):
                    return await ctx.send("Transaction invalide.")
                if status not in ("accepted", "won"):
                    return await ctx.send("Transaction non taxable.")
                if taxed:
                    return await ctx.send("Taxe déjà appliquée.")
                tax_amt = max(1, int(amount * TAX_RATE))
                await cur.execute(f"SELECT {col} FROM users WHERE user_id=%s", (target_id,))
                avail = (await cur.fetchone())[0]
                tax_real = min(tax_amt, avail)
                if tax_real <= 0:
                    return await ctx.send("Rien à taxer.")
                await cur.execute(f"UPDATE users SET {col}={col}-%s WHERE user_id=%s", (tax_real, target_id))
                await cur.execute("UPDATE users SET bank=bank+%s WHERE user_id=%s", (tax_real, ctx.author.id))
                await cur.execute("UPDATE transactions SET taxed=1 WHERE id=%s", (txid,))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(ctx, title="Taxe appliquée", color=discord.Color.dark_red(), fields=[("ID", txid, True), ("Montant", f"{tax_real} {cur}", True)], txn_id=txid)
        await ctx.send(embed=emb)

    @commands.command(name="remove_money", aliases=["remoney"]) 
    @commands.has_permissions(administrator=True)
    async def remove_money(self, ctx: commands.Context, member: discord.Member, amount: int, mode: str | None = None):
        await self._connect(); await self._ensure_user(member.id)
        col = "bank" if (mode or "").lower() == "bank" else "balance"
        if col not in ("balance", "bank"):
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Compte invalide.", color=discord.Color.red()))
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"UPDATE users SET {col}={col}-%s WHERE user_id=%s", (amount, member.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Débit admin",
            color=discord.Color.red(),
            fields=[
                ("Cible", member.mention, True),
                ("Montant", f"-{amount} {cur}", True),
                ("Compte", col, True),
            ],
        )
        await ctx.send(embed=emb)

    @commands.command(name="reset_user") 
    @commands.has_permissions(administrator=True)
    async def reset_user(self, ctx: commands.Context, member: discord.Member):
        await self._connect(); await self._ensure_user(member.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=0, bank=0 WHERE user_id=%s", (member.id,))
                await cur.execute("DELETE FROM inventory WHERE user_id=%s", (member.id,))
        await ctx.send(embed=discord.Embed(description=f"Reset complet de {member.mention}", color=discord.Color.dark_gray()))

    # Fun commands
    @commands.command(name="coin_flip", aliases=["cf", "coinflip"], help="Pile/Face avec mise. Gains taxables via ID.") 
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def coin_flip(self, ctx: commands.Context, bet_on: str | None = None, amount: str | None = None):
        await self._connect(); await self._ensure_user(ctx.author.id)
        if bet_on is None or amount is None:
            view = CoinFlipView(self, ctx)
            return await ctx.send(embed=self._bank_embed(ctx, title="Casino • Pile ou Face", description=":coin: Choisis Pile ou Face et ta mise", color=discord.Color.blurple()), view=view)
        side = bet_on.lower()
        if side not in ("pile", "face"): return await ctx.send("Choisis 'pile' ou 'face'.")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(str(amount), bal_user)
        if amt <= 0: return await ctx.send("Montant invalide.")
        import random
        txid = None
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < amt: return await ctx.send("Pas assez en poche.")
                flip = random.choice(["pile", "face"])
                if flip == side:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amt, ctx.author.id))
                    txid = self._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", ctx.author.id, ctx.author.id, amt, "balance", "won"),
                    )
                    desc = f"Coin flip: {flip}. Gagné +{amt} {self._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, ctx.author.id))
                    desc = f"Coin flip: {flip}. Perdu -{amt} {self._currency_emoji(ctx)}"
                    color = discord.Color.red()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self._currency_emoji(ctx)
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = (
            f"Tirage: {flip}\n\n"
            + (f":tada: __**Vous avez gagné {self._fmt_amount(amt)} {cur_emoji} Fcoins !**__" if color == discord.Color.green() else f":x: **Vous avez perdu {self._fmt_amount(amt)} {cur_emoji} Fcoins**")
            + f"\n\nVotre solde s'estime à : **{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**" + extra_id
        )
        emb = self._bank_embed(ctx, title="Casino • Pile ou Face", description=full_desc, color=color, txn_id=txid)
        await ctx.send(embed=emb)

    @commands.command(name="ladder", help="Échelle Push Your Luck: +ladder montant") 
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def ladder(self, ctx: commands.Context, amount: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(str(amount), bal_user)
        if amt <= 0:
            return await ctx.send("Montant invalide.")
        view = LadderView(self, ctx, amt)
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(ctx, title="Casino • Échelle Push Your Luck", description=f"Mise initiale: **{self._fmt_amount(amt)} {cur_emoji}**\nChoisis 'Continuer' pour augmenter ton gain ou 'Encaisser' pour récupérer ton gain actuel.", color=discord.Color.blurple())
        await ctx.send(embed=emb, view=view)

    @commands.command(name="vol", aliases=["steal"]) 
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 60*60), commands.BucketType.user)
    async def vol(self, ctx: commands.Context, member: discord.Member):
        await self._connect(); await self._ensure_user(ctx.author.id); await self._ensure_user(member.id)
        if member.id == ctx.author.id:
            return await ctx.send("Tu ne peux pas te voler toi-même.")
        try:
            role = ctx.guild.get_role(PROTECTION_ROLE_ID) if ctx.guild else None
            if role and role in member.roles:
                emb = self._bank_embed(ctx, title="Vol", color=discord.Color.red(), fields=[("Statut", "Protégé — vol impossible", False), ("Victime", member.mention, True)])
                return await ctx.send(embed=emb)
        except Exception:
            pass
        import random
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (member.id,))
                r = await cur.fetchone()
                if not r:
                    return await ctx.send("Victime inconnue.")
                victim_bal, victim_bank = r
                if victim_bal <= 0:
                    emb = self._bank_embed(ctx, title="Vol", color=discord.Color.red(), fields=[("Statut", "Rien à voler (tout est à la banque)", False), ("Victime", member.mention, True)])
                    return await ctx.send(embed=emb)
                amount = random.randint(10, 100)
                amount = min(amount, victim_bal)
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amount, member.id))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, ctx.author.id))
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Vol",
            color=discord.Color.dark_gold(),
            fields=[
                ("Voleur", ctx.author.mention, True),
                ("Victime", member.mention, True),
                ("Montant", f"-{amount} {cur_emoji} pour la victime", False),
            ],
            txn_id=self._txn_id(),
        )
        await ctx.send(embed=emb)

    @commands.command(name="slots", aliases=["sl"], help="Machines à sous avec mise. Payouts variables.") 
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def slots(self, ctx: commands.Context, amount: str | None = None):
        await self._connect(); await self._ensure_user(ctx.author.id)
        if amount is None:
            view = SlotsView(self, ctx)
            return await ctx.send(embed=self._bank_embed(ctx, title="Casino • Machines à sous", description="🎰 Choisis ta mise", color=discord.Color.blurple()), view=view)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(str(amount), bal_user)
        if amt <= 0: return await ctx.send("Montant invalide.")
        import random
        reels = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
        txid = None
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < amt: return await ctx.send("Pas assez en poche.")
                r = [random.choice(reels) for _ in range(3)]
                unique = len(set(r))
                if unique == 1:
                    win = amt * 8
                elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
                    win = int(amt * 1.8)
                else:
                    win = 0
                if win > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win, ctx.author.id))
                    txid = self._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", ctx.author.id, ctx.author.id, win, "balance", "won"),
                    )
                    desc = f"Slots {' | '.join(r)} — Gagné +{win} {self._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, ctx.author.id))
                    desc = f"Slots {' | '.join(r)} — Perdu -{amt} {self._currency_emoji(ctx)}"
                    color = discord.Color.red()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self._currency_emoji(ctx)
        win_amt = win if txid else amt
        outcome_line = f":tada: __**Vous avez gagné {self._fmt_amount(win_amt)} {cur_emoji} Fcoins !**__" if txid else f":x: **Vous avez perdu {self._fmt_amount(amt)} {cur_emoji} Fcoins**"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Résultats: {' | '.join(r)}\n\n{outcome_line}\n\nVotre solde s'estime à : **{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**{extra_id}"
        emb = self._bank_embed(ctx, title="Casino • Machines à sous", description=full_desc, color=color, txn_id=txid)
        await ctx.send(embed=emb)

    @commands.command(name="dice", aliases=["de"], help="Pari pair/impair ou chiffre. Maison avantage légère.") 
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def dice(self, ctx: commands.Context, amount: str | None = None, bet_on: int | None = None):
        await self._connect(); await self._ensure_user(ctx.author.id)
        if amount is None:
            view = DiceView(self, ctx)
            return await ctx.send(embed=self._bank_embed(ctx, title="Casino • Jeu du dé", description=":game_die: Choisis mise et pari", color=discord.Color.blurple()), view=view)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(str(amount), bal_user)
        if amt <= 0: return await ctx.send("Montant invalide.")
        import random
        if bet_on is not None and not (1 <= bet_on <= 6):
            return await ctx.send("Parie sur un nombre entre 1 et 6.")
        txid = None
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < amt: return await ctx.send("Pas assez en poche.")
                roll = random.randint(1, 6)
                if bet_on is None:
                    if roll % 2 == 0:
                        win = amt
                    else:
                        win = -amt
                else:
                    if roll == bet_on:
                        win = amt * 5
                    else:
                        win = -amt
                if win > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win, ctx.author.id))
                    txid = self._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", ctx.author.id, ctx.author.id, win, "balance", "won"),
                    )
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (-win, ctx.author.id))
                desc = f"Dé {roll} — {'Gagné +' + str(win) if win>0 else 'Perdu ' + str(win)} {self._currency_emoji(ctx)}"
                color = discord.Color.green() if win > 0 else discord.Color.red()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self._currency_emoji(ctx)
        gain_line = f":tada: __**Vous avez gagné {self._fmt_amount(win)} {cur_emoji} Fcoins !**__" if win > 0 else f":x: **Vous avez perdu {self._fmt_amount(-win)} {cur_emoji} Fcoins**"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Le dé est tombé sur : {roll} :game_die:\n\n{gain_line}\n\nVotre solde s'estime à : **{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**{extra_id}"
        emb = self._bank_embed(ctx, title="Casino • Jeu du dé", description=full_desc, color=color, txn_id=txid)
        await ctx.send(embed=emb)

    @commands.command(name="mines", help="Jeu Mines 5×5 : +mines <montant> <mines 1–24>") 
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def mines(self, ctx: commands.Context, amount: str, mines: int):
        await self._connect(); await self._ensure_user(ctx.author.id)
        if not (1 <= mines <= 24):
            return await ctx.send("Choisis un nombre de mines entre 1 et 24.")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(str(amount), bal_user)
        if amt <= 0:
            return await ctx.send("Montant invalide.")
        if bal_user < amt:
            return await ctx.send("Pas assez en poche.")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, ctx.author.id))
        import random
        mines_set = set(random.sample(range(25), mines))
        session = {"bet": amt, "mines": mines, "mines_set": mines_set, "revealed": set(), "mult": 1.0, "ended": False}
        self._mines_sessions[ctx.author.id] = session
        cur_emoji = self._currency_emoji(ctx)
        desc = (
            f"Votre mise : {self._fmt_amount(amt)} {cur_emoji} • Nombre de mines : {mines}\n"
            f"Cases révélées : 0 • Gain potentiel : {self._fmt_amount(max(1, int(amt * 0.95)))} {cur_emoji}"
        )
        emb = self._bank_embed(ctx, title="Casino • Mines", description=desc, color=discord.Color.blurple())
        view_grid = MinesView(self, ctx, ctx.author.id)
        msg = await ctx.send(embed=emb, view=view_grid)
        view_cash = MinesCashView(self, ctx, ctx.author.id)
        cash_msg = await msg.reply(view=view_cash)
        self._mines_sessions[ctx.author.id]["cash_message_id"] = cash_msg.id

class MinesView(discord.ui.View):
    def __init__(self, cog: Economy, ctx: commands.Context, session_owner_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.session_owner_id = session_owner_id
        for i in range(25):
            btn = discord.ui.Button(label="❓", style=discord.ButtonStyle.secondary, row=i // 5)
            async def _cb(interaction: discord.Interaction, idx=i, b=btn):
                if interaction.user.id != self.session_owner_id:
                    return await interaction.response.send_message("Seul l’initiateur peut jouer.")
                s = self.cog._mines_sessions.get(self.session_owner_id)
                if not s or s.get("ended"):
                    return await interaction.response.send_message("Partie terminée.")
                if idx in s["revealed"]:
                    return await interaction.response.send_message("Déjà révélé.")
                s["revealed"].add(idx)
                if idx in s["mines_set"]:
                    s["ended"] = True
                    b.label = "💣"; b.disabled = True
                    for item in list(self.children):
                        try:
                            item.disabled = True
                        except Exception:
                            pass
                    async with self.cog.pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute("SELECT balance FROM users WHERE user_id=%s", (self.session_owner_id,))
                            bal_after = (await cur.fetchone())[0]
                    cur_emoji = self.cog._currency_emoji(self.ctx)
                    full_desc = (
                        ":boom: __**Vous êtes tombé sur la mine !**__\n\n"
                        f"Vous avez perdu {self.cog._fmt_amount(s['bet'])} {cur_emoji}\n\n"
                        f"Votre solde actuel s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji}**"
                    )
                    emb = self.cog._bank_embed(self.ctx, title="Casino • Mines", description=full_desc, color=discord.Color.red())
                    await interaction.response.edit_message(embed=emb, view=None)
                    cash_id = s.get("cash_message_id")
                    try:
                        if cash_id and interaction.channel:
                            msg = await interaction.channel.fetch_message(cash_id)
                            await msg.edit(view=None)
                    except Exception:
                        pass
                    return
                total_rem = 25 - len(s["revealed"])
                safe_rem = (25 - s["mines"]) - len(s["revealed"]) 
                q = max(1e-6, safe_rem / max(1, total_rem))
                s["mult"] *= (1.0 / q)
                b.label = "💎"; b.disabled = True
                cur_emoji = self.cog._currency_emoji(self.ctx)
                potential = max(1, int(s["bet"] * s["mult"] * 0.95))
                desc = (
                    f"Votre mise : {self.cog._fmt_amount(s['bet'])} {cur_emoji} • Nombre de mines : {s['mines']}\n"
                    f"Cases révélées : {len(s['revealed'])} • Gain potentiel : {self.cog._fmt_amount(potential)} {cur_emoji}"
                )
                emb = self.cog._bank_embed(self.ctx, title="Casino • Mines", description=desc, color=discord.Color.blurple())
                await interaction.response.edit_message(embed=emb, view=self)
            btn.callback = _cb
            self.add_item(btn)

class MinesCashView(discord.ui.View):
    def __init__(self, cog: Economy, ctx: commands.Context, session_owner_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.session_owner_id = session_owner_id

    @discord.ui.button(label="Encaisser", style=discord.ButtonStyle.success)
    async def cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.session_owner_id:
            return await interaction.response.send_message("Seul l’initiateur peut encaisser.")
        s = self.cog._mines_sessions.get(self.session_owner_id)
        if not s or s.get("ended"):
            return await interaction.response.send_message("Partie terminée.")
        payout = max(1, int(s["bet"] * s["mult"] * 0.95))
        txid = None
        await self.cog._connect(); await self.cog._ensure_user(self.session_owner_id)
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (payout, self.session_owner_id))
                txid = self.cog._txn_id()
                await cur.execute(
                    "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (txid, "win", self.session_owner_id, self.session_owner_id, payout, "balance", "won"),
                )
        self.cog._mines_sessions[self.session_owner_id]["ended"] = True
        cur_emoji = self.cog._currency_emoji(self.ctx)
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (self.session_owner_id,))
                bal_after = (await cur.fetchone())[0]
        full_desc = (
            ":moneybag: __**Encaissement**__\n\n"
            f"Vous gagnez {self.cog._fmt_amount(payout)} {cur_emoji}\n\n"
            f"Votre solde actuel s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji}**"
        )
        emb = self.cog._bank_embed(self.ctx, title="Casino • Mines", description=full_desc, color=discord.Color.green(), txn_id=txid)
        await interaction.response.edit_message(embed=emb, view=None)
        try:
            cash_id = self.cog._mines_sessions[self.session_owner_id].get("cash_message_id")
            if cash_id and interaction.channel:
                msg = await interaction.channel.fetch_message(cash_id)
                await msg.edit(view=None)
        except Exception:
            pass

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.session_owner_id:
            return await interaction.response.send_message("Seul l’initiateur peut annuler.")
        s = self.cog._mines_sessions.get(self.session_owner_id)
        if not s or s.get("ended"):
            return await interaction.response.send_message("Partie terminée.")
        self.cog._mines_sessions[self.session_owner_id]["ended"] = True
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (self.session_owner_id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self.cog._currency_emoji(self.ctx)
        full_desc = (
            ":stop_sign: __**Partie annulée**__\n\n"
            f"Votre solde actuel s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji}**"
        )
        emb = self.cog._bank_embed(self.ctx, title="Casino • Mines", description=full_desc, color=discord.Color.dark_gray())
        await interaction.response.edit_message(embed=emb, view=None)
        try:
            cash_id = self.cog._mines_sessions[self.session_owner_id].get("cash_message_id")
            if cash_id and interaction.channel:
                msg = await interaction.channel.fetch_message(cash_id)
                await msg.edit(view=None)
        except Exception:
            pass

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    

    
    
    
    

    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    

    
    
    
    

    
    
    
    
    
    

    
    
    
    

    
    
    
    

    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    

    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    

    

    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    

    
    
    
    
    
    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    

    


    
    

    
    

    
    

    
    
    
    
    

    
    

    
    

    
    

    
    

    
    

    
    

    
    

    
    

    
    

    
    

    
    
    

    
    
    
    
    

    
    

    
    

    
    

    
    
    
    

    
    
    
    
    

    
    
    
    
    

    
    
    
    

    

    

    

    

    

    

    

    
    
    

    
    

    
    

    
    

    
    

    
    

    
    

    
    

    
    


    

class CoinFlipView(discord.ui.View):
    def __init__(self, cog: Economy, ctx: commands.Context):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.side: str | None = None
        self.amount: int = 10

    @discord.ui.button(label="Pile", style=discord.ButtonStyle.primary)
    async def pile(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.side = "pile"
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Choix: Pile • Mise: {self.amount} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="Face", style=discord.ButtonStyle.primary)
    async def face(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.side = "face"
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Choix: Face • Mise: {self.amount} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="10", style=discord.ButtonStyle.secondary)
    async def bet10(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 10
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Mise: {self.amount} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary)
    async def bet50(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 50
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Mise: {self.amount} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="100", style=discord.ButtonStyle.secondary)
    async def bet100(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 100
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Mise: {self.amount} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="Jouer", style=discord.ButtonStyle.success)
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.side:
            return await interaction.response.send_message("Choisis Pile ou Face.")
        ctx = self.ctx
        await self.cog._ensure_user(ctx.author.id)
        import random
        txid = None
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < self.amount:
                    return await interaction.response.send_message("Pas assez en poche.")
                flip = random.choice(["pile", "face"])
                if flip == self.side:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (self.amount, ctx.author.id))
                    txid = self.cog._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", ctx.author.id, ctx.author.id, self.amount, "balance", "won"),
                    )
                    desc = f"Coin flip: {flip}. Gagné +{self.amount} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (self.amount, ctx.author.id))
                    desc = f"Coin flip: {flip}. Perdu -{self.amount} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.red()
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur2:
                await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur2.fetchone())[0]
        outcome_line = f":tada: __**Vous avez gagné {self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(ctx)} Fcoins !**__" if txid else f":x: **Vous avez perdu {self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(ctx)} Fcoins**"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Tirage: {flip}\n\n{outcome_line}\n\nVotre solde s'estime à : **{self.cog._fmt_amount(bal_after)} {self.cog._currency_emoji(ctx)} Fcoins**{extra_id}"
        emb = self.cog._bank_embed(self.ctx, title="Casino • Pile ou Face", description=full_desc, color=color, txn_id=txid)
        await interaction.response.edit_message(embed=emb, view=None)

class ScootRaceView(discord.ui.View):
    def __init__(self, cog: Economy, ctx: commands.Context, target: discord.Member, amount: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.target = target
        self.amount = amount

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("Seule la personne ping peut répondre.")
        await self.cog._ensure_user(self.ctx.author.id); await self.cog._ensure_user(self.target.id)
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (self.ctx.author.id,))
                a_bal = (await cur.fetchone())[0]
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (self.target.id,))
                t_bal = (await cur.fetchone())[0]
                if a_bal < self.amount or t_bal < self.amount:
                    return await interaction.response.send_message("Solde insuffisant pour l’un des deux.")
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (self.amount, self.ctx.author.id))
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (self.amount, self.target.id))
        import random
        winner = self.ctx.author if random.random() < 0.5 else self.target
        gain = self.amount * 2
        txid = None
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (gain, winner.id))
                txid = self.cog._txn_id()
                await cur.execute(
                    "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (txid, "win", winner.id, winner.id, gain, "balance", "won"),
                )
        cur_emoji = self.cog._currency_emoji(self.ctx)
        desc = f"Course Scoot • Mise: {self.amount} {cur_emoji} chacun\nGagnant: {winner.mention} (+{gain} {cur_emoji})"
        emb = self.cog._bank_embed(self.ctx, title="Scoot", description=desc, color=discord.Color.green(), txn_id=txid)
        await interaction.response.edit_message(embed=emb, view=None)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("Seule la personne ping peut répondre.")
        emb = self.cog._bank_embed(self.ctx, title="Scoot", description=f"Refusé par {self.target.mention}", color=discord.Color.red())
        await interaction.response.edit_message(embed=emb, view=None)

class SlotsView(discord.ui.View):
    def __init__(self, cog: Economy, ctx: commands.Context):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.amount: int = 10

    @discord.ui.button(label="10", style=discord.ButtonStyle.secondary)
    async def bet10(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 10
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=f"🎰 Mise: **{self.amount} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary)
    async def bet50(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 50
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=f"🎰 Mise: **{self.amount} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="100", style=discord.ButtonStyle.secondary)
    async def bet100(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 100
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=f"🎰 Mise: **{self.amount} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="Spin", style=discord.ButtonStyle.success)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = self.ctx
        await self.cog._ensure_user(ctx.author.id)
        import random
        reels = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
        txid = None
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < self.amount:
                    return await interaction.response.send_message("Pas assez en poche.")
                r = [random.choice(reels) for _ in range(3)]
                win = 0
                if len(set(r)) == 1: win = self.amount * 5
                elif len({r[0], r[1], r[2]}) == 2: win = self.amount * 2
                if win > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win, ctx.author.id))
                    txid = self.cog._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", ctx.author.id, ctx.author.id, win, "balance", "won"),
                    )
                    desc = f"Slots {' | '.join(r)} — Gagné +{win} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (self.amount, ctx.author.id))
                    desc = f"Slots {' | '.join(r)} — Perdu -{self.amount} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.red()
        cur_emoji = self.cog._currency_emoji(ctx)
        if txid:
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                    bal_after = (await cur.fetchone())[0]
            outcome_line = f":tada: __**Vous avez gagné {self.cog._fmt_amount(win)} {cur_emoji} Fcoins !**__"
            extra_id = f"\n\nID: {txid}" if txid else ""
            full_desc = f"Résultats: {' | '.join(r)}\n\n{outcome_line}\n\nVotre solde s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**{extra_id}"
            emb = self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=full_desc, color=color, txn_id=txid)
        else:
            outcome_line = f":x: **Vous avez perdu {self.cog._fmt_amount(self.amount)} {cur_emoji} Fcoins**"
            full_desc = f"Résultats: {' | '.join(r)}\n\n{outcome_line}"
            emb = self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=full_desc, color=color)
        await interaction.response.edit_message(embed=emb, view=None)

class DiceView(discord.ui.View):
    def __init__(self, cog: Economy, ctx: commands.Context):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.amount: int = 10
        self.bet_on: int | None = None
        self.parity: str | None = None

    @discord.ui.button(label="10", style=discord.ButtonStyle.secondary)
    async def bet10(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 10
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Mise: **{self.amount} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary)
    async def bet50(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 50
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Mise: **{self.amount} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="100", style=discord.ButtonStyle.secondary)
    async def bet100(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 100
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Mise: **{self.amount} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="Pair", style=discord.ButtonStyle.primary)
    async def pair(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parity = "pair"
        self.bet_on = None
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Pari: **Pair** • Mise: **{self.amount}**", color=discord.Color.blurple()))

    @discord.ui.button(label="Impair", style=discord.ButtonStyle.primary)
    async def impair(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parity = "impair"
        self.bet_on = None
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Pari: **Impair** • Mise: **{self.amount}**", color=discord.Color.blurple()))

    @discord.ui.select(placeholder="Choisis un nombre", options=[discord.SelectOption(label=str(i), value=str(i)) for i in range(1,7)])
    async def choose_number(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.bet_on = int(select.values[0])
        self.parity = None
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Pari: **{self.bet_on}** • Mise: **{self.amount}**", color=discord.Color.blurple()))

    @discord.ui.button(label="Jouer", style=discord.ButtonStyle.success)
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = self.ctx
        await self.cog._ensure_user(ctx.author.id)
        import random
        txid = None
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < self.amount:
                    return await interaction.response.send_message("Pas assez en poche.")
                roll = random.randint(1, 6)
                if self.bet_on is None:
                    win = self.amount if (roll % 2 == 0 and self.parity == "pair") or (roll % 2 == 1 and self.parity == "impair") else -self.amount
                else:
                    win = self.amount * 5 if roll == self.bet_on else -self.amount
                if win >= 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win, ctx.author.id))
                    txid = self.cog._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", ctx.author.id, ctx.author.id, win, "balance", "won"),
                    )
                    desc = f"Dé {roll} — Gagné +{win} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (-win, ctx.author.id))
                    desc = f"Dé {roll} — Perdu {win} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.red()
        if txid:
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                    bal_after = (await cur.fetchone())[0]
            cur_emoji = self.cog._currency_emoji(ctx)
            gain_line = f"**Vous avez gagné {win} {cur_emoji} Fcoins**" if win > 0 else f"**Vous avez perdu {-win} {cur_emoji} Fcoins**"
            extra_id = f"\n\nID: {txid}" if txid else ""
            full_desc = f"Le dé est tombé sur : {roll} :game_die:\n\n{gain_line}\n\nVotre solde s'estime à : **{bal_after} {cur_emoji} Fcoins**{extra_id}"
            emb = self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=full_desc, color=color, txn_id=txid)
        else:
            full_desc = f"Le dé est tombé sur : {roll} :game_die:\n\n**Vous avez perdu {-win} {cur_emoji} Fcoins**"
            emb = self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=full_desc, color=color)
        await interaction.response.edit_message(embed=emb, view=None)

class LadderView(discord.ui.View):
    def __init__(self, cog: Economy, ctx: commands.Context, base_amt: int):
        super().__init__(timeout=90)
        self.cog = cog
        self.ctx = ctx
        self.base_amt = base_amt
        self.step = 0
        self.mult = 1.0

    @discord.ui.button(label="Continuer", style=discord.ButtonStyle.success)
    async def cont(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._ensure_user(self.ctx.author.id)
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (self.ctx.author.id,))
                bal = (await cur.fetchone())[0]
        if bal < self.base_amt:
            return await interaction.response.send_message("Pas assez en poche.")
        import random
        busts = [0.20, 0.35, 0.50, 0.65, 0.80]
        mults = [1.5, 2.0, 2.5, 3.0, 3.5]
        p = busts[self.step] if self.step < len(busts) else 0.90
        m_next = mults[self.step] if self.step < len(mults) else (self.mult + 0.5)
        if random.random() < p:
            txid = None
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (self.base_amt, self.ctx.author.id))
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur2:
                    await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (self.ctx.author.id,))
                    bal_after = (await cur2.fetchone())[0]
            cur_emoji = self.cog._currency_emoji(self.ctx)
            outcome_line = f":x: **Vous avez perdu {self.cog._fmt_amount(self.base_amt)} {cur_emoji} Fcoins**"
            full_desc = f"Échelle: Bust instantané\n\n{outcome_line}\n\nVotre solde s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**"
            color = discord.Color.red()
            emb = self.cog._bank_embed(self.ctx, title="Casino • Échelle Push Your Luck", description=full_desc, color=color)
            return await interaction.response.edit_message(embed=emb, view=None)
        self.mult = m_next
        self.step += 1
        cur_emoji = self.cog._currency_emoji(self.ctx)
        potential = int(self.base_amt * self.mult * 0.95)
        desc = f"Étape: {self.step} • Multiplicateur: x{self.mult:.2f} • Risque bust: {int(p*100)}%\nGain potentiel: **{self.cog._fmt_amount(potential)} {cur_emoji}**"
        emb = self.cog._bank_embed(self.ctx, title="Casino • Échelle Push Your Luck", description=desc, color=discord.Color.blurple())
        await interaction.response.edit_message(embed=emb, view=self)

    @discord.ui.button(label="Encaisser", style=discord.ButtonStyle.primary)
    async def cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog._ensure_user(self.ctx.author.id)
        payout = max(1, int(self.base_amt * self.mult * 0.95))
        txid = None
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (payout, self.ctx.author.id))
                txid = self.cog._txn_id()
                await cur.execute("INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)", (txid, "win", self.ctx.author.id, self.ctx.author.id, payout, "balance", "won"))
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur2:
                await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (self.ctx.author.id,))
                bal_after = (await cur2.fetchone())[0]
        cur_emoji = self.cog._currency_emoji(self.ctx)
        outcome_line = f":tada: __**Vous avez gagné {self.cog._fmt_amount(payout)} {cur_emoji} Fcoins !**__"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Étapes franchies: {self.step}\n\n{outcome_line}\n\nVotre solde s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**" + extra_id
        color = discord.Color.green()
        emb = self.cog._bank_embed(self.ctx, title="Casino • Échelle Push Your Luck", description=full_desc, color=color, txn_id=txid)
        await interaction.response.edit_message(embed=emb, view=None)

class TaxTransactionView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=1)

class AdminTransactionView(discord.ui.View):
    def __init__(self, cog: Economy, txid: str):
        super().__init__(timeout=120)
        self.cog = cog
        self.txid = txid

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != 1443339902623154207:
            return await interaction.response.send_message("Non autorisé.")
        await self.cog._connect()
        txid = self.txid
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT target_id, amount, account, status FROM transactions WHERE id=%s", (txid,))
                row = await cur.fetchone()
                if not row:
                    return await interaction.response.send_message("Transaction introuvable.")
                target_id, amount, col, status = row
                if status != "pending":
                    return await interaction.response.send_message("Déjà traitée.")
                await cur.execute(f"UPDATE users SET {col}={col}+%s WHERE user_id=%s", (amount, target_id))
                await cur.execute("UPDATE transactions SET status='accepted' WHERE id=%s", (txid,))
        try:
            base = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
            if base:
                emb = discord.Embed.from_dict(base.to_dict())
                emb.title = "Crédit admin (accepté)"
                emb.color = discord.Color.green()
            else:
                emb = discord.Embed(title="Crédit admin (accepté)", color=discord.Color.green())
            await interaction.response.edit_message(embed=emb, view=None)
        except Exception:
            await interaction.response.send_message("Accepté.")

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != 1443339902623154207:
            return await interaction.response.send_message("Non autorisé.")
        await self.cog._connect()
        txid = self.txid
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT status FROM transactions WHERE id=%s", (txid,))
                row = await cur.fetchone()
                if not row:
                    return await interaction.response.send_message("Transaction introuvable.")
                status = row[0]
                if status != "pending":
                    return await interaction.response.send_message("Déjà traitée.")
                await cur.execute("UPDATE transactions SET status='refused' WHERE id=%s", (txid,))
        try:
            base = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
            if base:
                emb = discord.Embed.from_dict(base.to_dict())
                emb.title = "Crédit admin (refusé)"
                emb.color = discord.Color.red()
            else:
                emb = discord.Embed(title="Crédit admin (refusé)", color=discord.Color.red())
            await interaction.response.edit_message(embed=emb, view=None)
        except Exception:
            await interaction.response.send_message("Refusée.")


    @commands.command(name="scoot", help="Defie en course scoot: +scoot @membre montant. Pari symétrique.") 
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def scoot(self, ctx: commands.Context, member: discord.Member, amount: int):
        await self._connect(); await self._ensure_user(ctx.author.id); await self._ensure_user(member.id)
        if member.id == ctx.author.id:
            return await ctx.send("Choisis quelqu’un d’autre.")
        if amount <= 0:
            return await ctx.send("Montant invalide.")
        view = ScootRaceView(self, ctx, member, amount)
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(ctx, title="Scoot", description=f"{ctx.author.mention} défie {member.mention}. Mise: {amount} {cur_emoji} chacun.", color=discord.Color.blurple())
        await ctx.send(embed=emb, view=view)

    @commands.command(name="khedma", help="Travaille et gagne 100. Cooldown 5 minutes.")
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5*60), commands.BucketType.user)
    async def khedma(self, ctx: commands.Context):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance+100 WHERE user_id=%s", (ctx.author.id,))
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(ctx, title="Khedma", description=f"+100 {cur_emoji}", color=discord.Color.green(), actor=ctx.author)
        await ctx.send(embed=emb)

    # système d’entreprise retiré
    async def entreprise(self, ctx: commands.Context, name: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT bank FROM users WHERE user_id=%s", (ctx.author.id,))
                bank = (await cur.fetchone())[0]
                if bank < 100000:
                    return await ctx.send("Il faut 100000 en banque.")
                await cur.execute("SELECT id FROM enterprises WHERE name=%s", (name,))
                if await cur.fetchone():
                    return await ctx.send("Nom déjà pris.")
                await cur.execute("UPDATE users SET bank=bank-100000 WHERE user_id=%s", (ctx.author.id,))
                await cur.execute("INSERT INTO enterprises(name, owner_id, price, total_shares, funds) VALUES(%s,%s,%s,%s,%s)", (name, ctx.author.id, 1000, 100, 0))
                await cur.execute("SELECT id FROM enterprises WHERE name=%s", (name,))
                eid = (await cur.fetchone())[0]
                await cur.execute("INSERT INTO investments(enterprise_id, user_id, shares) VALUES(%s,%s,%s)", (eid, ctx.author.id, 100))
        emb = self._bank_embed(ctx, title="Entreprise créée", description=f"{name} créée par {ctx.author.mention}", color=discord.Color.teal())
        await ctx.send(embed=emb)

    # système d’entreprise retiré
    async def investir(self, ctx: commands.Context, name: str, amount: int):
        await self._connect(); await self._ensure_user(ctx.author.id)
        if amount <= 0:
            return await ctx.send("Montant invalide.")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id, price, total_shares FROM enterprises WHERE name=%s", (name,))
                row = await cur.fetchone()
                if not row:
                    return await ctx.send("Entreprise introuvable.")
                eid, price, total = row
                shares = amount // price
                if shares <= 0:
                    return await ctx.send("Montant trop faible pour une part.")
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                cost = shares * price
                if bal < cost:
                    return await ctx.send("Pas assez en poche.")
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (cost, ctx.author.id))
                await cur.execute("INSERT INTO investments(enterprise_id, user_id, shares) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE shares=shares+VALUES(shares)", (eid, ctx.author.id, shares))
                await cur.execute("UPDATE enterprises SET total_shares=total_shares+%s, funds=funds+%s WHERE id=%s", (shares, cost, eid))
        emb = self._bank_embed(ctx, title="Investissement", description=f"Achat de {shares} parts de {name}", color=discord.Color.gold(), actor=ctx.author)
        await ctx.send(embed=emb)

    # système d’entreprise retiré
    async def vendre_parts(self, ctx: commands.Context, name: str, qty: int):
        await self._connect(); await self._ensure_user(ctx.author.id)
        if qty <= 0:
            return await ctx.send("Quantité invalide.")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id, price FROM enterprises WHERE name=%s", (name,))
                row = await cur.fetchone()
                if not row:
                    emb = self._bank_embed(ctx, title="Erreur", description="Système d’entreprise retiré.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                eid, price = row
                await cur.execute("SELECT shares FROM investments WHERE enterprise_id=%s AND user_id=%s", (eid, ctx.author.id))
                inv = await cur.fetchone()
                shares = inv[0] if inv else 0
                if shares < qty:
                    emb = self._bank_embed(ctx, title="Erreur", description="Système d’entreprise retiré.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                proceeds = qty * price
                await cur.execute("UPDATE investments SET shares=shares-%s WHERE enterprise_id=%s AND user_id=%s", (qty, eid, ctx.author.id))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (proceeds, ctx.author.id))
                await cur.execute("UPDATE enterprises SET total_shares=total_shares-%s, funds=funds-%s WHERE id=%s", (qty, proceeds, eid))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(ctx, title="Système d’entreprise retiré", description="Cette fonction n’est plus disponible.", color=discord.Color.dark_gray(), actor=ctx.author)
        await ctx.send(embed=emb)

    # système d’entreprise retiré
    async def entreprises(self, ctx: commands.Context):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT name, price, total_shares FROM enterprises ORDER BY price DESC")
                rows = await cur.fetchall()
        emb = self._bank_embed(ctx, title="Système d’entreprise retiré", description="Les entreprises ne sont plus disponibles.", color=discord.Color.dark_gray())
        await ctx.send(embed=emb)

    # système de bourse retiré
    async def bourse(self, ctx: commands.Context, *, name: str | None = None):
        await self._connect(); await self._ensure_user(ctx.author.id)
        emb = self._bank_embed(ctx, title="Système de bourse retiré", description="Cette fonction n’est plus disponible.", color=discord.Color.dark_gray())
        await ctx.send(embed=emb)

    @commands.command(name="portefeuille", help="Vos parts par entreprise")
    async def portefeuille(self, ctx: commands.Context):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT e.name, i.shares FROM investments i JOIN enterprises e ON i.enterprise_id=e.id WHERE i.user_id=%s ORDER BY e.name", (ctx.author.id,))
                rows = await cur.fetchall()
        desc = "\n".join([f"{n} — {s} parts" for n, s in rows]) or "Aucune part."
        emb = self._bank_embed(ctx, title="Portefeuille", description=desc, color=discord.Color.green(), actor=ctx.author)
        await ctx.send(embed=emb)

    @commands.command(name="tick_bourse", help="Forcer un tick du marché")
    async def tick_bourse(self, ctx: commands.Context):
        if ctx.author.id != 1443339902623154207:
            return await ctx.send("Non autorisé.")
        emb = self._bank_embed(ctx, title="Système de bourse retiré", description="Cette fonction n’est plus disponible.", color=discord.Color.dark_gray())
        await ctx.send(embed=emb)

    # système de bourse retiré

    async def _run_market_tick(self):
        await self._connect()
        try:
            print("market tick: start")
        except Exception:
            pass
        import random
        market_bias = random.uniform(-0.5, 0.8)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id, owner_id, name, price FROM enterprises")
                rows = await cur.fetchall()
                summaries = []
                ch = await self._resolve_bourse_channel()
                ctx_like = type("_Ctx", (), {"author": self.bot.user, "guild": getattr(ch, "guild", None)})() if ch else None
                cur_emoji = self._currency_emoji(ctx_like) if ctx_like else ""
                if not ch:
                    try:
                        print("bourse channel not found; notifications skipped")
                    except Exception:
                        pass
                for eid, owner_id, name, price in rows:
                    self._prev_prices[eid] = price
                    noise = random.uniform(-0.25, 0.35)
                    factor = market_bias + noise
                    if random.random() < 0.25:
                        factor *= random.uniform(1.2, 2.0)
                    if abs(factor) < 0.12:
                        factor = (1 if random.random() < 0.5 else -1) * random.uniform(0.2, 0.5)
                    if factor > 0.9:
                        factor = 0.9
                    if factor < -0.9:
                        factor = -0.9
                    change = int(price * factor)
                    new_price = max(100, price + change)
                    bonus = max(1, int(new_price * 0.02))
                    await cur.execute("UPDATE enterprises SET price=%s WHERE id=%s", (new_price, eid))
                    self._last_prices[eid] = new_price
                    await cur.execute("UPDATE users SET bank=bank+%s WHERE user_id=%s", (bonus, owner_id))
                    txid = secrets.token_hex(4)
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", owner_id, owner_id, bonus, "bank", "won"),
                    )
                    prev = price
                    delta = new_price - prev
                    pct = (delta / prev * 100.0) if prev > 0 else 0.0
                    try:
                        print(f"market update: {name} {self._fmt_amount(prev)} -> {self._fmt_amount(new_price)} ({pct:+.2f}%)")
                    except Exception:
                        pass
                    summaries.append((name, prev, new_price, delta, pct))
                    if ch and ctx_like:
                        try:
                            status = "↗︎ en hausse" if delta > 0 else ("↘︎ en baisse" if delta < 0 else "→ stable")
                            desc = (
                                f"Prix: {self._fmt_amount(prev)} → {self._fmt_amount(new_price)} {cur_emoji}\n"
                                f"Variation: {('+' if delta>0 else '')}{self._fmt_amount(delta)} ({pct:+.2f}%) • {status}\n\n"
                                f"Acheter/Vendre: utilise `/bourse {name}` pour voir tes parts et décider."
                            )
                            emb = self._bank_embed(ctx_like, title=f"Bourse • {name}", description=desc, color=discord.Color.orange())
                            await ch.send(embed=emb)
                        except Exception as e:
                            try:
                                print(f"bourse send error: {e}")
                            except Exception:
                                pass
                if ch and ctx_like and summaries:
                    try:
                        avg = sum(p for _, _, _, _, p in summaries) / len(summaries)
                        status = "↗︎ marché en forte hausse" if avg > 0 else ("↘︎ marché en forte baisse" if avg < 0 else "→ marché stable")
                        top = sorted(summaries, key=lambda t: abs(t[3]), reverse=True)[:10]
                        lines = [
                            f"{n}: {('+' if d>0 else '')}{self._fmt_amount(d)} ({p:+.2f}%)"
                            for n, _, _, d, p in top
                        ]
                        desc = f"{status}\n\n" + "\n".join(lines)
                        emb = self._bank_embed(ctx_like, title="Bourse • Mise à jour du marché", description=desc, color=discord.Color.red())
                        await ch.send(embed=emb)
                    except Exception as e:
                        try:
                            print(f"bourse summary error: {e}")
                        except Exception:
                            pass
                try:
                    await self.bot.tree.sync()
                except Exception:
                    pass
        try:
            print("market tick: end")
        except Exception:
            pass

    # système de bourse retiré


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
    tree = bot.tree

    class _SlashCtx:
        def __init__(self, interaction: discord.Interaction):
            self.author = interaction.user
            self.guild = interaction.guild

    @tree.command(name="balance", description="Voir le solde (poche+banque)")
    async def balance_slash(interaction: discord.Interaction, member: discord.Member | None = None):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); member = member or interaction.user; await cog._ensure_user(member.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (member.id,))
                bal, bank = await cur.fetchone()
        ctx = _SlashCtx(interaction)
        cur = cog._currency_emoji(ctx)
        emb = cog._bank_embed(ctx, title=f"Solde de {member.display_name}", color=discord.Color.gold(), fields=[("Poche", f"{bal} {cur}", True), ("Banque", f"{bank} {cur}", True)], actor=member)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="send", description="Envoyer de l’argent")
    async def send_slash(interaction: discord.Interaction, member: discord.Member, amount: int):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id); await cog._ensure_user(member.id)
        if amount <= 0:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                if bal < amount:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amount, interaction.user.id))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, member.id))
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        emb = cog._bank_embed(ctx, title="Virement", color=discord.Color.purple(), fields=[("De", interaction.user.mention, True), ("Vers", member.mention, True), ("Montant", f"{cog._fmt_amount(amount)} {cur_emoji}", True)], txn_id=cog._txn_id())
        await interaction.response.send_message(embed=emb)

    @tree.command(name="deposit", description="Déposer à la banque")
    async def deposit_slash(interaction: discord.Interaction, amount: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (interaction.user.id,))
                bal, bank = await cur.fetchone()
                try:
                    amt = bal if amount.lower() in ("all", "tout") else int(amount)
                except Exception:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                if amt <= 0:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                if bal < amt:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                bal -= amt; bank += amt
                await cur.execute("UPDATE users SET balance=%s, bank=%s WHERE user_id=%s", (bal, bank, interaction.user.id))
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        emb = cog._bank_embed(ctx, title="Dépôt", color=discord.Color.green(), fields=[("Montant", f"{cog._fmt_amount(amt)} {cur_emoji}", True), ("Opérateur", interaction.user.mention, True)], txn_id=cog._txn_id())
        await interaction.response.send_message(embed=emb)

    @tree.command(name="withdraw", description="Retirer de la banque")
    async def withdraw_slash(interaction: discord.Interaction, amount: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (interaction.user.id,))
                bal, bank = await cur.fetchone()
                try:
                    amt = bank if amount.lower() in ("all", "tout") else int(amount)
                except Exception:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                if amt <= 0:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                if bank < amt:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez à la banque.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                bank -= amt; bal += amt
                await cur.execute("UPDATE users SET balance=%s, bank=%s WHERE user_id=%s", (bal, bank, interaction.user.id))
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        emb = cog._bank_embed(ctx, title="Retrait", color=discord.Color.blue(), fields=[("Montant", f"{cog._fmt_amount(amt)} {cur_emoji}", True), ("Opérateur", interaction.user.mention, True)], txn_id=cog._txn_id())
        await interaction.response.send_message(embed=emb)

    @tree.command(name="shop", description="Voir le shop ou un item")
    async def shop_slash(interaction: discord.Interaction, item_name: str | None = None):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if item_name:
                    await cur.execute("SELECT item, buy_price, sell_price FROM shop WHERE item=%s", (item_name,))
                    row = await cur.fetchone()
                if not row:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Item introuvable.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                    item, buy, sell = row
                    ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
                    emb = cog._bank_embed(ctx, title=f"Infos {item}", color=discord.Color.teal(), fields=[("Prix d’achat", f"{buy} {cur_emoji}", True), ("Prix de vente", f"{sell} {cur_emoji}", True)], actor=interaction.user)
                    return await interaction.response.send_message(embed=emb)
                await cur.execute("SELECT item, buy_price, sell_price FROM shop ORDER BY buy_price ASC")
                rows = await cur.fetchall()
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        desc = "\n".join([f"{i} — buy {bp} / sell {sp} {cur_emoji}" for i, bp, sp in rows]) or "Shop vide."
        emb = cog._bank_embed(ctx, title="Shop", description=desc, color=discord.Color.teal())
        await interaction.response.send_message(embed=emb)

    @tree.command(name="buy", description="Acheter un item")
    async def buy_slash(interaction: discord.Interaction, item_name: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT buy_price FROM shop WHERE item=%s", (item_name,))
                row = await cur.fetchone()
                if not row:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Item introuvable.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                price = row[0]
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                if bal < price:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (price, interaction.user.id))
                if item_name == "protection":
                    try:
                        role = interaction.guild.get_role(PROTECTION_ROLE_ID) if interaction.guild else None
                        if role:
                            await interaction.user.add_roles(role, reason="Achat protection")
                    except Exception:
                        pass
                    await cur.execute("INSERT INTO inventory(user_id,item,qty) VALUES(%s,%s,1) ON DUPLICATE KEY UPDATE qty=1", (interaction.user.id, item_name))
                else:
                    await cur.execute("INSERT INTO inventory(user_id,item,qty) VALUES(%s,%s,1) ON DUPLICATE KEY UPDATE qty=qty+1", (interaction.user.id, item_name))
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        emb = cog._bank_embed(ctx, title="Achat", color=discord.Color.green(), fields=[("Article", item_name, True), ("Prix", f"{price} {cur_emoji}", True), ("Acheteur", interaction.user.mention, True)], txn_id=cog._txn_id(), actor=interaction.user)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="sell", description="Vendre un item")
    async def sell_slash(interaction: discord.Interaction, item_name: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT sell_price FROM shop WHERE item=%s", (item_name,))
                row = await cur.fetchone()
                if not row:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Item introuvable.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                price = row[0]
                await cur.execute("SELECT qty FROM inventory WHERE user_id=%s AND item=%s", (interaction.user.id, item_name))
                r = await cur.fetchone()
                qty = r[0] if r else 0
                if qty <= 0:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Tu n’as pas cet item.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                await cur.execute("UPDATE inventory SET qty=qty-1 WHERE user_id=%s AND item=%s", (interaction.user.id, item_name))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (price, interaction.user.id))
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        emb = cog._bank_embed(ctx, title="Vente", color=discord.Color.orange(), fields=[("Article", item_name, True), ("Prix", f"{price} {cur_emoji}", True), ("Vendeur", interaction.user.mention, True)], txn_id=cog._txn_id(), actor=interaction.user)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="inventory", description="Voir un inventaire")
    async def inventory_slash(interaction: discord.Interaction, member: discord.Member | None = None):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); member = member or interaction.user; await cog._ensure_user(member.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT item, qty FROM inventory WHERE user_id=%s AND qty>0 ORDER BY item", (member.id,))
                rows = await cur.fetchall()
        desc = "\n".join([f"{i} ×{q}" for i, q in rows]) or "Inventaire vide."
        emb = cog._bank_embed(_SlashCtx(interaction), title=f"Inventaire de {member.display_name}", description=desc, color=discord.Color.blurple(), actor=member)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="leaderboard", description="Top banque")
    async def leaderboard_slash(interaction: discord.Interaction):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT user_id, (balance+bank) AS total FROM users ORDER BY total DESC LIMIT 10")
                rows = await cur.fetchall()
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        desc = "\n".join([f"<@{uid}> — {total} {cur_emoji}" for uid, total in rows]) or "Aucun joueur."
        emb = cog._bank_embed(_SlashCtx(interaction), title="Classement Banque", description=desc, color=discord.Color.orange())
        await interaction.response.send_message(embed=emb)

    @tree.command(name="daily", description="Crédit quotidien")
    async def daily_slash(interaction: discord.Interaction):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        reward = 200
        now = dt.datetime.now()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT last_daily FROM users WHERE user_id=%s", (interaction.user.id,))
                row = await cur.fetchone()
                last = row[0] if row else None
                if last and last.date() == now.date():
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Crédit quotidien", color=discord.Color.red(), fields=[("Statut", "Déjà collecté aujourd'hui", False), ("Dernière", last.strftime("%Y-%m-%d %H:%M:%S"), False)])
                    return await interaction.response.send_message(embed=emb)
                await cur.execute("UPDATE users SET balance=balance+%s, last_daily=NOW() WHERE user_id=%s", (reward, interaction.user.id))
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        emb = cog._bank_embed(_SlashCtx(interaction), title="Crédit quotidien", color=discord.Color.green(), fields=[("Montant", f"+{cog._fmt_amount(reward)} {cur_emoji}", True), ("Bénéficiaire", interaction.user.mention, True)], txn_id=cog._txn_id(), actor=interaction.user)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="weekly", description="Crédit hebdo")
    async def weekly_slash(interaction: discord.Interaction):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        reward = 1000
        now = dt.datetime.now()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT last_weekly FROM users WHERE user_id=%s", (interaction.user.id,))
                row = await cur.fetchone()
                last = row[0] if row else None
                if last and (now - last).days < 7:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Crédit hebdomadaire", color=discord.Color.red(), fields=[("Statut", "Déjà collecté cette semaine", False), ("Dernière", last.strftime("%Y-%m-%d %H:%M:%S"), False)])
                    return await interaction.response.send_message(embed=emb)
                await cur.execute("UPDATE users SET balance=balance+%s, last_weekly=NOW() WHERE user_id=%s", (reward, interaction.user.id))
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        emb = cog._bank_embed(_SlashCtx(interaction), title="Crédit hebdomadaire", color=discord.Color.green(), fields=[("Montant", f"+{cog._fmt_amount(reward)} {cur_emoji}", True), ("Bénéficiaire", interaction.user.mention, True)], txn_id=cog._txn_id(), actor=interaction.user)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="monthly", description="Crédit mensuel")
    async def monthly_slash(interaction: discord.Interaction):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        reward = 4000
        now = dt.datetime.now()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT last_monthly FROM users WHERE user_id=%s", (interaction.user.id,))
                row = await cur.fetchone()
                last = row[0] if row else None
                if last and (now - last).days < 30:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Crédit mensuel", color=discord.Color.red(), fields=[("Statut", "Déjà collecté ce mois-ci", False), ("Dernière", last.strftime("%Y-%m-%d %H:%M:%S"), False)])
                    return await interaction.response.send_message(embed=emb)
                await cur.execute("UPDATE users SET balance=balance+%s, last_monthly=NOW() WHERE user_id=%s", (reward, interaction.user.id))
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        emb = cog._bank_embed(_SlashCtx(interaction), title="Crédit mensuel", color=discord.Color.green(), fields=[("Montant", f"+{cog._fmt_amount(reward)} {cur_emoji}", True), ("Bénéficiaire", interaction.user.mention, True)], txn_id=cog._txn_id(), actor=interaction.user)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="mines", description="Jeu Mines 5×5 avec mise")
    @app_commands.checks.cooldown(1, 5)
    async def mines_slash(interaction: discord.Interaction, amount: str, mines: int):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        try:
            if interaction.user.guild_permissions.administrator:
                pass
            else:
                # respect cooldown as defined above
                pass
        except Exception:
            pass
        if not (1 <= mines <= 24):
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Choisis un nombre de mines entre 1 et 24.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_user = (await cur.fetchone())[0]
        amt = cog._parse_bet_amount(str(amount), bal_user)
        if amt <= 0:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        if bal_user < amt:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, interaction.user.id))
        import random
        mines_set = set(random.sample(range(25), mines))
        session = {"bet": amt, "mines": mines, "mines_set": mines_set, "revealed": set(), "mult": 1.0, "ended": False}
        cog._mines_sessions[interaction.user.id] = session
        ctx_like = _SlashCtx(interaction)
        cur_emoji = cog._currency_emoji(ctx_like)
        desc = (
            f"Votre mise : {cog._fmt_amount(amt)} {cur_emoji} • Nombre de mines : {mines}\n"
            f"Cases révélées : 0 • Gain potentiel : {cog._fmt_amount(max(1, int(amt * 0.95)))} {cur_emoji}"
        )
        emb = cog._bank_embed(ctx_like, title="Casino • Mines", description=desc, color=discord.Color.blurple())
        view_grid = MinesView(cog, ctx_like, interaction.user.id)
        await interaction.response.send_message(embed=emb, view=view_grid)
        view_cash = MinesCashView(cog, ctx_like, interaction.user.id)
        cash_msg = await interaction.followup.send(view=view_cash)
        try:
            cog._mines_sessions[interaction.user.id]["cash_message_id"] = cash_msg.id
        except Exception:
            pass

    @tree.command(name="vol", description="Voler quelqu’un")
    @app_commands.checks.cooldown(1, 60*60)
    async def vol_slash(interaction: discord.Interaction, member: discord.Member):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id); await cog._ensure_user(member.id)
        try:
            if interaction.user.guild_permissions.administrator:
                pass
            else:
                # respect cooldown as defined above
                pass
        except Exception:
            pass
        if member.id == interaction.user.id:
            return await interaction.response.send_message("Tu ne peux pas te voler toi-même.")
        try:
            role = interaction.guild.get_role(PROTECTION_ROLE_ID) if interaction.guild else None
            if role and role in member.roles:
                emb = cog._bank_embed(_SlashCtx(interaction), title="Vol", color=discord.Color.red(), fields=[("Statut", "Protégé — vol impossible", False), ("Victime", member.mention, True)])
                return await interaction.response.send_message(embed=emb)
        except Exception:
            pass
        import random
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (member.id,))
                r = await cur.fetchone()
                if not r:
                    return await interaction.response.send_message("Victime inconnue.")
                victim_bal, victim_bank = r
                if victim_bal <= 0:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Vol", color=discord.Color.red(), fields=[("Statut", "Rien à voler (tout est à la banque)", False), ("Victime", member.mention, True)])
                    return await interaction.response.send_message(embed=emb)
                amount = random.randint(10, 100)
                amount = min(amount, victim_bal)
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amount, member.id))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, interaction.user.id))
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        emb = cog._bank_embed(_SlashCtx(interaction), title="Vol", color=discord.Color.dark_gold(), fields=[("Voleur", interaction.user.mention, True), ("Victime", member.mention, True), ("Montant", f"-{amount} {cur_emoji} pour la victime", False)], txn_id=cog._txn_id())
        await interaction.response.send_message(embed=emb)

    @tree.command(name="add_money", description="Crédit admin")
    @app_commands.default_permissions(administrator=True)
    async def add_money_slash(interaction: discord.Interaction, member: discord.Member, amount: int, mode: str | None = None):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(member.id)
        col = "bank" if (mode or "").lower() == "bank" else "balance"
        txid = cog._txn_id()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (txid, "credit", interaction.user.id, member.id, amount, col, "pending"),
                )
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        emb = cog._bank_embed(_SlashCtx(interaction), title="Crédit admin (en attente)", color=discord.Color.orange(), fields=[("Cible", member.mention, True), ("Montant", f"+{cog._fmt_amount(amount)} {cur_emoji}", True), ("Compte", col, True)], txn_id=txid)
        await interaction.response.send_message(embed=emb, view=AdminTransactionView(cog, txid))

    @tree.command(name="remove_money", description="Débit admin")
    @app_commands.default_permissions(administrator=True)
    async def remove_money_slash(interaction: discord.Interaction, member: discord.Member, amount: int, mode: str | None = None):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(member.id)
        col = "bank" if (mode or "").lower() == "bank" else "balance"
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"UPDATE users SET {col}={col}-%s WHERE user_id=%s", (amount, member.id))
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        emb = cog._bank_embed(_SlashCtx(interaction), title="Débit admin", color=discord.Color.red(), fields=[("Cible", member.mention, True), ("Montant", f"-{cog._fmt_amount(amount)} {cur_emoji}", True), ("Compte", col, True)])
        await interaction.response.send_message(embed=emb)

    @tree.command(name="reset_user", description="Reset complet utilisateur")
    @app_commands.default_permissions(administrator=True)
    async def reset_user_slash(interaction: discord.Interaction, member: discord.Member):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(member.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=0, bank=0 WHERE user_id=%s", (member.id,))
                await cur.execute("DELETE FROM inventory WHERE user_id=%s", (member.id,))
        await interaction.response.send_message(embed=discord.Embed(description=f"Reset complet de {member.mention}", color=discord.Color.dark_gray()))
    
    @tree.command(name="khedma", description="Travail et gagne 100 (CD géré côté +)")
    @app_commands.checks.cooldown(1, 5*60)
    async def khedma_slash(interaction: discord.Interaction):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        try:
            if interaction.user.guild_permissions.administrator:
                pass
            else:
                # respect cooldown as defined above
                pass
        except Exception:
            pass
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance+100 WHERE user_id=%s", (interaction.user.id,))
        ctx = _SlashCtx(interaction)
        cur = cog._currency_emoji(ctx)
        emb = cog._bank_embed(ctx, title="Khedma", description=f"+100 {cur}", color=discord.Color.green(), actor=interaction.user)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="scoot", description="Course scoot avec pari symétrique")
    @app_commands.checks.cooldown(1, 5)
    async def scoot_slash(interaction: discord.Interaction, membre: discord.Member, montant: int):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id); await cog._ensure_user(membre.id)
        if interaction.user.id == membre.id:
            return await interaction.response.send_message("Choisis quelqu’un d’autre.")
        if montant <= 0:
            return await interaction.response.send_message("Montant invalide.")
        view = ScootRaceView(cog, _SlashCtx(interaction), membre, montant)
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        emb = cog._bank_embed(_SlashCtx(interaction), title="Scoot", description=f"{interaction.user.mention} défie {membre.mention}. Mise: {montant} {cur_emoji} chacun.", color=discord.Color.blurple())
        await interaction.response.send_message(embed=emb, view=view)

    @tree.command(name="coinflip", description="Pile/Face avec mise")
    @app_commands.checks.cooldown(1, 5)
    async def coinflip_slash(interaction: discord.Interaction, side: str, amount: int):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        s = (side or "").lower()
        if s not in ("pile", "face"):
            return await interaction.response.send_message("Choisis 'pile' ou 'face'.")
        if amount <= 0:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        import random
        txid = None
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                if bal < amount:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                flip = random.choice(["pile", "face"])
                if flip == s:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, interaction.user.id))
                    txid = cog._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", interaction.user.id, interaction.user.id, amount, "balance", "won"),
                    )
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amount, interaction.user.id))
        ctx = _SlashCtx(interaction)
        cur = cog._currency_emoji(ctx)
        won = txid is not None
        desc = f"Coin flip: {flip}. {'Gagné +' + str(amount) if won else 'Perdu -' + str(amount)} {cur}"
        color = discord.Color.green() if won else discord.Color.red()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur2:
                await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_after = (await cur2.fetchone())[0]
        emb = cog._bank_embed(
            ctx,
            title="Casino • Coin Flip",
            description=desc,
            color=color,
            txn_id=txid,
            fields=[("Solde", f"{bal_after} {cur}", True)],
        )
        await interaction.response.send_message(embed=emb)

    @tree.command(name="slots", description="Machines à sous avec mise")
    @app_commands.checks.cooldown(1, 5)
    async def slots_slash(interaction: discord.Interaction, amount: int):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        if amount <= 0:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        import random
        reels = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
        txid = None
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                if bal < amount:
                    return await interaction.response.send_message("Pas assez en poche.")
                r = [random.choice(reels) for _ in range(3)]
                unique = len(set(r))
                if unique == 1:
                    win = amount * 8
                elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
                    win = int(amount * 1.8)
                else:
                    win = 0
                if win > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win, interaction.user.id))
                    txid = cog._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", interaction.user.id, interaction.user.id, win, "balance", "won"),
                    )
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amount, interaction.user.id))
        ctx = _SlashCtx(interaction)
        cur = cog._currency_emoji(ctx)
        color = discord.Color.green() if win > 0 else discord.Color.red()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur2:
                await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_after = (await cur2.fetchone())[0]
        outcome_line = f":tada: __**Vous avez gagné {win} {cur} Fcoins !**__" if win > 0 else f":x: **Vous avez perdu {amount} {cur} Fcoins**"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Résultats: {' | '.join(r)}\n\n{outcome_line}\n\nVotre solde s'estime à : **{bal_after} {cur} Fcoins**{extra_id}"
        emb = cog._bank_embed(ctx, title="Casino • Machines à sous", description=full_desc, color=color, txn_id=txid)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="dice", description="Pari pair/impair ou sur un chiffre")
    @app_commands.checks.cooldown(1, 5)
    async def dice_slash(interaction: discord.Interaction, amount: int, bet_on: int | None = None):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        if amount <= 0:
            return await interaction.response.send_message("Montant invalide.")
        if bet_on is not None and not (1 <= bet_on <= 6):
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Parie sur un nombre entre 1 et 6.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        import random
        txid = None
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                if bal < amount:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                roll = random.randint(1, 6)
                if bet_on is None:
                    if roll % 2 == 0:
                        win = amount
                    else:
                        win = -amount
                else:
                    if roll == bet_on:
                        win = amount * 5
                    else:
                        win = -amount
                if win > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win, interaction.user.id))
                    txid = cog._txn_id()
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", interaction.user.id, interaction.user.id, win, "balance", "won"),
                    )
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (-win, interaction.user.id))
        ctx = _SlashCtx(interaction)
        cur = cog._currency_emoji(ctx)
        color = discord.Color.green() if win > 0 else discord.Color.red()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur2:
                await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_after2 = (await cur2.fetchone())[0]
        gain_line = f":tada: __**Vous avez gagné {win} {cur} Fcoins !**__" if win > 0 else f":x: **Vous avez perdu {-win} {cur} Fcoins**"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Le dé est tombé sur : {roll} :game_die:\n\n{gain_line}\n\nVotre solde s'estime à : **{bal_after2} {cur} Fcoins**{extra_id}"
        emb = cog._bank_embed(ctx, title="Casino • Jeu du dé", description=full_desc, color=color, txn_id=txid)
        await interaction.response.send_message(embed=emb)

    # système d’entreprise retiré
    async def entreprise_slash(interaction: discord.Interaction, name: str):
        await interaction.response.send_message("Système d’entreprise retiré.")

    # système d’entreprise retiré
    async def investir_slash(interaction: discord.Interaction, name: str, amount: int):
        await interaction.response.send_message("Système d’entreprise retiré.")

    # système d’entreprise retiré
    async def vendre_parts_slash(interaction: discord.Interaction, name: str, qty: int):
        await interaction.response.send_message("Système d’entreprise retiré.")

    # système d’entreprise retiré
    async def entreprises_slash(interaction: discord.Interaction):
        await interaction.response.send_message("Système d’entreprise retiré.")

    # système d’entreprise retiré
    async def portefeuille_slash(interaction: discord.Interaction):
        await interaction.response.send_message("Système d’entreprise retiré.")

    @tree.command(name="tax", description="Taxer une transaction (owner)")
    async def tax_slash(interaction: discord.Interaction, txid: str):
        if interaction.user.id != 1443339902623154207:
            return await interaction.response.send_message("Non autorisé.")
        cog: Economy = bot.get_cog("Economy")
        await cog._connect()
        TAX_RATE = 0.05
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT target_id, amount, account, status, taxed FROM transactions WHERE id=%s", (txid,))
                row = await cur.fetchone()
                if not row:
                    return await interaction.response.send_message("Transaction introuvable.")
                target_id, amount, col, status, taxed = row
                if status not in ("accepted", "won"):
                    return await interaction.response.send_message("Transaction non taxable.")
                if taxed:
                    return await interaction.response.send_message("Taxe déjà appliquée.")
                tax_amt = max(1, int(amount * TAX_RATE))
                await cur.execute(f"SELECT {col} FROM users WHERE user_id=%s", (target_id,))
                avail = (await cur.fetchone())[0]
                tax_real = min(tax_amt, avail)
                if tax_real <= 0:
                    return await interaction.response.send_message("Rien à taxer.")
                await cur.execute(f"UPDATE users SET {col}={col}-%s WHERE user_id=%s", (tax_real, target_id))
                await cur.execute("UPDATE users SET bank=bank+%s WHERE user_id=%s", (tax_real, interaction.user.id))
                await cur.execute("UPDATE transactions SET taxed=1 WHERE id=%s", (txid,))
        await interaction.response.send_message(f"Taxe appliquée: {tax_real}")
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        try:
            if not hasattr(self, "_snipes"):
                self._snipes = {}
            self._snipes[message.channel.id] = {
                "author": message.author,
                "content": message.content,
                "created_at": message.created_at,
            }
        except Exception:
            pass

    @commands.command(name="snipe")
    async def snipe(self, ctx: commands.Context):
        await self._connect()
        data = getattr(self, "_snipes", {}).get(ctx.channel.id)
        if not data:
            return await ctx.send("Rien à snipe.")
        content = data.get("content") or "(vide)"
        author = data.get("author")
        emb = self._bank_embed(ctx, title="Snipe", description=content, color=discord.Color.dark_gray(), actor=author)
        await ctx.send(embed=emb)

    @commands.command(name="risk", help="Bande de Risque 1–100: +risk montant L-H (ex: +risk 300k 15-35)") 
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def risk(self, ctx: commands.Context, amount: str, band: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        try:
            parts = band.replace(" ", "").split("-")
            if len(parts) != 2: return await ctx.send("Bande invalide. Format L-H.")
            L = int(parts[0]); H = int(parts[1])
        except Exception:
            return await ctx.send("Bande invalide. Format L-H.")
        if not (1 <= L <= 100 and 1 <= H <= 100 and L <= H):
            return await ctx.send("Bande hors limites (1–100) ou inversée.")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(amount, bal_user)
        if amt <= 0:
            return await ctx.send("Montant invalide.")
        length = H - L + 1
        import random
        n = random.randint(1, 100)
        win = L <= n <= H
        house = 0.97
        payout = int(amt * (100 / length) * house) if win else 0
        txid = None
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if win:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (payout, ctx.author.id))
                    txid = self._txn_id()
                    await cur.execute("INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)", (txid, "win", ctx.author.id, ctx.author.id, payout, "balance", "won"))
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, ctx.author.id))
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self._currency_emoji(ctx)
        extra_id = f"\n\nID: {txid}" if txid else ""
        outcome_line = (
            f":tada: __**Vous avez gagné {self._fmt_amount(payout)} {cur_emoji} Fcoins !**__"
            if win else f":x: **Vous avez perdu {self._fmt_amount(amt)} {cur_emoji} Fcoins**"
        )
        full_desc = (
            f"Tirage: {n} • Bande choisie: [{L}-{H}] (longueur {length})\n\n"
            f"{outcome_line}\n\nVotre solde s'estime à : **{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**" + extra_id
        )
        color = discord.Color.green() if win else discord.Color.red()
        emb = self._bank_embed(ctx, title="Casino • Bande de Risque", description=full_desc, color=color, txn_id=txid)
        await ctx.send(embed=emb)

    @tree.command(name="risk", description="Bande de Risque 1–100")
    @app_commands.checks.cooldown(1, 5)
    async def risk_slash(interaction: discord.Interaction, amount: str, band: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        try:
            parts = band.replace(" ", "").split("-")
            if len(parts) != 2:
                return await interaction.response.send_message("Bande invalide. Format L-H.")
            L = int(parts[0]); H = int(parts[1])
        except Exception:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Bande invalide. Format L-H.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        if not (1 <= L <= 100 and 1 <= H <= 100 and L <= H):
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Bande hors limites (1–100) ou inversée.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_user = (await cur.fetchone())[0]
        amt = cog._parse_bet_amount(amount, bal_user)
        if amt <= 0:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        length = H - L + 1
        import random
        n = random.randint(1, 100)
        win = L <= n <= H
        house = 0.97
        payout = int(amt * (100 / length) * house) if win else 0
        txid = None
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if win:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (payout, interaction.user.id))
                    txid = cog._txn_id()
                    await cur.execute("INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)", (txid, "win", interaction.user.id, interaction.user.id, payout, "balance", "won"))
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, interaction.user.id))
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        extra_id = f"\n\nID: {txid}" if txid else ""
        outcome_line = (
            f":tada: __**Vous avez gagné {cog._fmt_amount(payout)} {cur_emoji} Fcoins !**__"
            if win else f":x: **Vous avez perdu {cog._fmt_amount(amt)} {cur_emoji} Fcoins**"
        )
        full_desc = (
            f"Tirage: {n} • Bande choisie: [{L}-{H}] (longueur {length})\n\n"
            f"{outcome_line}\n\nVotre solde s'estime à : **{cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**" + extra_id
        )
        color = discord.Color.green() if win else discord.Color.red()
        emb = cog._bank_embed(_SlashCtx(interaction), title="Casino • Bande de Risque", description=full_desc, color=color, txn_id=txid)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="ladder", description="Échelle Push Your Luck")
    @app_commands.checks.cooldown(1, 5)
    async def ladder_slash(interaction: discord.Interaction, amount: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_user = (await cur.fetchone())[0]
        amt = cog._parse_bet_amount(str(amount), bal_user)
        if amt <= 0:
            return await interaction.response.send_message("Montant invalide.")
        view = LadderView(cog, _SlashCtx(interaction), amt)
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        emb = cog._bank_embed(_SlashCtx(interaction), title="Casino • Échelle Push Your Luck", description=f"Mise initiale: **{cog._fmt_amount(amt)} {cur_emoji}**\nChoisis 'Continuer' pour augmenter ton gain ou 'Encaisser' pour récupérer ton gain actuel.", color=discord.Color.blurple())
        await interaction.response.send_message(embed=emb, view=view)

    # système de bourse retiré
    async def bourse_slash(interaction: discord.Interaction, name: str):
        await interaction.response.send_message("Système de bourse retiré.")
