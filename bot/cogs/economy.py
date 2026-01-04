import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiomysql
import os
import datetime as dt
import secrets
import re
import asyncio
import random
import io
from PIL import Image, ImageDraw, ImageFont
import plotly.graph_objects as go
from zoneinfo import ZoneInfo
from typing import Literal

CURRENCY_EMOJI = ":monnaie:"
PROTECTION_ROLE_ID = 1448414767533527153

DDL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        balance BIGINT NOT NULL DEFAULT 0,
        bank BIGINT NOT NULL DEFAULT 0,
        bank_2 BIGINT NOT NULL DEFAULT 0,
        bank_3 BIGINT NOT NULL DEFAULT 0,
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
    """
    CREATE TABLE IF NOT EXISTS settings (
        setting_key VARCHAR(64) PRIMARY KEY,
        setting_value VARCHAR(255)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS crypto_history (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        price DECIMAL(20, 8) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS user_properties (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        property_key VARCHAR(32) NOT NULL,
        last_collected TIMESTAMP NULL,
        INDEX idx_user_prop (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS user_luxury (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        item_key VARCHAR(32) NOT NULL,
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        serial_number INT DEFAULT 0,
        original_owner_id BIGINT DEFAULT NULL,
        INDEX idx_user_lux (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sender_id BIGINT NOT NULL,
        receiver_id BIGINT NOT NULL,
        amount BIGINT NOT NULL,
        reason VARCHAR(255),
        status VARCHAR(16) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_inv_recv (receiver_id),
        INDEX idx_inv_send (sender_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
]

# --- REAL ESTATE DATA ---
PROPERTIES = {
    "studio": {"name": "Studio miteux", "price": 50_000, "income": 500, "emoji": "🏚️", "desc": "Un petit trou à rat, mais c'est chez toi."},
    "appartement": {"name": "Appartement Centre", "price": 200_000, "income": 2_500, "emoji": "🏢", "desc": "Un T3 sympa en centre-ville."},
    "maison": {"name": "Maison de Banlieue", "price": 1_000_000, "income": 15_000, "emoji": "🏡", "desc": "Jardin, garage et barbecue le dimanche."},
    "villa": {"name": "Villa de Luxe", "price": 5_000_000, "income": 80_000, "emoji": "🌴", "desc": "Piscine à débordement et vue sur la mer."},
    "immeuble": {"name": "Gratte-ciel", "price": 20_000_000, "income": 350_000, "emoji": "🏙️", "desc": "Tu possèdes la skyline. Le patron."}
}

# --- LUXURY SHOP DATA ---
LUXURY_ITEMS = {
    "rolex": {"name": "Montre en Or", "price": 20_000, "emoji": "⌚", "type": "Accessoire"},
    "sac": {"name": "Sac de Luxe", "price": 15_000, "emoji": "👜", "type": "Accessoire"},
    "costume": {"name": "Costume Sur-Mesure", "price": 10_000, "emoji": "👔", "type": "Vêtement"},
    "sportcar": {"name": "Voiture de Sport", "price": 150_000, "emoji": "🏎️", "type": "Véhicule"},
    "supercar": {"name": "Supercar", "price": 2_000_000, "emoji": "🚀", "type": "Véhicule"},
    "yacht": {"name": "Yacht Privé", "price": 10_000_000, "emoji": "🛥️", "type": "Véhicule"},
    "jet": {"name": "Jet Privé", "price": 50_000_000, "emoji": "✈️", "type": "Véhicule"},
    "island": {"name": "Île Privée", "price": 500_000_000, "emoji": "🏝️", "type": "Immobilier"}
}

# --- CONSTANTS ---
BANK_TIERS = {
    0: {"limit": 2_500, "price": 0, "name": "Compte Épargne Junior"},
    1: {"limit": 20_000, "price": 10_000, "name": "Compte Standard"},
    2: {"limit": 100_000, "price": 50_000, "name": "Compte Premium"},
    3: {"limit": 500_000, "price": 200_000, "name": "Compte Gold"},
    4: {"limit": 2_000_000, "price": 1_000_000, "name": "Compte Platinum"},
    5: {"limit": 10_000_000, "price": 5_000_000, "name": "Compte Black (Offshore)"}
}
SUSPICIOUS_THRESHOLD = 50_000

# Nouvelle fonction utilitaire pour le formatage abrégé et complet
def format_currency_abbr(n: int) -> str:
    """
    Abrège le nombre (ex: 1800000 -> 1.8m) et ajoute le nombre entier
    formaté avec des points comme séparateur de milliers entre parenthèses.
    Exemple: 1.8m (1.800.000)
    
    Mis à jour pour inclure les nombres au-delà du Billion (Quadrillions, etc.).
    """
    if not isinstance(n, int):
        try:
            n = int(n)
        except (ValueError, TypeError):
            return "0 (0)"
        
    abs_n = abs(n)
    
    # Formatage de la partie entière avec points comme séparateur de milliers
    full_str = f"{abs_n:,}".replace(",", ".")

    if abs_n < 1000:
        abbr_str = full_str
    elif abs_n < 1_000_000:
        # Milliers (k)
        value = abs_n / 1000
        abbr_str = f"{value:.1f}".rstrip('0').rstrip('.') + 'k'
    elif abs_n < 1_000_000_000:
        # Millions (m)
        value = abs_n / 1_000_000
        abbr_str = f"{value:.1f}".rstrip('0').rstrip('.') + 'm'
    elif abs_n < 1_000_000_000_000:
        # Milliards (b)
        value = abs_n / 1_000_000_000
        abbr_str = f"{value:.1f}".rstrip('0').rstrip('.') + 'b'
    elif abs_n < 1_000_000_000_000_000:
        # Billions (t pour Trillions)
        value = abs_n / 1_000_000_000_000
        abbr_str = f"{value:.1f}".rstrip('0').rstrip('.') + 't'
    elif abs_n < 1_000_000_000_000_000_000:
        # Quadrillions (q)
        value = abs_n / 1_000_000_000_000_000
        abbr_str = f"{value:.1f}".rstrip('0').rstrip('.') + 'q'
    else:
        # Plus grand (Quintillions et au-delà, on utilise le format entier)
        abbr_str = full_str

    # Construction de la chaîne finale (avec le signe si négatif)
    final_str = f"{abbr_str} ({full_str})"
    return f"-{final_str}" if n < 0 else final_str


class BalanceView(discord.ui.View):
    def __init__(self, ctx, member, bal, bank1, bank2, bank3, fcoin, cur_emoji, cog):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.member = member
        self.bal = bal
        self.bank1 = bank1
        self.bank2 = bank2
        self.bank3 = bank3
        self.fcoin = fcoin
        self.cur = cur_emoji
        self.cog = cog
        
        # Determine available banks (if balance > 0)
        # Note: User request: "faut pas que par défaut ça affiche 'banque 1, 2 et 3' alors que l'user les a pas forcément"
        # Logic: Always show Main Bank (1). Show 2 & 3 only if they have funds OR if explicitly requested via button click?
        # Better: Show buttons for all, but embed only shows active one.
        
        # Default view: Overview (Poche + Main Bank)
        self.current_view = "main"
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        # Main Button
        btn_main = discord.ui.Button(label="Principal", style=discord.ButtonStyle.primary if self.current_view == "main" else discord.ButtonStyle.secondary)
        btn_main.callback = self.show_main
        self.add_item(btn_main)
        
        # Bank 2 Button (Only if used or navigation)
        # Showing button allows user to check even if 0
        btn_b2 = discord.ui.Button(label="Banque 2", style=discord.ButtonStyle.primary if self.current_view == "bank2" else discord.ButtonStyle.secondary)
        btn_b2.callback = self.show_bank2
        self.add_item(btn_b2)

        # Bank 3 Button
        btn_b3 = discord.ui.Button(label="Banque 3", style=discord.ButtonStyle.primary if self.current_view == "bank3" else discord.ButtonStyle.secondary)
        btn_b3.callback = self.show_bank3
        self.add_item(btn_b3)

    async def show_main(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: return await interaction.response.send_message("Tu n'es pas le propriétaire de ce compte.", ephemeral=True)
        self.current_view = "main"
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def show_bank2(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: return await interaction.response.send_message("Tu n'es pas le propriétaire de ce compte.", ephemeral=True)
        self.current_view = "bank2"
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def show_bank3(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author: return await interaction.response.send_message("Tu n'es pas le propriétaire de ce compte.", ephemeral=True)
        self.current_view = "bank3"
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def get_embed(self):
        emb = self.cog._bank_embed(
            self.ctx,
            title=f"Solde de {self.member.display_name}",
            color=discord.Color.gold(),
            actor=self.member
        )
        
        # Poche is always visible
        emb.add_field(name="Poche", value=f"{self.cog._fmt_amount(self.bal)} {self.cur}", inline=True)
        
        if self.current_view == "main":
            emb.add_field(name="Banque 1", value=f"{self.cog._fmt_amount(self.bank1)} {self.cur}", inline=True)
            if self.bank2 > 0 or self.bank3 > 0:
                 emb.set_footer(text="D'autres fonds disponibles en Banque 2/3")
        elif self.current_view == "bank2":
            emb.add_field(name="Banque 2", value=f"{self.cog._fmt_amount(self.bank2)} {self.cur}", inline=True)
        elif self.current_view == "bank3":
            emb.add_field(name="Banque 3", value=f"{self.cog._fmt_amount(self.bank3)} {self.cur}", inline=True)
            
        return emb


class InvoiceView(discord.ui.View):
    def __init__(self, ctx, inv_id, amount, sender_id, cog):
        super().__init__(timeout=600) # 10 minutes
        self.ctx = ctx
        self.inv_id = inv_id
        self.amount = amount
        self.sender_id = sender_id
        self.cog = cog

    @discord.ui.button(label="✅ Payer", style=discord.ButtonStyle.green)
    async def pay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # We need to call the payfacture command logic or reimplement it.
        # Calling the command is cleaner if possible, but context is different (Interaction).
        # Let's reimplement logic for speed and cleaner interaction response.
        
        await interaction.response.defer()
        
        # Security checks
        await self.cog._connect()
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Re-check invoice status
                await cur.execute("SELECT status FROM invoices WHERE id=%s", (self.inv_id,))
                res = await cur.fetchone()
                if not res:
                    return await interaction.followup.send("❌ Facture introuvable.", ephemeral=True)
                if res[0] != 'pending':
                    return await interaction.followup.send(f"❌ Facture déjà {res[0]}.", ephemeral=True)
                
                # Check Balance
                await cur.execute("SELECT balance, bank, bank_2, bank_3 FROM users WHERE user_id=%s", (interaction.user.id,))
                res = await cur.fetchone()
                if not res:
                    return await interaction.followup.send("❌ Erreur compte utilisateur.", ephemeral=True)
                bal, b1, b2, b3 = res
                total_wealth = bal + b1 + b2 + b3
                
                if total_wealth < self.amount:
                    return await interaction.followup.send("❌ Fonds insuffisants.", ephemeral=True)
                
                # Deduct
                remaining = self.amount
                new_bal, new_b1, new_b2, new_b3 = bal, b1, b2, b3
                
                if new_bal >= remaining: new_bal -= remaining; remaining = 0
                else: remaining -= new_bal; new_bal = 0
                if remaining > 0 and new_b1 >= remaining: new_b1 -= remaining; remaining = 0
                elif remaining > 0: remaining -= new_b1; new_b1 = 0
                if remaining > 0 and new_b2 >= remaining: new_b2 -= remaining; remaining = 0
                elif remaining > 0: remaining -= new_b2; new_b2 = 0
                if remaining > 0 and new_b3 >= remaining: new_b3 -= remaining; remaining = 0
                elif remaining > 0: remaining -= new_b3; new_b3 = 0
                
                # Update Payer
                await cur.execute(
                    "UPDATE users SET balance=%s, bank=%s, bank_2=%s, bank_3=%s WHERE user_id=%s",
                    (new_bal, new_b1, new_b2, new_b3, interaction.user.id)
                )
                
                # Update Receiver
                await cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (self.amount, self.sender_id))
                
                # Update Invoice
                await cur.execute("UPDATE invoices SET status='paid' WHERE id=%s", (self.inv_id,))
                
                # Log
                is_suspect = 1 if self.amount >= SUSPICIOUS_THRESHOLD else 0
                await cur.execute(
                    "INSERT INTO transactions (type, requester_id, target_id, amount, account, status, is_suspect) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    ('invoice', interaction.user.id, self.sender_id, self.amount, 'mix', 'success', is_suspect)
                )
                
        await interaction.followup.send(f"✅ Facture #{self.inv_id} payée avec succès !")
        self.stop()
        # Disable buttons
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.red)
    async def refuse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.cog._connect()
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE invoices SET status='refused' WHERE id=%s", (self.inv_id,))
        
        await interaction.followup.send(f"🚫 Facture #{self.inv_id} refusée.")
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pool: aiomysql.Pool | None = None
        self._last_prices: dict[int, int] = {}
        self._prev_prices: dict[int, int] = {}
        self._fmt_cache: dict[int, str] = {}
        self._mines_sessions: dict[int, dict] = {}
        self._slash_cds: dict[str, dict[int, float]] = {}
        # Cache pour les sessions de blackjack
        self._blackjack_sessions: dict[int, 'BlackjackGame'] = {}
        self._roulette_sessions: dict[int, dict] = {}
        self.logs_enabled = True # Default
        self.illegal_cooldowns = commands.CooldownMapping.from_cooldown(1, 3600, commands.BucketType.user)

    async def _connect(self):
        if self.pool:
            return
        host = os.getenv("DB_HOST", "127.0.0.1")
        db = os.getenv("DB_NAME", "bot_fazer")
        user = os.getenv("DB_USER", "botfazer")
        pwd = os.getenv("DB_PASSWORD", "")
        try:
            print(f"[DEBUG] Connecting to DB {host} as {user}...")
            self.pool = await aiomysql.create_pool(
                host=host, db=db, user=user, password=pwd, autocommit=True, minsize=1, maxsize=10
            )
            print("[DEBUG] DB Connected successfully.")
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for sql in DDL:
                        await cur.execute(sql)
                    
                    # --- MIGRATIONS (Fixes pour tables existantes) ---
                    try:
                        await cur.execute("ALTER TABLE user_luxury ADD COLUMN serial_number INT DEFAULT 0")
                    except Exception:
                        pass
                    try:
                        await cur.execute("ALTER TABLE user_luxury ADD COLUMN original_owner_id BIGINT DEFAULT NULL")
                    except Exception:
                        pass
                    try:
                        await cur.execute("ALTER TABLE users ADD COLUMN bank_tier INT DEFAULT 0")
                    except Exception:
                        pass
                    try:
                        await cur.execute("ALTER TABLE transactions ADD COLUMN is_suspect TINYINT DEFAULT 0")
                    except Exception:
                        pass
                    
                    # Load settings
                    await cur.execute("SELECT setting_value FROM settings WHERE setting_key='logs_enabled'")
                    row = await cur.fetchone()
                    if row:
                        self.logs_enabled = (row[0] == "1")
                    else:
                        # Insert default
                        await cur.execute("INSERT INTO settings(setting_key, setting_value) VALUES('logs_enabled', '1')")
                        self.logs_enabled = True
        except Exception as e:
            print(f"[ERROR] DB Connection failed: {e}")
            self.pool = None
            raise e

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
        # Utilise la nouvelle fonction utilitaire de formatage
        # Note: La gestion du cache est simplifiée car format_currency_abbr est rapide
        # self._fmt_cache.clear() # Commenté pour éviter le clear systématique qui nuit au cache
        # if n in self._fmt_cache:
        #     return self._fmt_cache[n]
        out = format_currency_abbr(n)
        # self._fmt_cache[n] = out
        return out

    # Mise à jour de _parse_bet_amount pour inclure les milliards et plus (b, t, q)
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
        elif s.endswith("b"): # Milliards
            mult = 1_000_000_000
            s = s[:-1]
        elif s.endswith("t"): # Billions
            mult = 1_000_000_000_000
            s = s[:-1]
        elif s.endswith("q"): # Quadrillions
            mult = 1_000_000_000_000_000
            s = s[:-1]

        # Suppression des séparateurs de milliers potentiels (point ou virgule)
        s = re.sub(r"[\.,_]", "", s)
        try:
            # Gérer les décimales si elles existent avant le suffixe (ex: 1.5m)
            if '.' in s:
                return int(float(s) * mult)
            return int(s) * mult
        except Exception:
            return 0

    async def cog_load(self):
        try:
            await self._connect()
        except Exception:
            return
        # système de bourse retiré pcq fdp
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
                    # s zbi
        except Exception:
            pass

        try:
            self._daily_reset_task.start()
            self._daily_tax_task.start()
            self._crypto_update_task.start()
        except Exception:
            pass

    def cog_unload(self):
        try:
            self._daily_reset_task.cancel()
            self._daily_tax_task.cancel()
            self._crypto_update_task.cancel()
        except Exception:
            pass

    @tasks.loop(time=dt.time(hour=6, minute=0, tzinfo=ZoneInfo("Europe/Paris")))
    async def _daily_reset_task(self):
        try:
            await self._connect()
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Reset balance (poche) à 0 chaque jour. Les banques ne sont PAS reset.
                    await cur.execute("UPDATE users SET balance=0")
        except Exception:
            pass

    @tasks.loop(time=dt.time(hour=6, minute=5, tzinfo=ZoneInfo("Europe/Paris")))
    async def _daily_tax_task(self):
        try:
            await self._connect()
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Appliquer une taxe quotidienne de 2% sur les banques
                    await cur.execute("""
                        UPDATE users 
                        SET bank = FLOOR(bank * 0.98),
                            bank_2 = FLOOR(bank_2 * 0.98),
                            bank_3 = FLOOR(bank_3 * 0.98)
                    """)
        except Exception:
            pass

    @tasks.loop(seconds=10)
    async def _crypto_update_task(self):
        try:
            await self._connect()
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Get current price
                    await cur.execute("SELECT price FROM crypto_history ORDER BY created_at DESC LIMIT 1")
                    row = await cur.fetchone()
                    current_price = float(row[0]) if row else 1.25

                    # Check for inflation (credits in last minute)
                    await cur.execute("SELECT SUM(amount) FROM transactions WHERE type='credit' AND created_at >= NOW() - INTERVAL 1 MINUTE")
                    res = await cur.fetchone()
                    recent_credits = float(res[0]) if res and res[0] else 0

                    volatility = 0.02
                    bias = 0

                    if recent_credits > 5000:
                        volatility = 0.05
                        bias = -0.01
                        if recent_credits > 50000:
                            volatility = 0.15
                            bias = -0.05
                    
                    change = random.uniform(-volatility, volatility) + bias
                    new_price = max(0.1, current_price * (1 + change))
                    
                    await cur.execute("INSERT INTO crypto_history(price) VALUES(%s)", (new_price,))
                    
                    # Cleanup old history periodically
                    if random.random() < 0.01:
                         await cur.execute("DELETE FROM crypto_history WHERE created_at < NOW() - INTERVAL 24 HOUR")
        except Exception:
            pass

    async def _ensure_user(self, uid: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT IGNORE INTO users(user_id) VALUES(%s)", (uid,))

    # Bank commands
    @commands.command(name="toggle_logs")
    @commands.has_permissions(administrator=True)
    async def toggle_logs(self, ctx: commands.Context, mode: str):
        """Active ou désactive les logs d'argent dans la base de données (on/off)."""
        await self._connect()
        if mode.lower() == "on":
            val = "1"
            self.logs_enabled = True
            msg = "Logs d'argent activés."
        elif mode.lower() == "off":
            val = "0"
            self.logs_enabled = False
            msg = "Logs d'argent désactivés."
        else:
            return await ctx.send("Usage: +toggle_logs <on/off>")
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT INTO settings(setting_key, setting_value) VALUES('logs_enabled', %s) ON DUPLICATE KEY UPDATE setting_value=%s", (val, val))
        
        await ctx.send(msg)


    @commands.command(name="work", aliases=["w"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def work(self, ctx: commands.Context):
        """Travailler pour gagner un peu d'argent."""
        await self._connect(); await self._ensure_user(ctx.author.id)
        
        earnings = random.randint(50, 200)
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (earnings, ctx.author.id))
                
                # Log (Optional for small amounts, but consistent)
                if self.logs_enabled:
                     await cur.execute(
                        "INSERT INTO transactions (type, requester_id, target_id, amount, account, status) VALUES (%s, %s, %s, %s, %s, %s)",
                        ('work', ctx.author.id, ctx.author.id, earnings, 'cash', 'success')
                    )
        
        await ctx.send(f"🔨 Vous avez travaillé et gagné **{self._fmt_amount(earnings)}** {self._currency_emoji(ctx)}.")

    @commands.command(name="braquage")
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def braquage(self, ctx: commands.Context, target: discord.Member):
        """(Illégal) Tenter de braquer un joueur."""
        if target.bot or target.id == ctx.author.id:
            return await ctx.send("❌ Cible invalide.")
        
        await self._connect(); await self._ensure_user(ctx.author.id); await self._ensure_user(target.id)
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Check target balance
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (target.id,))
                t_bal = (await cur.fetchone())[0]
                
                if t_bal < 100:
                    return await ctx.send(f"❌ {target.display_name} est trop pauvre pour être braqué.")
                
                # 30% Success Rate
                if random.random() < 0.3:
                    # Success: Steal 10-50% of cash
                    percent = random.uniform(0.1, 0.5)
                    steal_amt = int(t_bal * percent)
                    
                    # Update balances
                    await cur.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s", (steal_amt, target.id))
                    await cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (steal_amt, ctx.author.id))
                    
                    # Log
                    await cur.execute(
                        "INSERT INTO transactions (type, requester_id, target_id, amount, account, status, is_suspect) VALUES (%s, %s, %s, %s, %s, %s, 1)",
                        ('robbery_success', ctx.author.id, target.id, steal_amt, 'cash', 'success')
                    )
                    
                    await ctx.send(f"🔫 **Braquage Réussi !** Vous avez volé {self._fmt_amount(steal_amt)} {self._currency_emoji(ctx)} à {target.mention} !")
                else:
                    # Fail: Pay fine (10% of own cash or 500 min)
                    await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                    own_bal = (await cur.fetchone())[0]
                    fine = max(500, int(own_bal * 0.1))
                    
                    if own_bal < fine: fine = own_bal # Take all if poor
                    
                    await cur.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s", (fine, ctx.author.id))
                    
                    # Log
                    await cur.execute(
                        "INSERT INTO transactions (type, requester_id, target_id, amount, account, status, is_suspect) VALUES (%s, %s, %s, %s, %s, %s, 1)",
                        ('robbery_fail', ctx.author.id, target.id, fine, 'cash', 'fail')
                    )
                    
                    await ctx.send(f"👮 **Échec !** La police vous a attrapé. Amende : {self._fmt_amount(fine)} {self._currency_emoji(ctx)}.")

    @commands.command(name="gofast")
    @commands.cooldown(1, 7200, commands.BucketType.user)
    async def gofast(self, ctx: commands.Context):
        """(Illégal) Faire un Go-Fast (Risqué)."""
        await self._connect(); await self._ensure_user(ctx.author.id)
        
        # Scenario
        scenarios = [
            {"msg": "🏎️ Vous foncez sur l'autoroute avec la cargaison...", "risk": 0.2, "reward": (5000, 15000)},
            {"msg": "🚤 Vous traversez la frontière en hors-bord...", "risk": 0.4, "reward": (10000, 30000)},
            {"msg": "✈️ Vous pilotez un avion rase-mottes...", "risk": 0.6, "reward": (25000, 80000)},
        ]
        
        chosen = random.choice(scenarios)
        msg = await ctx.send(f"{chosen['msg']} (Simulation en cours...)")
        await asyncio.sleep(3)
        
        if random.random() > chosen['risk']:
            # Success
            reward = random.randint(*chosen['reward'])
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (reward, ctx.author.id))
                    # Log
                    await cur.execute(
                        "INSERT INTO transactions (type, requester_id, target_id, amount, account, status, is_suspect) VALUES (%s, %s, %s, %s, %s, %s, 1)",
                        ('gofast_success', ctx.author.id, ctx.author.id, reward, 'cash', 'success')
                    )
            await msg.edit(content=f"✅ **Succès !** La livraison est arrivée à bon port. Gain : {self._fmt_amount(reward)} {self._currency_emoji(ctx)}")
        else:
            # Fail
            fine = random.randint(1000, 5000)
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s", (fine, ctx.author.id))
                    # Log
                    await cur.execute(
                        "INSERT INTO transactions (type, requester_id, target_id, amount, account, status, is_suspect) VALUES (%s, %s, %s, %s, %s, %s, 1)",
                        ('gofast_fail', ctx.author.id, ctx.author.id, fine, 'cash', 'fail')
                    )
            await msg.edit(content=f"🚓 **Interception !** La douane vous a coincé. Vous perdez la cargaison et payez {self._fmt_amount(fine)} {self._currency_emoji(ctx)} d'avocat.")

    def _draw_credit_card_sync(self, user_name, user_id, bal, bank1, bank2, bank3, assets_val):
        # Create base card image (Dark Gold/Black Gradient simulation)
        width, height = 600, 350
        image = Image.new('RGB', (width, height), color=(20, 20, 20))
        draw = ImageDraw.Draw(image)
        
        # Background Gradient (Fake)
        for y in range(height):
            r = int(20 + (y / height) * 30)
            g = int(20 + (y / height) * 30)
            b = int(25 + (y / height) * 40)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
            
        # Border
        draw.rectangle([(10, 10), (width-10, height-10)], outline=(212, 175, 55), width=5) # Gold border
        
        # Chip (Fake)
        draw.rectangle([(50, 100), (110, 150)], fill=(212, 175, 55), outline=(0,0,0))
        draw.line([(80, 100), (80, 150)], fill=(0,0,0), width=1)
        draw.line([(50, 125), (110, 125)], fill=(0,0,0), width=1)

        # Text
        try:
            # Try load font, fallback to default
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except:
            font_large = ImageFont.load_default()
            font_med = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Bank Name
        draw.text((width-250, 30), "MRO BANK", fill=(255, 255, 255), font=font_large)
        
        # Card Number (Fake)
        card_num = f"4921  {str(user_id)[:4]}  {str(user_id)[4:8]}  {str(user_id)[8:12]}"
        draw.text((50, 180), card_num, fill=(240, 240, 240), font=font_med)
        
        # Holder Name
        draw.text((50, 280), user_name.upper(), fill=(255, 255, 255), font=font_med)
        
        # Exp Date
        draw.text((450, 260), "VALID THRU", fill=(200, 200, 200), font=font_small)
        draw.text((450, 285), "12/99", fill=(255, 255, 255), font=font_med)

        # Balances (Right Side List)
        # Using simple format_currency_abbr from global scope or reimplement small logic
        def fmt(n):
            if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
            if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
            if n >= 1_000: return f"{n/1_000:.1f}k"
            return str(n)

        # Draw Balances on Card (Bottom Right overlay or similar? maybe too crowded)
        # Let's put total wealth top left
        total = bal + bank1 + bank2 + bank3
        draw.text((50, 40), f"WEALTH: ${fmt(total)}", fill=(212, 175, 55), font=font_small)

        # Save
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    @commands.command(name="card", aliases=["carte"])
    async def card(self, ctx: commands.Context, member: discord.Member | None = None):
        member = member or ctx.author
        await self._connect(); await self._ensure_user(member.id)
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank, bank_2, bank_3 FROM users WHERE user_id=%s", (member.id,))
                res = await cur.fetchone()
                if not res: res = (0, 0, 0, 0)
                bal, bank1, bank2, bank3 = res
                
                # Get Assets Value
                assets_val = 0
                # Real Estate
                await cur.execute("SELECT property_key FROM user_properties WHERE user_id=%s", (member.id,))
                props = await cur.fetchall()
                for p in props:
                    if p[0] in PROPERTIES: assets_val += PROPERTIES[p[0]]['price']
                
                # Luxury
                await cur.execute("SELECT item_key FROM user_luxury WHERE user_id=%s", (member.id,))
                luxs = await cur.fetchall()
                for l in luxs:
                    if l[0] in LUXURY_ITEMS: assets_val += LUXURY_ITEMS[l[0]]['price']
        
        # Run sync drawing in executor
        buf = await self.bot.loop.run_in_executor(
            None, 
            self._draw_credit_card_sync, 
            member.display_name, 
            member.id, 
            bal, 
            bank1, 
            bank2, 
            bank3,
            assets_val
        )
        
        file = discord.File(buf, filename="credit_card.png")
        await ctx.send(f"Voici la carte de {member.mention}", file=file)

    @commands.command(name="balance", aliases=["bal"]) 
    async def balance(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._connect(); member = member or ctx.author; await self._ensure_user(member.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank, bank_2, bank_3 FROM users WHERE user_id=%s", (member.id,))
                res = await cur.fetchone()
                if not res: res = (0, 0, 0, 0)
                bal, bank1, bank2, bank3 = res
        
        cur_emoji = self._currency_emoji(ctx)
        
        # Check if View is needed (if user has money in other banks)
        # User requested buttons anyway.
        
        view = BalanceView(ctx, member, bal, bank1, bank2, bank3, 0.0, cur_emoji, self)
        await ctx.send(embed=view.get_embed(), view=view)

    @commands.command(name="depobank", aliases=["db"])
    async def depobank(self, ctx: commands.Context, bank_id: int, amount: str):
        if bank_id not in (1, 2, 3):
            emb = self._bank_embed(ctx, title="Erreur", description="Banque invalide. Utilisez 1, 2 ou 3.", color=discord.Color.red())
            return await ctx.send(embed=emb)
        
        await self._connect(); await self._ensure_user(ctx.author.id)
        
        col_name = "bank" if bank_id == 1 else f"bank_{bank_id}"
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT balance, bank_tier, {col_name} FROM users WHERE user_id=%s", (ctx.author.id,))
                res = await cur.fetchone()
                bal, tier, current_bank = res
                
                amt = self._parse_bet_amount(amount, bal)
                if amt <= 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                
                # Check Tier Limit
                limit = BANK_TIERS.get(tier, BANK_TIERS[0])["limit"]
                if current_bank + amt > limit:
                    space = limit - current_bank
                    emb = self._bank_embed(
                        ctx, 
                        title="Plafond Atteint", 
                        description=f"❌ Votre palier ({BANK_TIERS.get(tier, {}).get('name', 'Inconnu')}) est limité à {self._fmt_amount(limit)} {self._currency_emoji(ctx)}.\nEspace libre : {self._fmt_amount(space)}.", 
                        color=discord.Color.red()
                    )
                    emb.set_footer(text="Utilisez +upgrade_bank pour augmenter votre plafond.")
                    return await ctx.send(embed=emb)

                # Atomic Transaction: Update only if balance >= amount
                await cur.execute(
                    f"UPDATE users SET balance = balance - %s, {col_name} = {col_name} + %s WHERE user_id=%s AND balance >= %s",
                    (amt, amt, ctx.author.id, amt)
                )
                
                if cur.rowcount == 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Pas assez en poche (ou transaction échouée).", color=discord.Color.red())
                    return await ctx.send(embed=emb)

                # Fetch new values for display
                await cur.execute(f"SELECT balance, {col_name} FROM users WHERE user_id=%s", (ctx.author.id,))
                new_bal, new_bank = await cur.fetchone()
                
                # Log Suspect
                if amt >= SUSPICIOUS_THRESHOLD:
                     await cur.execute(
                        "INSERT INTO transactions (type, requester_id, target_id, amount, account, status, is_suspect) VALUES (%s, %s, %s, %s, %s, %s, 1)",
                        ('deposit', ctx.author.id, ctx.author.id, amt, f'bank_{bank_id}', 'success')
                    )

        
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title=f"Dépôt Banque {bank_id}",
            color=discord.Color.green(),
            fields=[
                ("Montant", f"{self._fmt_amount(amt)} {cur}", True),
                ("Nouveau Solde Banque", f"{self._fmt_amount(new_bank)} {cur}", True),
            ],
            txn_id=self._txn_id(),
        )
        await ctx.send(embed=emb)

    @commands.command(name="upgrade_bank", aliases=["upbank"])
    async def upgrade_bank(self, ctx: commands.Context, tier_choice: int | None = None):
        """Améliorer son compte bancaire pour augmenter le plafond."""
        await self._connect(); await self._ensure_user(ctx.author.id)
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT bank_tier, balance FROM users WHERE user_id=%s", (ctx.author.id,))
                current_tier, bal = await cur.fetchone()
                
                if tier_choice is None:
                    # Show Menu
                    desc = f"**Votre Palier Actuel :** {BANK_TIERS.get(current_tier, {}).get('name')} (Max {self._fmt_amount(BANK_TIERS.get(current_tier, {}).get('limit'))})\n\n"
                    desc += "**Paliers Disponibles :**\n"
                    for t, data in BANK_TIERS.items():
                        if t > current_tier:
                            desc += f"`{t}` : **{data['name']}** — Max {self._fmt_amount(data['limit'])} — Prix : **{self._fmt_amount(data['price'])}**\n"
                    
                    desc += "\nUtilisez `+upgrade_bank <numero>` pour acheter."
                    emb = self._bank_embed(ctx, title="⬆️ Amélioration Bancaire", description=desc, color=discord.Color.gold())
                    return await ctx.send(embed=emb)
                
                if tier_choice <= current_tier:
                    return await ctx.send("❌ Vous avez déjà ce palier ou mieux.")
                
                if tier_choice not in BANK_TIERS:
                    return await ctx.send("❌ Palier invalide.")
                
                target_data = BANK_TIERS[tier_choice]
                price = target_data["price"]
                
                if bal < price:
                    return await ctx.send(f"❌ Pas assez d'argent en poche (Requis: {self._fmt_amount(price)}).")
                
                # Buy
                await cur.execute("UPDATE users SET balance=balance-%s, bank_tier=%s WHERE user_id=%s", (price, tier_choice, ctx.author.id))
                
        await ctx.send(f"✅ Félicitations ! Vous êtes passé au palier **{target_data['name']}** (Max {self._fmt_amount(target_data['limit'])}).")

    @commands.command(name="withbank", aliases=["wb"])
    async def withbank(self, ctx: commands.Context, bank_id: int, amount: str):
        if bank_id not in (1, 2, 3):
            emb = self._bank_embed(ctx, title="Erreur", description="Banque invalide. Utilisez 1, 2 ou 3.", color=discord.Color.red())
            return await ctx.send(embed=emb)
        
        await self._connect(); await self._ensure_user(ctx.author.id)
        
        col_name = "bank" if bank_id == 1 else f"bank_{bank_id}"
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT {col_name} FROM users WHERE user_id=%s", (ctx.author.id,))
                bank_bal = (await cur.fetchone())[0]
                
                amt = self._parse_bet_amount(amount, bank_bal)
                if amt <= 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                
                # Atomic Transaction
                await cur.execute(
                    f"UPDATE users SET balance = balance + %s, {col_name} = {col_name} - %s WHERE user_id=%s AND {col_name} >= %s",
                    (amt, amt, ctx.author.id, amt)
                )

                if cur.rowcount == 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Pas assez dans la banque (ou transaction échouée).", color=discord.Color.red())
                    return await ctx.send(embed=emb)

                # Fetch new values
                await cur.execute(f"SELECT balance, {col_name} FROM users WHERE user_id=%s", (ctx.author.id,))
                new_bal, new_bank = await cur.fetchone()

        
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title=f"Retrait Banque {bank_id}",
            color=discord.Color.blue(),
            fields=[
                ("Montant", f"{self._fmt_amount(amt)} {cur}", True),
                ("Nouveau Solde Banque", f"{self._fmt_amount(new_bank)} {cur}", True),
            ],
            txn_id=self._txn_id(),
        )
        await ctx.send(embed=emb)

    @commands.command(name="deposit", aliases=["dep"]) 
    async def deposit(self, ctx: commands.Context, amount: str):
        """(Désactivé) Déposer de l'argent."""
        emb = self._bank_embed(ctx, title="Action Impossible", description="❌ Les dépôts sont désactivés par la banque centrale.", color=discord.Color.red())
        await ctx.send(embed=emb)
        return

        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (ctx.author.id,))
                bal, bank = await cur.fetchone()
                amt = self._parse_bet_amount(amount, bal)
                
                if amt <= 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                if bal < amt:
                    emb = self._bank_embed(ctx, title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                
                # Limite de 100k (Banque 1)
                MAX_CAPACITY = 100000
                if bank + amt > MAX_CAPACITY:
                    space = MAX_CAPACITY - bank
                    if space <= 0:
                        desc = "La banque est pleine (Max 100k)."
                    else:
                        desc = f"Limite de 100k atteinte. Tu ne peux déposer que {self._fmt_amount(space)} {self._currency_emoji(ctx)}."
                    emb = self._bank_embed(ctx, title="Erreur", description=desc, color=discord.Color.red())
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
                amt = self._parse_bet_amount(amount, bank)
                
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

    @commands.command(name="facture", aliases=["invoice", "bill"])
    async def facture(self, ctx: commands.Context, target: discord.Member, amount: str, *, reason: str = "Aucun motif"):
        """Envoyer une facture à un joueur."""
        if target.bot or target.id == ctx.author.id:
            return await ctx.send("❌ Cible invalide.")
            
        await self._connect(); await self._ensure_user(ctx.author.id); await self._ensure_user(target.id)
        
        # Check amount
        # Need target balance for "all" ? No, fixed amount usually.
        # Use a dummy balance for parsing.
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                 await cur.execute("SELECT balance FROM users WHERE user_id=%s", (target.id,))
                 t_bal = (await cur.fetchone())[0]

        amt_int = self._parse_bet_amount(amount, t_bal)     
        if amt_int <= 0:
            return await ctx.send("❌ Montant invalide.")
            
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO invoices (sender_id, receiver_id, amount, reason, status) VALUES (%s, %s, %s, %s, 'pending')",
                    (ctx.author.id, target.id, amt_int, reason)
                )
                inv_id = cur.lastrowid
                
        cur_emoji = self._currency_emoji(ctx)
        
        # Notify Sender
        await ctx.send(f"✅ Facture **#{inv_id}** de {self._fmt_amount(amt_int)} {cur_emoji} envoyée à {target.mention} pour : *{reason}*.")
        
        # Notify Receiver (Channel with Buttons)
        emb = discord.Embed(
            title="🧾 Facture Reçue",
            description=f"**De :** {ctx.author.mention}\n**Montant :** {self._fmt_amount(amt_int)} {cur_emoji}\n**Motif :** {reason}",
            color=discord.Color.orange()
        )
        emb.set_footer(text=f"ID: {inv_id}")
        
        view = InvoiceView(ctx, inv_id, amt_int, ctx.author.id, self)
        await ctx.send(f"{target.mention}, vous avez reçu une facture !", embed=emb, view=view)

    @commands.command(name="payfacture", aliases=["payinvoice", "pf"])
    async def payfacture(self, ctx: commands.Context, invoice_id: int):
        """(Obsolète) Payer une facture (Utilisez les boutons)."""
        await ctx.send("ℹ️ Utilisez les boutons sous la facture pour payer ou refuser.")

    @commands.command(name="admin_assets")
    @commands.has_permissions(administrator=True)
    async def admin_assets(self, ctx: commands.Context, action: str, target: discord.Member, asset_type: str = None, item_key: str = None):
        """(Admin) Gérer les assets : list/remove <user> [immo/luxe] [key]"""
        await self._connect(); await self._ensure_user(target.id)
        
        if action == "list":
            # List all assets
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Immo
                    await cur.execute("SELECT property_key FROM user_properties WHERE user_id=%s", (target.id,))
                    props = await cur.fetchall()
                    p_list = [f"`{p[0]}` ({PROPERTIES.get(p[0], {}).get('name', '?')})" for p in props]
                    
                    # Luxe
                    await cur.execute("SELECT item_key, serial_number FROM user_luxury WHERE user_id=%s", (target.id,))
                    luxs = await cur.fetchall()
                    l_list = [f"`{l[0]}` (#{l[1]})" for l in luxs]
            
            desc = f"**Immobilier ({len(p_list)}) :**\n" + (", ".join(p_list) if p_list else "Aucun") + "\n\n"
            desc += f"**Luxe ({len(l_list)}) :**\n" + (", ".join(l_list) if l_list else "Aucun")
            
            emb = self._bank_embed(ctx, title=f"Assets de {target.display_name}", description=desc, color=discord.Color.red())
            await ctx.send(embed=emb)
            
        elif action == "remove":
            if not asset_type or not item_key:
                return await ctx.send("❌ Usage: `+admin_assets remove <user> <immo/luxe> <key>`")
            
            if asset_type not in ("immo", "luxe"):
                return await ctx.send("❌ Type invalide (immo/luxe).")

            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if asset_type == "immo":
                        await cur.execute("DELETE FROM user_properties WHERE user_id=%s AND property_key=%s", (target.id, item_key))
                    else:
                        await cur.execute("DELETE FROM user_luxury WHERE user_id=%s AND item_key=%s", (target.id, item_key))
                    
                    if cur.rowcount > 0:
                        await ctx.send(f"✅ Asset `{item_key}` retiré à {target.display_name}.")
                        # Log
                        await cur.execute(
                            "INSERT INTO transactions (type, requester_id, target_id, amount, account, status) VALUES (%s, %s, %s, %s, %s, %s)",
                            ('admin_remove_asset', ctx.author.id, target.id, 0, asset_type, 'success')
                        )
                    else:
                        await ctx.send("❌ Asset introuvable pour ce joueur.")

    @commands.command(name="audit")
    @commands.has_permissions(administrator=True) # Only admins? Or Police role? Let's say Admins for now.
    async def audit(self, ctx: commands.Context, target: discord.Member):
        """(Admin) Auditer les finances d'un joueur."""
        await self._connect()
        
        embed = discord.Embed(title=f"🕵️ Rapport d'Audit : {target.display_name}", color=discord.Color.red())
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Wealth
                await cur.execute("SELECT balance, bank, bank_2, bank_3 FROM users WHERE user_id=%s", (target.id,))
                res = await cur.fetchone()
                if not res: return await ctx.send("Utilisateur introuvable.")
                bal, b1, b2, b3 = res
                embed.add_field(name="💰 Richesse Actuelle", value=f"Cash: {self._fmt_amount(bal)}\nBanques: {self._fmt_amount(b1+b2+b3)}", inline=False)
                
                # Assets
                await cur.execute("SELECT property_key FROM user_properties WHERE user_id=%s", (target.id,))
                props = await cur.fetchall()
                prop_val = sum(PROPERTIES[p[0]]['price'] for p in props if p[0] in PROPERTIES)
                
                await cur.execute("SELECT item_key FROM user_luxury WHERE user_id=%s", (target.id,))
                luxs = await cur.fetchall()
                lux_val = sum(LUXURY_ITEMS[l[0]]['price'] for l in luxs if l[0] in LUXURY_ITEMS)
                
                embed.add_field(name="🏰 Patrimoine", value=f"Immobilier: {self._fmt_amount(prop_val)}\nLuxe: {self._fmt_amount(lux_val)}", inline=False)

                # Recent Inflows (Money In)
                await cur.execute(
                    "SELECT type, requester_id, amount, created_at FROM transactions WHERE target_id=%s AND type IN ('transfer', 'invoice') ORDER BY created_at DESC LIMIT 5",
                    (target.id,)
                )
                inflows = await cur.fetchall()
                in_txt = ""
                for t in inflows:
                    ttype, req_id, amt, date = t
                    in_txt += f"• +{self._fmt_amount(amt)} de <@{req_id}> ({ttype}) le {date.strftime('%d/%m')}\n"
                if not in_txt: in_txt = "Aucun mouvement suspect récent."
                embed.add_field(name="📥 Entrées d'Argent (5 dernières)", value=in_txt, inline=False)
                
                # Recent Outflows (Money Out)
                await cur.execute(
                    "SELECT type, target_id, amount, created_at FROM transactions WHERE requester_id=%s AND type IN ('transfer', 'invoice') ORDER BY created_at DESC LIMIT 5",
                    (target.id,)
                )
                outflows = await cur.fetchall()
                out_txt = ""
                for t in outflows:
                    ttype, tgt_id, amt, date = t
                    out_txt += f"• -{self._fmt_amount(amt)} vers <@{tgt_id}> ({ttype}) le {date.strftime('%d/%m')}\n"
                if not out_txt: out_txt = "Aucune dépense majeure récente."
                embed.add_field(name="📤 Sorties d'Argent (5 dernières)", value=out_txt, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="ecostats")
    async def ecostats(self, ctx: commands.Context):
        """Statistiques économiques globales du serveur."""
        await self._connect()
        cur_emoji = self._currency_emoji(ctx)
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Money Supply (M1)
                await cur.execute("SELECT SUM(balance + bank + bank_2 + bank_3) FROM users")
                m1 = (await cur.fetchone())[0] or 0
                
                # Real Estate Value
                await cur.execute("SELECT property_key FROM user_properties")
                all_props = await cur.fetchall()
                prop_val = sum(PROPERTIES[p[0]]['price'] for p in all_props if p[0] in PROPERTIES)
                
                # Luxury Value
                await cur.execute("SELECT item_key FROM user_luxury")
                all_lux = await cur.fetchall()
                lux_val = sum(LUXURY_ITEMS[l[0]]['price'] for l in all_lux if l[0] in LUXURY_ITEMS)
                
                # GDP (Gross Domestic Product - approximated by Total Wealth)
                gdp = m1 + prop_val + lux_val
                
                # Richest Player
                await cur.execute("SELECT user_id, (balance + bank + bank_2 + bank_3) as wealth FROM users ORDER BY wealth DESC LIMIT 1")
                richest = await cur.fetchone()
                
        embed = discord.Embed(title="📊 Statistiques Économiques (INSEE)", color=discord.Color.dark_blue())
        embed.add_field(name="💰 Masse Monétaire (Cash + Banques)", value=f"{self._fmt_amount(m1)} {cur_emoji}", inline=False)
        embed.add_field(name="🏰 Valorisation Immobilière", value=f"{self._fmt_amount(prop_val)} {cur_emoji}", inline=True)
        embed.add_field(name="💎 Marché du Luxe", value=f"{self._fmt_amount(lux_val)} {cur_emoji}", inline=True)
        embed.add_field(name="🌍 PIB Total (Wealth)", value=f"**{self._fmt_amount(gdp)} {cur_emoji}**", inline=False)
        
        if richest:
            share = (richest[1] / m1 * 100) if m1 > 0 else 0
            embed.add_field(name="👑 Joueur le plus riche", value=f"<@{richest[0]}> possède {share:.1f}% de la masse monétaire.", inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="send", aliases=["give","sd"]) 
    async def send(self, ctx: commands.Context, member: discord.Member, amount: str):
        await self._connect(); await self._ensure_user(ctx.author.id); await self._ensure_user(member.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                amount_int = self._parse_bet_amount(amount, bal)

                if amount_int <= 0:
                    emb = self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                if bal < amount_int:
                    emb = self._bank_embed(ctx, title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await ctx.send(embed=emb)
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amount_int, ctx.author.id))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount_int, member.id))
        cur = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Virement",
            color=discord.Color.purple(),
            fields=[
                ("De", ctx.author.mention, True),
                ("Vers", member.mention, True),
                ("Montant", f"{self._fmt_amount(amount_int)} {cur}", True),
            ],
            txn_id=self._txn_id(),
        )
        await ctx.send(embed=emb)

    @commands.command(name="leaderboard", aliases=["lb"]) 
    async def leaderboard(self, ctx: commands.Context):
        await self._connect()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Top 10 users based on total balance (poche + toutes les banques)
                await cur.execute("SELECT user_id, (balance + bank + bank_2 + bank_3) AS total FROM users ORDER BY total DESC LIMIT 10")
                rows = await cur.fetchall()
        
        cur = self._currency_emoji(ctx)
        
        # Amélioration de l'embed du leaderboard
        if not rows:
            desc = "Aucun joueur dans le classement pour l'instant."
            color = discord.Color.blurple()
        else:
            description_lines = [f"**#{i+1}** <@{uid}> — **{self._fmt_amount(total)} {cur}**" for i, (uid, total) in enumerate(rows)]
            desc = "\n".join(description_lines)
            color = discord.Color.gold()
        
        emb = self._bank_embed(
            ctx, 
            title=f"🥇 Classement des {len(rows)} meilleurs joueurs 🏆", 
            description=desc, 
            color=color
        )
        
        emb.set_footer(text="Basé sur le solde total (poche + banque).")
        await ctx.send(embed=emb)

    # Shop commands
    @commands.command(name="shop", aliases=["sh"]) 
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

    @commands.command(name="buy", aliases=["b"]) 
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

    @commands.command(name="sell", aliases=["se"]) 
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
                ("Prix", f"{self._fmt_amount(price)} {cur}", True), # Mis à jour ici aussi
                ("Vendeur", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
            actor=ctx.author,
        )
        await ctx.send(embed=emb)

    @commands.command(name="immo", aliases=["realestate"])
    async def immo(self, ctx: commands.Context, action: str = None, name: str = None):
        """Système immobilier: buy, list, collect"""
        await self._connect()
        cur_emoji = self._currency_emoji(ctx)
        
        if not action or action.lower() == "list":
            embed = discord.Embed(title="🏢 Agence Immobilière", color=discord.Color.blue())
            for key, data in PROPERTIES.items():
                embed.add_field(
                    name=f"{data['emoji']} {data['name']}",
                    value=f"**Prix:** {self._fmt_amount(data['price'])} {cur_emoji}\n**Revenu:** {self._fmt_amount(data['income'])} {cur_emoji}/jour\n*{data['desc']}*",
                    inline=False
                )
            embed.set_footer(text=f"Utilise {ctx.prefix}immo buy <nom> pour acheter")
            return await ctx.send(embed=embed)

        if action.lower() == "buy":
            if not name:
                return await ctx.send(f"❌ Indique le nom du bien à acheter (ex: `{ctx.prefix}immo buy studio`).")
            
            # Find property
            prop_key = next((k for k in PROPERTIES if k.lower() == name.lower() or PROPERTIES[k]['name'].lower() == name.lower()), None)
            if not prop_key:
                return await ctx.send("❌ Ce bien n'existe pas. Regarde `+immo list`.")
            
            prop_data = PROPERTIES[prop_key]
            price = prop_data['price']
            
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Check balance
                    await cur.execute("SELECT balance, bank, bank_2, bank_3 FROM users WHERE user_id=%s", (ctx.author.id,))
                    res = await cur.fetchone()
                    if not res: return await ctx.send("❌ Compte introuvable.")
                    bal, b1, b2, b3 = res
                    total_wealth = bal + b1 + b2 + b3
                    
                    if total_wealth < price:
                        return await ctx.send(f"❌ T'as pas les sous. Il faut {self._fmt_amount(price)} {cur_emoji}.")
                    
                    # Deduct money (prioritize pocket, then banks)
                    remaining = price
                    new_bal = bal
                    new_b1 = b1
                    new_b2 = b2
                    new_b3 = b3
                    
                    if new_bal >= remaining:
                        new_bal -= remaining
                        remaining = 0
                    else:
                        remaining -= new_bal
                        new_bal = 0
                        
                    if remaining > 0:
                        if new_b1 >= remaining:
                            new_b1 -= remaining
                            remaining = 0
                        else:
                            remaining -= new_b1
                            new_b1 = 0
                            
                    if remaining > 0:
                        if new_b2 >= remaining:
                            new_b2 -= remaining
                            remaining = 0
                        else:
                            remaining -= new_b2
                            new_b2 = 0
                            
                    if remaining > 0:
                        if new_b3 >= remaining:
                            new_b3 -= remaining
                            remaining = 0
                        else:
                            remaining -= new_b3
                            new_b3 = 0
                    
                    # Update Balance
                    await cur.execute(
                        "UPDATE users SET balance=%s, bank=%s, bank_2=%s, bank_3=%s WHERE user_id=%s",
                        (new_bal, new_b1, new_b2, new_b3, ctx.author.id)
                    )
                    
                    # Add Property
                    await cur.execute(
                        "INSERT INTO user_properties (user_id, property_key, last_collected) VALUES (%s, %s, %s)",
                        (ctx.author.id, prop_key, dt.datetime.now() - dt.timedelta(days=1)) # Ready to collect immediately? Or wait 24h? Let's say wait. Actually user expects immediate rent? No, real estate takes time. Let's set last_collected to NOW, so they wait 24h.
                    )
                    await conn.commit()
            
            await ctx.send(f"✅ Félicitations ! Tu es l'heureux propriétaire de **{prop_data['name']}** {prop_data['emoji']} !")
            return

        if action.lower() == "collect":
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT id, property_key, last_collected FROM user_properties WHERE user_id=%s", (ctx.author.id,))
                    rows = await cur.fetchall()
                    
                    if not rows:
                        return await ctx.send("❌ Tu n'as aucun bien immobilier.")
                    
                    total_income = 0
                    now = dt.datetime.now()
                    collected_count = 0
                    
                    for row in rows:
                        pid, key, last = row
                        if key not in PROPERTIES: continue
                        
                        # Check 24h cooldown
                        if last and (now - last).total_seconds() < 86400:
                            continue
                            
                        income = PROPERTIES[key]['income']
                        total_income += income
                        collected_count += 1
                        
                        # Update timestamp
                        await cur.execute("UPDATE user_properties SET last_collected=%s WHERE id=%s", (now, pid))
                    
                    if total_income > 0:
                        # Add to balance
                        await cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (total_income, ctx.author.id))
                        await conn.commit()
                        await ctx.send(f"✅ Loyers collectés : **{self._fmt_amount(total_income)}** {cur_emoji} (sur {collected_count} biens).")
                    else:
                        await ctx.send("❌ Aucun loyer à collecter pour le moment (reviens plus tard).")
            return

    @commands.command(name="luxury", aliases=["shopluxe", "luxe"])
    async def luxury(self, ctx: commands.Context, action: str = None, item_name: str = None):
        """Boutique de luxe et flex"""
        await self._connect()
        cur_emoji = self._currency_emoji(ctx)
        
        if not action or action.lower() == "list":
            embed = discord.Embed(title="💎 Boutique de Luxe", color=discord.Color.purple())
            
            # Group by type
            categories = {}
            for k, v in LUXURY_ITEMS.items():
                t = v.get('type', 'Autre')
                if t not in categories: categories[t] = []
                categories[t].append(v)
            
            for cat, items in categories.items():
                desc = ""
                for data in items:
                    key = next(k for k, v in LUXURY_ITEMS.items() if v == data)
                    desc += f"{data['emoji']} **{data['name']}** - {self._fmt_amount(data['price'])} {cur_emoji} (`{key}`)\n"
                embed.add_field(name=f"--- {cat} ---", value=desc, inline=False)
                
            embed.set_footer(text=f"Utilise {ctx.prefix}luxury buy <nom_item> pour flex.")
            return await ctx.send(embed=embed)

        if action.lower() == "buy":
            if not item_name:
                return await ctx.send("❌ Qu'est-ce que tu veux acheter ?")
            
            item_key = next((k for k in LUXURY_ITEMS if k.lower() == item_name.lower() or LUXURY_ITEMS[k]['name'].lower() == item_name.lower()), None)
            if not item_key:
                return await ctx.send("❌ Cet article n'existe pas.")
            
            data = LUXURY_ITEMS[item_key]
            price = data['price']
            
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Check balance
                    await cur.execute("SELECT balance, bank, bank_2, bank_3 FROM users WHERE user_id=%s", (ctx.author.id,))
                    res = await cur.fetchone()
                    if not res: return await ctx.send("❌ Compte introuvable.")
                    bal, b1, b2, b3 = res
                    total_wealth = bal + b1 + b2 + b3
                    
                    if total_wealth < price:
                        return await ctx.send(f"❌ T'es trop pauvre pour ça. Il faut {self._fmt_amount(price)} {cur_emoji}.")
                    
                    # Deduct (Pocket -> Banks)
                    remaining = price
                    new_bal, new_b1, new_b2, new_b3 = bal, b1, b2, b3
                    
                    # Deduction Logic (Same as Real Estate)
                    if new_bal >= remaining: new_bal -= remaining; remaining = 0
                    else: remaining -= new_bal; new_bal = 0
                    if remaining > 0 and new_b1 >= remaining: new_b1 -= remaining; remaining = 0
                    elif remaining > 0: remaining -= new_b1; new_b1 = 0
                    if remaining > 0 and new_b2 >= remaining: new_b2 -= remaining; remaining = 0
                    elif remaining > 0: remaining -= new_b2; new_b2 = 0
                    if remaining > 0 and new_b3 >= remaining: new_b3 -= remaining; remaining = 0
                    elif remaining > 0: remaining -= new_b3; new_b3 = 0
                    
                    # Update Balance
                    await cur.execute(
                        "UPDATE users SET balance=%s, bank=%s, bank_2=%s, bank_3=%s WHERE user_id=%s",
                        (new_bal, new_b1, new_b2, new_b3, ctx.author.id)
                    )
                    
                    # Generate Serial Number
                    await cur.execute("SELECT COUNT(*) FROM user_luxury WHERE item_key=%s", (item_key,))
                    count = (await cur.fetchone())[0]
                    serial = count + 1
                    
                    # Add Item
                    await cur.execute(
                        "INSERT INTO user_luxury (user_id, item_key, serial_number, original_owner_id) VALUES (%s, %s, %s, %s)", 
                        (ctx.author.id, item_key, serial, ctx.author.id)
                    )
                    await conn.commit()
            
            await ctx.send(f"💎 **BOOM !** Tu viens d'acheter **{data['name']}** {data['emoji']} (Série #{serial}) ! T'es le roi du pétrole.")
            return

    @commands.command(name="assets", aliases=["biens", "patrimoine"])
    async def assets(self, ctx: commands.Context, member: discord.Member = None):
        """Affiche le patrimoine immobilier et luxe"""
        member = member or ctx.author
        await self._connect()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Get Properties
                await cur.execute("SELECT property_key, last_collected FROM user_properties WHERE user_id=%s", (member.id,))
                props = await cur.fetchall()
                
                # Get Luxury
                await cur.execute("SELECT item_key, purchase_date FROM user_luxury WHERE user_id=%s", (member.id,))
                luxs = await cur.fetchall()
        
        embed = discord.Embed(title=f"🏰 Patrimoine de {member.display_name}", color=discord.Color.gold())
        
        # Properties Field
        if props:
            prop_list = ""
            total_income = 0
            prop_val = 0
            counts = {}
            
            for p in props:
                k = p[0]
                if k in PROPERTIES:
                    counts[k] = counts.get(k, 0) + 1
                    total_income += PROPERTIES[k]['income']
                    prop_val += PROPERTIES[k]['price']
            
            for k, count in counts.items():
                data = PROPERTIES[k]
                prop_list += f"{count}x {data['emoji']} **{data['name']}**\n"
            
            prop_list += f"\n💰 **Revenu total:** {self._fmt_amount(total_income)}/jour"
            prop_list += f"\n🏘️ **Valeur Immo:** {self._fmt_amount(prop_val)}"
            embed.add_field(name="Immobilier", value=prop_list, inline=False)
        else:
            embed.add_field(name="Immobilier", value="SDF (Sans Domicile Fixe)", inline=False)
            prop_val = 0

        # Luxury Field
        if luxs:
            lux_list = ""
            lux_val = 0
            lcounts = {}
            for l in luxs:
                k = l[0]
                if k in LUXURY_ITEMS:
                    lcounts[k] = lcounts.get(k, 0) + 1
                    lux_val += LUXURY_ITEMS[k]['price']
            
            for k, count in lcounts.items():
                data = LUXURY_ITEMS[k]
                lux_list += f"{count}x {data['emoji']} **{data['name']}**\n"
            
            lux_list += f"\n💎 **Valeur Luxe:** {self._fmt_amount(lux_val)}"
            embed.add_field(name="Objets de Luxe", value=lux_list, inline=False)
        else:
            embed.add_field(name="Objets de Luxe", value="Aucun flow.", inline=False)
            lux_val = 0
            
        embed.set_footer(text=f"Valeur Totale des Actifs: {self._fmt_amount(prop_val + lux_val)}")
        await ctx.send(embed=embed)

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

    @commands.command(name="transactions", aliases=["tx"])
    async def transactions(self, ctx: commands.Context):
        await self._connect()
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT type, amount, created_at, requester_id, target_id 
                        FROM transactions 
                        ORDER BY created_at DESC LIMIT 10
                    """)
                    rows = await cur.fetchall()
            
            if not rows:
                return await ctx.send("Aucune transaction récente.")
            
            cur_sym = self._currency_emoji(ctx)
            fields = []
            for r in rows:
                ttype, amount, date, u1_id, u2_id = r
                date_str = date.strftime("%H:%M:%S")
                u1 = f"<@{u1_id}>" if u1_id else "Système"
                u2 = f"<@{u2_id}>" if u2_id else "Système"
                
                if ttype == 'transfer':
                    desc = f"{u1} ➔ {u2}"
                elif ttype == 'deposit':
                    desc = f"{u1} ➔ Banque"
                elif ttype == 'withdraw':
                    desc = f"Banque ➔ {u1}"
                else:
                    desc = f"{ttype} {u1}"
                    
                fields.append((f"{date_str} • {self._fmt_amount(amount)} {cur_sym}", desc, False))
                
            emb = self._bank_embed(ctx, title="Dernières Transactions", color=discord.Color.blue(), fields=fields)
            await ctx.send(embed=emb)
        except Exception as e:
            await ctx.send(f"Erreur transactions: {e}")

    # cmd
    @commands.command(name="daily", aliases=["d"])
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
                ("Montant", f"+{self._fmt_amount(reward)} {cur}", True),
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
                ("Montant", f"+{self._fmt_amount(reward)} {cur}", True),
                ("Bénéficiaire", ctx.author.mention, True),
            ],
            txn_id=self._txn_id(),
            actor=ctx.author,
        )
        await ctx.send(embed=emb)

    @commands.command(name="monthly", aliases=["m"]) 
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
                ("Montant", f"+{self._fmt_amount(reward)} {cur}", True),
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
                if self.logs_enabled:
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
                ("Montant", f"+{self._fmt_amount(amount)} {cur}", True),
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
        emb = self._bank_embed(ctx, title="Transaction acceptée", color=discord.Color.green(), fields=[("ID", txid, True), ("Montant", f"+{self._fmt_amount(amount)} {cur}", True)], txn_id=txid)
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
        emb = self._bank_embed(ctx, title="Taxe appliquée", color=discord.Color.dark_red(), fields=[("ID", txid, True), ("Montant", f"{self._fmt_amount(tax_real)} {cur}", True)], txn_id=txid)
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
                ("Montant", f"-{self._fmt_amount(amount)} {cur}", True),
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
    @commands.command(name="coin_flip", aliases=["cf", "coinflip", "flip"], help="Pile/Face avec mise. Gains taxables via ID.") 
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def coin_flip(self, ctx: commands.Context, bet_on: str | None = None, amount: str | None = None):
        await self._connect(); await self._ensure_user(ctx.author.id)
        if bet_on is None or amount is None:
            view = CoinFlipView(self, ctx)
            msg = await ctx.send(embed=self._bank_embed(ctx, title="Casino • Pile ou Face", description=":coin: Choisis Pile ou Face et ta mise", color=discord.Color.blurple()), view=view)
            try:
                view.message = msg
            except Exception:
                pass
            return
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
                    if self.logs_enabled:
                        await cur.execute(
                            "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (txid, "win", ctx.author.id, ctx.author.id, amt, "balance", "won"),
                        )
                    desc = f"Coin flip: {flip}. Gagné +{self._fmt_amount(amt)} {self._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, ctx.author.id))
                    desc = f"Coin flip: {flip}. Perdu -{self._fmt_amount(amt)} {self._currency_emoji(ctx)}"
                    color = discord.Color.red()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Casino • Pile ou Face",
            description=f"**Mise : {self._fmt_amount(amt)} {cur_emoji}**",
            color=color,
            txn_id=txid,
        )
        emb.add_field(name="Choix", value=side, inline=True)
        emb.add_field(name="Tirage", value=str(flip), inline=True)
        res_txt = "Gagné" if color == discord.Color.green() else "Perdu"
        emb.add_field(name="Résultat", value=f"{res_txt} {self._fmt_amount(amt)} {cur_emoji}", inline=False)
        emb.add_field(name="Solde après jeu", value=f"**{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**", inline=False)
        await ctx.send(embed=emb)

    @commands.command(name="ladder", aliases=["ld"], help="Échelle Push Your Luck: +ladder montant") 
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def ladder(self, ctx: commands.Context, amount: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(str(amount), bal_user)
        # Nerf: limites et plafond
        LADDER_MIN = 1000
        LADDER_MAX = min(bal_user, 1_000_000)  # plafond 1M
        if amt < LADDER_MIN:
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description=f"Mise minimale: {self._fmt_amount(LADDER_MIN)} {self._currency_emoji(ctx)}", color=discord.Color.red()))
        if amt > LADDER_MAX:
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description=f"Mise maximale: {self._fmt_amount(LADDER_MAX)} {self._currency_emoji(ctx)}", color=discord.Color.red()))
        view = LadderView(self, ctx, amt)
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(ctx, title="Casino • Échelle Push Your Luck", description=f"Mise initiale: **{self._fmt_amount(amt)} {cur_emoji}**\nChoisis 'Continuer' pour augmenter ton gain ou 'Encaisser' pour récupérer ton gain actuel.", color=discord.Color.blurple())
        msg = await ctx.send(embed=emb, view=view)
        try:
            view.message = msg
        except Exception:
            pass

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
                ("Montant", f"-{self._fmt_amount(amount)} {cur_emoji} pour la victime", False), # Mis à jour ici
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
                    if self.logs_enabled:
                        await cur.execute(
                            "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (txid, "win", ctx.author.id, ctx.author.id, win, "balance", "won"),
                        )
                    desc = f"Slots {' | '.join(r)} — Gagné +{self._fmt_amount(win)} {self._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, ctx.author.id))
                    desc = f"Slots {' | '.join(r)} — Perdu -{self._fmt_amount(amt)} {self._currency_emoji(ctx)}"
                    color = discord.Color.red()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Casino • Machines à sous",
            description=f"**Mise : {self._fmt_amount(amt)} {cur_emoji}**",
            color=color,
            txn_id=txid,
        )
        emb.add_field(name="Roues", value=" | ".join(r), inline=True)
        if txid:
            emb.add_field(name="Gain", value=f"+{self._fmt_amount(win)} {cur_emoji}", inline=True)
        else:
            emb.add_field(name="Perte", value=f"-{self._fmt_amount(amt)} {cur_emoji}", inline=True)
        emb.add_field(name="Solde après jeu", value=f"**{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**", inline=False)
        await ctx.send(embed=emb)

    @commands.command(name="dice", aliases=["de","dc"], help="Pari pair/impair ou chiffre. Maison avantage légère.") 
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
        if bet_on is not None and not (1 <= bet_on <= 6):
            return await ctx.send("Parie sur un nombre entre 1 et 6.")
        import random
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
                    if self.logs_enabled:
                        await cur.execute(
                            "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (txid, "win", ctx.author.id, ctx.author.id, win, "balance", "won"),
                        )
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (-win, ctx.author.id))
                desc = f"Dé {roll} — {'Gagné +' + self._fmt_amount(win) if win>0 else 'Perdu ' + self._fmt_amount(abs(win))} {self._currency_emoji(ctx)}"
                color = discord.Color.green() if win > 0 else discord.Color.red()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(
            ctx,
            title="Casino • Jeu du dé",
            description=f"**Mise : {self._fmt_amount(abs(win) if win < 0 else amt)} {cur_emoji}**",
            color=color,
            txn_id=txid,
        )
        emb.add_field(name="Tirage", value=str(roll), inline=True)
        if bet_on is not None:
            emb.add_field(name="Pari", value=str(bet_on), inline=True)
        res_txt = "+" + self._fmt_amount(win) if win > 0 else "-" + self._fmt_amount(abs(win))
        emb.add_field(name="Résultat", value=f"{res_txt} {cur_emoji}", inline=False)
        emb.add_field(name="Solde après jeu", value=f"**{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**", inline=False)
        await ctx.send(embed=emb)

    @commands.command(name="roulette", aliases=["rl"], help="Roulette européenne: +roulette <mise> <pari>. Ex: +roulette 1m rouge | pair | 17 | 1-18 | 19-36 | 1st | 2nd | 3rd")
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def roulette(self, ctx: commands.Context, amount: str, bet: str):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(str(amount), bal_user)
        if amt <= 0:
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Montant invalide.", color=discord.Color.red()))
        if bal_user < amt:
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Pas assez en poche.", color=discord.Color.red()))
        b = bet.strip().lower()
        kind = None; value = None
        if b in ("rouge", "red"):
            kind = "color"; value = "red"
        elif b in ("noir", "black"):
            kind = "color"; value = "black"
        elif b in ("pair", "even"):
            kind = "parity"; value = "even"
        elif b in ("impair", "odd"):
            kind = "parity"; value = "odd"
        elif b in ("1-18", "bas"):
            kind = "range"; value = (1, 18)
        elif b in ("19-36", "haut"):
            kind = "range"; value = (19, 36)
        elif b in ("1st", "premier"):
            kind = "dozen"; value = 1
        elif b in ("2nd", "deuxième"):
            kind = "dozen"; value = 2
        elif b in ("3rd", "troisième"):
            kind = "dozen"; value = 3
        else:
            try:
                num = int(b)
                if not (0 <= num <= 36):
                    raise ValueError
                kind = "number"; value = num
            except Exception:
                return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Pari invalide.", color=discord.Color.red()))
        import random
        wheel_red = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        n = random.randint(0, 36)
        win_amt = 0
        if kind == "color":
            is_red = n in wheel_red
            ok = (value == "red" and is_red) or (value == "black" and n != 0 and not is_red)
            win_amt = int(amt * 2) if ok else -amt
        elif kind == "parity":
            ok = (n != 0 and (n % 2 == 0 and value == "even" or n % 2 == 1 and value == "odd"))
            win_amt = int(amt * 2) if ok else -amt
        elif kind == "range":
            ok = (value[0] <= n <= value[1])
            win_amt = int(amt * 2) if ok else -amt
        elif kind == "dozen":
            group = 1 if (1 <= n <= 12) else 2 if (13 <= n <= 24) else 3 if (25 <= n <= 36) else 0
            ok = (group == value)
            win_amt = int(amt * 3) if ok else -amt
        elif kind == "number":
            ok = (n == value)
            win_amt = int(amt * 36) if ok else -amt
        txid = None
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal = (await cur.fetchone())[0]
                if bal < amt:
                    return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Pas assez en poche.", color=discord.Color.red()))
                if win_amt > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win_amt, ctx.author.id))
                    txid = self._txn_id()
                    if self.logs_enabled:
                        await cur.execute("INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)", (txid, "win", ctx.author.id, ctx.author.id, win_amt, "balance", "won"))
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (-win_amt, ctx.author.id))
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self._currency_emoji(ctx)
        color = discord.Color.green() if win_amt > 0 else discord.Color.red()
        result_txt = f"**Résultat: {n} {'🔴' if n in wheel_red else ('⚫' if n != 0 else '🟢')}**"
        if win_amt > 0:
            desc = f"{result_txt}\n\n:tada: __**Vous avez gagné {self._fmt_amount(win_amt)} {cur_emoji} Fcoins !**__\n\nVotre solde s'estime à : **{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**"
        else:
            desc = f"{result_txt}\n\n:x: **Vous avez perdu {self._fmt_amount(abs(win_amt))} {cur_emoji} Fcoins**\n\nVotre solde s'estime à : **{self._fmt_amount(bal_after)} {cur_emoji} Fcoins**"
        emb = self._bank_embed(ctx, title="Casino • Roulette", description=desc, color=color, txn_id=txid)
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
        
    @commands.command(name="blackjack", aliases=["bj"], help="Jeu de Blackjack contre le croupier.")
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5), commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context, amount: str):
        await self._connect()
        await self._ensure_user(ctx.author.id)

        if ctx.author.id in self._blackjack_sessions and not self._blackjack_sessions[ctx.author.id].ended:
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Vous avez déjà une partie de Blackjack en cours ! Terminez-la ou attendez qu'elle expire.", color=discord.Color.red()))

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        
        amt = self._parse_bet_amount(amount, bal_user)

        if amt <= 0:
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Montant de mise invalide.", color=discord.Color.red()))
        if bal_user < amt:
            return await ctx.send(embed=self._bank_embed(ctx, title="Erreur", description="Vous n'avez pas assez d'argent en poche pour cette mise.", color=discord.Color.red()))

        # Déduire la mise initialement
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, ctx.author.id))
        
        game = BlackjackGame(self, ctx.author.id, amt)
        game.start_game()
        self._blackjack_sessions[ctx.author.id] = game
        
        cur_emoji = self._currency_emoji(ctx)
        
        # Utiliser la version asynchrone de get_embed
        embed = await game.get_embed(ctx, cur_emoji)
        view = BlackjackView(self, game, ctx)
        
        msg = await ctx.send(embed=embed, view=view)
        game.message = msg


# --- Blackjack Game Logic ---

class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.value = self._get_value()
        self.emoji = self._get_emoji()

    def _get_value(self) -> int:
        if self.rank.isdigit():
            return int(self.rank)
        elif self.rank in ["J", "Q", "K"]:
            return 10
        elif self.rank == "A":
            return 11 # As commence à 11

    def _get_emoji(self) -> str:
        # Simplification des emojis pour garantir la compatibilité
        suit_emojis = {"♥": "♥", "♦": "♦", "♣": "♣", "♠": "♠"}
        return f"[{self.rank}{suit_emojis.get(self.suit, '')}]"

    def __str__(self) -> str:
        return self.emoji

class Deck:
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    SUITS = ["♥", "♦", "♣", "♠"]
    
    def __init__(self):
        self.cards = [Card(rank, suit) for rank in self.RANKS for suit in self.SUITS]
        import random
        random.shuffle(self.cards)

    def draw(self) -> Card:
        # S'assurer que le jeu ne plante pas s'il manque de cartes (même si peu probable en BJ)
        if not self.cards:
            self.__init__() # Réinitialiser/Mélanger
        return self.cards.pop()

class BlackjackGame:
    def __init__(self, cog: Economy, player_id: int, bet: int):
        self.cog = cog
        self.player_id = player_id
        self.bet = bet
        self.deck = Deck()
        self.player_hand: list[Card] = []
        self.dealer_hand: list[Card] = []
        self.ended = False
        self.message: discord.Message | None = None
        self.result: str = "Jeu en cours" # 'Jeu en cours', 'Blackjack', 'Gagné', 'Perdu', 'Égalité', 'Abandon'
        
        # Ajout des variables pour stocker le résultat du payout
        self.payout_details: tuple[int, int, str] | None = None # (winnings, bal_after, payout_status)

    def _calculate_hand_value(self, hand: list[Card]) -> int:
        value = sum(card.value for card in hand)
        num_aces = sum(1 for card in hand if card.rank == "A")
        
        # Ajuster les As (11 -> 1) si la main dépasse 21
        while value > 21 and num_aces > 0:
            value -= 10
            num_aces -= 1
        return value

    def start_game(self):
        # Distribution initiale
        self.player_hand.append(self.deck.draw())
        self.dealer_hand.append(self.deck.draw())
        self.player_hand.append(self.deck.draw())
        self.dealer_hand.append(self.deck.draw())
        
        # Vérifier le Blackjack initial
        if self.get_player_value() == 21:
            self.end_game("Blackjack")
            
    def get_player_value(self) -> int:
        return self._calculate_hand_value(self.player_hand)
    
    def get_dealer_value(self, reveal_all=False) -> int:
        if reveal_all:
            return self._calculate_hand_value(self.dealer_hand)
        # Ne montrer que la première carte du croupier
        return self.dealer_hand[0].value
        
    def hit(self):
        if self.ended: return
        self.player_hand.append(self.deck.draw())
        if self.get_player_value() > 21:
            self.end_game("Perdu") # Bust

    async def stand(self):
        if self.ended: return
        
        # Le croupier révèle sa deuxième carte
        # Pas d'action spécifique nécessaire ici, juste la boucle de tirage
        
        # Le croupier tire jusqu'à ce que sa main vaille 17 ou plus
        dealer_value = self._calculate_hand_value(self.dealer_hand)
        while dealer_value < 17:
            # Note: Le croupier tire immédiatement sans attendre l'utilisateur
            self.dealer_hand.append(self.deck.draw())
            dealer_value = self._calculate_hand_value(self.dealer_hand)

        player_value = self.get_player_value()
        
        if dealer_value > 21:
            self.end_game("Gagné") # Croupier Bust
        elif dealer_value > player_value:
            self.end_game("Perdu") # Croupier a une meilleure main
        elif dealer_value < player_value:
            self.end_game("Gagné") # Joueur a une meilleure main
        else:
            self.end_game("Égalité") # Push

    def end_game(self, result: Literal["Blackjack", "Gagné", "Perdu", "Égalité", "Abandon"]):
        self.ended = True
        self.result = result
    
    async def process_payout(self, cog: Economy):
        if not self.ended: return
        if self.payout_details: return self.payout_details # Déjà calculé
        
        user_id = self.player_id
        winnings = 0
        payout_status = ""
        
        # Récupérer la balance actuelle AVANT le payout pour les logs
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (user_id,))
                bal_before = (await cur.fetchone())[0]

        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if self.result == "Blackjack":
                    # Payout de 1.5x la mise (mise initiale + gain de 1.5x) -> 2.5 * bet
                    winnings = int(self.bet * 2.5) 
                    payout_status = "Blackjack! (Gain 1.5x)"
                elif self.result == "Gagné":
                    # Payout de 1x la mise (mise initiale + gain de 1x) -> 2 * bet
                    winnings = self.bet * 2
                    payout_status = "Victoire! (Gain 1x)"
                elif self.result == "Égalité":
                    # Mise rendue (Push) -> 1 * bet
                    winnings = self.bet
                    payout_status = "Égalité (Mise rendue)"
                elif self.result == "Perdu":
                    # Mise déjà déduite, ne rien rendre.
                    winnings = 0
                    payout_status = "Défaite"
                elif self.result == "Abandon":
                    # Demi-mise rendue (Surrender standard)
                    winnings = self.bet // 2
                    payout_status = "Abandon (Demi-mise rendue)"
                
                # Créditer les gains (si > 0)
                if winnings > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (winnings, user_id))
                    
                    # Log de la transaction (uniquement si le gain net est > 0 pour éviter le spam de transaction)
                    gain_net = winnings - self.bet if self.result not in ["Perdu", "Abandon"] and winnings > self.bet else 0
                    if self.result == "Blackjack":
                        gain_net = int(self.bet * 1.5)
                    
                    if gain_net > 0:
                        txid = cog._txn_id()
                        if cog.logs_enabled:
                            await cur.execute(
                                "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                                (txid, "win", user_id, user_id, gain_net, "balance", "won"),
                            )
                    
                # Récupérer le nouveau solde
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (user_id,))
                bal_after = (await cur.fetchone())[0]
        
        self.payout_details = (winnings, bal_after, payout_status)
        return self.payout_details

    # RENDU ASYNCHRONE
    async def get_embed(self, ctx: commands.Context, cur_emoji: str) -> discord.Embed:
        # Affichage des cartes
        player_cards = " ".join(str(c) for c in self.player_hand)
        player_value = self.get_player_value()
        
        # Déterminer les cartes et la valeur du croupier
        if not self.ended:
            # En jeu: cacher la deuxième carte du croupier
            dealer_cards = f"{self.dealer_hand[0]} [❓]"
            dealer_value_str = f"Valeur visible : {self.dealer_hand[0].value}"
            title = "♦️ Jeu de Blackjack en cours ♦️"
            color = discord.Color.blurple()
        else:
            # Fin de jeu: montrer toutes les cartes
            dealer_cards = " ".join(str(c) for c in self.dealer_hand)
            dealer_value = self.get_dealer_value(reveal_all=True)
            dealer_value_str = f"Valeur finale : **{dealer_value}**"
            
            if self.result == "Blackjack":
                title = "♣️ Blackjack ! ♣️"
                color = discord.Color.gold()
            elif self.result == "Gagné":
                title = "✅ Victoire du joueur ! ✅"
                color = discord.Color.green()
            elif self.result == "Perdu":
                title = "❌ Défaite du joueur ! ❌"
                color = discord.Color.red()
            elif self.result == "Égalité":
                title = "🤝 Égalité (Push) 🤝"
                color = discord.Color.dark_gray()
            else: # Abandon
                title = "🛑 Abandon"
                color = discord.Color.dark_gray()

        description = f"**Mise : {self.cog._fmt_amount(self.bet)} {cur_emoji}**\n\n"
        
        embed = self.cog._bank_embed(
            ctx,
            title=title,
            description=description,
            color=color,
            actor=ctx.author
        )
        
        # Champs d'information
        embed.add_field(name="🃏 Votre main", value=f"{player_cards}\nValeur : **{player_value}**", inline=True)
        embed.add_field(name="💻 Main du Croupier", value=f"{dealer_cards}\n{dealer_value_str}", inline=True)
        
        if self.ended:
            # Traiter le payout SEULEMENT à la fin de la partie
            final_payout_amount, final_balance, status_text = await self.process_payout(self.cog)
            
            # Calcul du gain net pour l'affichage
            if self.result == "Blackjack":
                gain_net = int(self.bet * 1.5)
            elif self.result == "Gagné":
                gain_net = self.bet
            elif self.result == "Égalité":
                gain_net = 0 # Mise rendue
            elif self.result == "Abandon":
                gain_net = - (self.bet - final_payout_amount) # Perte de la moitié de la mise
            else: # Perdu
                gain_net = -self.bet
            
            
            if self.result == "Perdu":
                payout_desc = f"Vous perdez votre mise de **{self.cog._fmt_amount(self.bet)} {cur_emoji}**."
            elif self.result == "Abandon":
                payout_desc = f"Vous abandonnez. **{self.cog._fmt_amount(final_payout_amount)} {cur_emoji}** (demi-mise) vous est rendu."
            elif self.result == "Égalité":
                payout_desc = f"Égalité. Votre mise de **{self.cog._fmt_amount(self.bet)} {cur_emoji}** vous est rendue."
            else:
                payout_desc = f"Gain net : **{self.cog._fmt_amount(gain_net)} {cur_emoji}** (Paiement total reçu: **{self.cog._fmt_amount(final_payout_amount)} {cur_emoji}**)."
            
            embed.description += f"**Résultat final : {status_text}**\n{payout_desc}"
            embed.add_field(name="💰 Solde après jeu", value=f"**{self.cog._fmt_amount(final_balance)} {cur_emoji}**", inline=False)
            
        return embed

# --- Blackjack View ---

class BlackjackView(discord.ui.View):
    def __init__(self, cog: Economy, game: BlackjackGame, ctx: commands.Context):
        super().__init__(timeout=90) # Augmentation du timeout
        self.cog = cog
        self.game = game
        self.ctx = ctx
        self.cur_emoji = cog._currency_emoji(ctx)
        
        if game.ended:
            for item in self.children:
                item.disabled = True
            self.stop() # Arrêter la vue si le jeu est déjà terminé

    async def on_timeout(self) -> None:
        if not self.game.ended:
            self.game.end_game("Abandon")
            try:
                # Calcul du résultat final
                embed = await self.game.get_embed(self.ctx, self.cur_emoji)
                
                # Désactiver les boutons et éditer le message
                for item in self.children:
                    item.disabled = True
                await self.game.message.edit(embed=embed, view=self)
                self.cog._blackjack_sessions.pop(self.game.player_id, None)
            except Exception:
                pass # Ignorer les erreurs si le message est déjà supprimé

    async def update_message(self, interaction: discord.Interaction):
        # Assurer que l'embed est asynchrone
        embed = await self.game.get_embed(self.ctx, self.cur_emoji)
        
        if self.game.ended:
            for item in self.children:
                item.disabled = True
            
            # Suppression de la session de jeu du cache après la fin
            self.cog._blackjack_sessions.pop(self.game.player_id, None)
            
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.game.player_id:
            await interaction.response.send_message("Seul le joueur ayant initié la partie peut interagir.", ephemeral=True)
            return False
        if self.game.ended:
            await interaction.response.send_message("La partie est terminée.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Tirer (Hit)", style=discord.ButtonStyle.green)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game.hit()
        await self.update_message(interaction)

    @discord.ui.button(label="Rester (Stand)", style=discord.ButtonStyle.red)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Le stand doit être await car il contient la logique du croupier et la fin de jeu
        await self.game.stand()
        await self.update_message(interaction)
        
    @discord.ui.button(label="Abandonner (Surrender)", style=discord.ButtonStyle.blurple)
    async def surrender_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.game.end_game("Abandon")
        await self.update_message(interaction)


# --- Les autres classes du fichier (Mines, CoinFlip, etc.) ---

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
                    return await interaction.response.send_message("Seul l’initiateur peut jouer.", ephemeral=True)
                s = self.cog._mines_sessions.get(self.session_owner_id)
                if not s or s.get("ended"):
                    return await interaction.response.send_message("Partie terminée.")
                if idx in s["revealed"]:
                    return await interaction.response.send_message("Déjà révélé.")
                s["revealed"].add(idx)
                try:
                    await interaction.response.defer()
                except Exception:
                    pass
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
                    # Utilisation de _fmt_amount
                    full_desc = (
                        ":boom: __**Vous êtes tombé sur la mine !**__\n\n"
                        f"Vous avez perdu {self.cog._fmt_amount(s['bet'])} {cur_emoji}\n\n"
                        f"Votre solde actuel s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji}**"
                    )
                    emb = self.cog._bank_embed(self.ctx, title="Casino • Mines", description=full_desc, color=discord.Color.red())
                    try:
                        await interaction.message.edit(embed=emb, view=None)
                    except Exception:
                        pass
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
                # Utilisation de _fmt_amount
                desc = (
                    f"Votre mise : {self.cog._fmt_amount(s['bet'])} {cur_emoji} • Nombre de mines : {s['mines']}\n"
                    f"Cases révélées : {len(s['revealed'])} • Gain potentiel : {self.cog._fmt_amount(potential)} {cur_emoji}"
                )
                emb = self.cog._bank_embed(self.ctx, title="Casino • Mines", description=desc, color=discord.Color.blurple())
                try:
                    await interaction.message.edit(embed=emb, view=self)
                except Exception:
                    pass
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
            return await interaction.response.send_message("Seul l’initiateur peut encaisser.", ephemeral=True)
        s = self.cog._mines_sessions.get(self.session_owner_id)
        if not s or s.get("ended"):
            return await interaction.response.send_message("Partie terminée.", ephemeral=True)
        try:
            await interaction.response.defer()
        except Exception:
            pass
        payout = max(1, int(s["bet"] * s["mult"] * 0.95))
        txid = None
        await self.cog._connect(); await self.cog._ensure_user(self.session_owner_id)
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (payout, self.session_owner_id))
                txid = self.cog._txn_id()
                if self.cog.logs_enabled:
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
        # Utilisation de _fmt_amount
        full_desc = (
            ":moneybag: __**Encaissement**__\n\n"
            f"Vous gagnez {self.cog._fmt_amount(payout)} {cur_emoji}\n\n"
            f"Votre solde actuel s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji}**"
        )
        emb = self.cog._bank_embed(self.ctx, title="Casino • Mines", description=full_desc, color=discord.Color.green(), txn_id=txid)
        try:
            await interaction.message.edit(embed=emb, view=None)
        except Exception:
            pass
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
            return await interaction.response.send_message("Seul l’initiateur peut annuler.", ephemeral=True)
        s = self.cog._mines_sessions.get(self.session_owner_id)
        if not s or s.get("ended"):
            return await interaction.response.send_message("Partie terminée.", ephemeral=True)
        try:
            await interaction.response.defer()
        except Exception:
            pass
        self.cog._mines_sessions[self.session_owner_id]["ended"] = True
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (self.session_owner_id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = self.cog._currency_emoji(self.ctx)
        # Utilisation de _fmt_amount
        full_desc = (
            ":stop_sign: __**Partie annulée**__\n\n"
            f"Votre solde actuel s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji}**"
        )
        emb = self.cog._bank_embed(self.ctx, title="Casino • Mines", description=full_desc, color=discord.Color.dark_gray())
        try:
            await interaction.message.edit(embed=emb, view=None)
        except Exception:
            pass
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
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Choix: Pile • Mise: {self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="Face", style=discord.ButtonStyle.primary)
    async def face(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.side = "face"
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Choix: Face • Mise: {self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="10", style=discord.ButtonStyle.secondary)
    async def bet10(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 10
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Mise: {self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary)
    async def bet50(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 50
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Mise: {self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="100", style=discord.ButtonStyle.secondary)
    async def bet100(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 100
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Coin Flip", description=f"Mise: {self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}", color=discord.Color.blurple()))

    @discord.ui.button(label="Jouer", style=discord.ButtonStyle.success)
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Seul l’initiateur peut jouer.", ephemeral=True)
        if not self.side:
            return await interaction.response.send_message("Choisis Pile ou Face.")
        ctx = self.ctx
        await self.cog._ensure_user(ctx.author.id)
        import random
        txid = None
        try:
            await interaction.response.defer()
        except Exception:
            pass
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
                    if self.cog.logs_enabled:
                        await cur.execute(
                            "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (txid, "win", ctx.author.id, ctx.author.id, self.amount, "balance", "won"),
                        )
                    desc = f"Coin flip: {flip}. Gagné +{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (self.amount, ctx.author.id))
                    desc = f"Coin flip: {flip}. Perdu -{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.red()
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur2:
                await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_after = (await cur2.fetchone())[0]
        cur_emoji = self.cog._currency_emoji(ctx)
        # Utilisation de _fmt_amount
        outcome_line = f":tada: __**Vous avez gagné {self.cog._fmt_amount(self.amount)} {cur_emoji} Fcoins !**__" if txid else f":x: **Vous avez perdu {self.cog._fmt_amount(self.amount)} {cur_emoji} Fcoins**"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Tirage: {flip}\n\n{outcome_line}\n\nVotre solde s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**{extra_id}"
        emb = self.cog._bank_embed(self.ctx, title="Casino • Pile ou Face", description=full_desc, color=color, txn_id=txid)
        try:
            await interaction.message.edit(embed=emb, view=None)
        except Exception:
            pass

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
            return await interaction.response.send_message("Seule la personne ping peut répondre.", ephemeral=True)
        await self.cog._ensure_user(self.ctx.author.id); await self.cog._ensure_user(self.target.id)
        try:
            await interaction.response.defer()
        except Exception:
            pass
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
                if self.cog.logs_enabled:
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "win", winner.id, winner.id, gain, "balance", "won"),
                    )
        cur_emoji = self.cog._currency_emoji(self.ctx)
        # Utilisation de _fmt_amount
        desc = f"Course Scoot • Mise: {self.cog._fmt_amount(self.amount)} {cur_emoji} chacun\nGagnant: {winner.mention} (+{self.cog._fmt_amount(gain)} {cur_emoji})"
        emb = self.cog._bank_embed(self.ctx, title="Scoot", description=desc, color=discord.Color.green(), txn_id=txid)
        try:
            await interaction.message.edit(embed=emb, view=None)
        except Exception:
            pass

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("Seule la personne ping peut répondre.", ephemeral=True)
        try:
            await interaction.response.defer()
        except Exception:
            pass
        emb = self.cog._bank_embed(self.ctx, title="Scoot", description=f"Refusé par {self.target.mention}", color=discord.Color.red())
        try:
            await interaction.message.edit(embed=emb, view=None)
        except Exception:
            pass

class SlotsView(discord.ui.View):
    def __init__(self, cog: Economy, ctx: commands.Context):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.amount: int = 10

    @discord.ui.button(label="10", style=discord.ButtonStyle.secondary)
    async def bet10(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 10
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=f"🎰 Mise: **{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary)
    async def bet50(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 50
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=f"🎰 Mise: **{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="100", style=discord.ButtonStyle.secondary)
    async def bet100(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 100
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=f"🎰 Mise: **{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="Spin", style=discord.ButtonStyle.success)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = self.ctx
        await self.cog._ensure_user(ctx.author.id)
        import random
        reels = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
        txid = None
        try:
            await interaction.response.defer()
        except Exception:
            pass
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
                    if self.cog.logs_enabled:
                        await cur.execute(
                            "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (txid, "win", ctx.author.id, ctx.author.id, win, "balance", "won"),
                        )
                    desc = f"Slots {' | '.join(r)} — Gagné +{self.cog._fmt_amount(win)} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (self.amount, ctx.author.id))
                    desc = f"Slots {' | '.join(r)} — Perdu -{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.red()
        cur_emoji = self.cog._currency_emoji(ctx)
        if txid:
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                    bal_after = (await cur.fetchone())[0]
            # Utilisation de _fmt_amount
            outcome_line = f":tada: __**Vous avez gagné {self.cog._fmt_amount(win)} {cur_emoji} Fcoins !**__"
            extra_id = f"\n\nID: {txid}" if txid else ""
            full_desc = f"Résultats: {' | '.join(r)}\n\n{outcome_line}\n\nVotre solde s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**{extra_id}"
            emb = self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=full_desc, color=color, txn_id=txid)
        else:
            # Utilisation de _fmt_amount
            outcome_line = f":x: **Vous avez perdu {self.cog._fmt_amount(self.amount)} {cur_emoji} Fcoins**"
            full_desc = f"Résultats: {' | '.join(r)}\n\n{outcome_line}"
            emb = self.cog._bank_embed(self.ctx, title="Casino • Machines à sous", description=full_desc, color=color)
        try:
            await interaction.message.edit(embed=emb, view=None)
        except Exception:
            pass

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
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Mise: **{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="50", style=discord.ButtonStyle.secondary)
    async def bet50(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 50
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Mise: **{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="100", style=discord.ButtonStyle.secondary)
    async def bet100(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.amount = 100
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Mise: **{self.cog._fmt_amount(self.amount)} {self.cog._currency_emoji(self.ctx)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="Pair", style=discord.ButtonStyle.primary)
    async def pair(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parity = "pair"
        self.bet_on = None
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Pari: **Pair** • Mise: **{self.cog._fmt_amount(self.amount)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="Impair", style=discord.ButtonStyle.primary)
    async def impair(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parity = "impair"
        self.bet_on = None
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Pari: **Impair** • Mise: **{self.cog._fmt_amount(self.amount)}**", color=discord.Color.blurple()))

    @discord.ui.select(placeholder="Choisis un nombre", options=[discord.SelectOption(label=str(i), value=str(i)) for i in range(1,7)])
    async def choose_number(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.bet_on = int(select.values[0])
        self.parity = None
        await interaction.response.edit_message(embed=self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=f":game_die: Pari: **{self.bet_on}** • Mise: **{self.cog._fmt_amount(self.amount)}**", color=discord.Color.blurple()))

    @discord.ui.button(label="Jouer", style=discord.ButtonStyle.success)
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = self.ctx
        await self.cog._ensure_user(ctx.author.id)
        import random
        txid = None
        try:
            await interaction.response.defer()
        except Exception:
            pass
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
                    if self.cog.logs_enabled:
                        await cur.execute(
                            "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (txid, "win", ctx.author.id, ctx.author.id, win, "balance", "won"),
                        )
                    desc = f"Dé {roll} — Gagné +{self.cog._fmt_amount(win)} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.green()
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (-win, ctx.author.id))
                    desc = f"Dé {roll} — Perdu -{self.cog._fmt_amount(abs(win))} {self.cog._currency_emoji(ctx)}"
                    color = discord.Color.red()
        if txid:
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                    bal_after = (await cur.fetchone())[0]
            cur_emoji = self.cog._currency_emoji(ctx)
            # Utilisation de _fmt_amount
            gain_line = f"**Vous avez gagné {self.cog._fmt_amount(win)} {cur_emoji} Fcoins**" if win > 0 else f"**Vous avez perdu {self.cog._fmt_amount(abs(win))} {cur_emoji} Fcoins**"
            extra_id = f"\n\nID: {txid}" if txid else ""
            full_desc = f"Le dé est tombé sur : {roll} :game_die:\n\n{gain_line}\n\nVotre solde s'estime à : **{self.cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**{extra_id}"
            emb = self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=full_desc, color=color, txn_id=txid)
        else:
            # Utilisation de _fmt_amount
            full_desc = f"Le dé est tombé sur : {roll} :game_die:\n\n**Vous avez perdu {self.cog._fmt_amount(abs(win))} {cur_emoji} Fcoins**"
            emb = self.cog._bank_embed(self.ctx, title="Casino • Jeu du dé", description=full_desc, color=color)
        try:
            await interaction.message.edit(embed=emb, view=None)
        except Exception:
            pass

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
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Seul l’initiateur peut jouer.")
        await self.cog._ensure_user(self.ctx.author.id)
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (self.ctx.author.id,))
                bal = (await cur.fetchone())[0]
        if bal < self.base_amt:
            return await interaction.response.send_message("Pas assez en poche.")
        try:
            await interaction.response.defer()
        except Exception:
            pass
        import random
        busts = [0.20, 0.35, 0.50, 0.65, 0.80]
        mults = [1.5, 2.0, 2.5, 3.0, 3.5]
        p = busts[self.step] if self.step < len(busts) else 0.90
        m_next = mults[self.step] if self.step < len(mults) else (self.mult + 0.5)
        if random.random() < p:
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (self.base_amt, self.ctx.author.id))
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur2:
                    await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (self.ctx.author.id,))
                    bal_after = (await cur2.fetchone())[0]
            cur_emoji = self.cog._currency_emoji(self.ctx)
            emb = self.cog._bank_embed(
                self.ctx,
                title="Casino • Échelle Push Your Luck",
                description=f"**Mise : {self.cog._fmt_amount(self.base_amt)} {cur_emoji}**",
                color=discord.Color.red(),
            )
            emb.add_field(name="État", value="Bust instantané", inline=True)
            emb.add_field(name="Perte", value=f"-{self.cog._fmt_amount(self.base_amt)} {cur_emoji}", inline=True)
            emb.add_field(name="Solde après jeu", value=f"**{self.cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**", inline=False)
            try:
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(embed=emb, view=None)
            except Exception:
                pass
            self.stop()
            return
        self.mult = m_next
        self.step += 1
        cur_emoji = self.cog._currency_emoji(self.ctx)
        potential = int(self.base_amt * self.mult * 0.95)
        emb = self.cog._bank_embed(
            self.ctx,
            title="Casino • Échelle Push Your Luck",
            description=f"**Mise : {self.cog._fmt_amount(self.base_amt)} {cur_emoji}**",
            color=discord.Color.blurple(),
        )
        emb.add_field(name="Étape", value=str(self.step), inline=True)
        emb.add_field(name="Multiplicateur", value=f"x{self.mult:.2f}", inline=True)
        emb.add_field(name="Risque bust", value=f"{int(p*100)}%", inline=True)
        emb.add_field(name="Gain potentiel", value=f"{self.cog._fmt_amount(potential)} {cur_emoji}", inline=False)
        try:
            await interaction.message.edit(embed=emb, view=self)
        except Exception:
            pass

    @discord.ui.button(label="Encaisser", style=discord.ButtonStyle.primary)
    async def cash(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("Seul l’initiateur peut encaisser.", ephemeral=True)
        await self.cog._ensure_user(self.ctx.author.id)
        payout = max(1, int(self.base_amt * self.mult * 0.95))
        txid = None
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (payout, self.ctx.author.id))
                txid = self.cog._txn_id()
                if self.cog.logs_enabled:
                    await cur.execute("INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)", (txid, "win", self.ctx.author.id, self.ctx.author.id, payout, "balance", "won"))
        async with self.cog.pool.acquire() as conn:
            async with conn.cursor() as cur2:
                await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (self.ctx.author.id,))
                bal_after = (await cur2.fetchone())[0]
        cur_emoji = self.cog._currency_emoji(self.ctx)
        emb = self.cog._bank_embed(
            self.ctx,
            title="Casino • Échelle Push Your Luck",
            description=f"**Mise : {self.cog._fmt_amount(self.base_amt)} {cur_emoji}**",
            color=discord.Color.green(),
            txn_id=txid,
        )
        emb.add_field(name="Étapes franchies", value=str(self.step), inline=True)
        emb.add_field(name="Gain", value=f"+{self.cog._fmt_amount(payout)} {cur_emoji}", inline=True)
        emb.add_field(name="Solde après jeu", value=f"**{self.cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**", inline=False)
        try:
            for item in self.children:
                item.disabled = True
            try:
                await interaction.response.defer()
            except Exception:
                pass
            await interaction.message.edit(embed=emb, view=None)
        except Exception:
            pass
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Seul l’initiateur peut interagir.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        try:
            for item in self.children:
                item.disabled = True
            cur_emoji = self.cog._currency_emoji(self.ctx)
            emb = self.cog._bank_embed(
                self.ctx,
                title="Casino • Échelle Push Your Luck",
                description=f"**Mise : {self.cog._fmt_amount(self.base_amt)} {cur_emoji}**",
                color=discord.Color.dark_gray(),
            )
            emb.add_field(name="État", value="Temps écoulé", inline=True)
            target_msg = getattr(self, "message", None)
            if target_msg:
                await target_msg.edit(embed=emb, view=None)
        except Exception:
            pass
        self.stop()

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
            return await interaction.response.send_message("Non autorisé.", ephemeral=True)
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
            return await interaction.response.send_message("Non autorisé.", ephemeral=True)
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
    async def scoot(self, ctx: commands.Context, member: discord.Member, amount: str):
        await self._connect(); await self._ensure_user(ctx.author.id); await self._ensure_user(member.id)
        if member.id == ctx.author.id:
            return await ctx.send("Choisis quelqu’un d’autre.")
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                bal_user = (await cur.fetchone())[0]
        amt = self._parse_bet_amount(amount, bal_user)
        
        if amt <= 0:
            return await ctx.send("Montant invalide.")
        if bal_user < amt:
            return await ctx.send("Pas assez en poche.")
            
        view = ScootRaceView(self, ctx, member, amt)
        cur_emoji = self._currency_emoji(ctx)
        # Utilisation de _fmt_amount
        emb = self._bank_embed(ctx, title="Scoot", description=f"{ctx.author.mention} défie {member.mention}. Mise: {self._fmt_amount(amt)} {cur_emoji} chacun.", color=discord.Color.blurple())
        await ctx.send(embed=emb, view=view)

    @commands.command(name="khedma", help="Travaille et gagne 100. Cooldown 5 minutes.")
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5*60), commands.BucketType.user)
    async def khedma(self, ctx: commands.Context):
        await self._connect(); await self._ensure_user(ctx.author.id)
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance+100 WHERE user_id=%s", (ctx.author.id,))
        cur_emoji = self._currency_emoji(ctx)
        emb = self._bank_embed(ctx, title="Khedma", description=f"+{self._fmt_amount(100)} {cur_emoji}", color=discord.Color.green(), actor=ctx.author)
        await ctx.send(embed=emb)

    # Alias goût local
    @commands.command(name="khadma", aliases=["khadema", "khdma", "khedma2"])  
    @commands.dynamic_cooldown(lambda ctx: None if getattr(ctx.author, "guild_permissions", None) and ctx.author.guild_permissions.administrator else commands.Cooldown(1, 5*60), commands.BucketType.user)
    async def khadma(self, ctx: commands.Context):
        await self.khedma(ctx)

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
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(ctx, title=f"Solde de {member.display_name}", color=discord.Color.gold(), fields=[("Poche", f"{cog._fmt_amount(bal)} {cur}", True), ("Banque", f"{cog._fmt_amount(bank)} {cur}", True)], actor=member)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="send", description="Envoyer de l’argent")
    async def send_slash(interaction: discord.Interaction, member: discord.Member, amount: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id); await cog._ensure_user(member.id)
        
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                amount_int = cog._parse_bet_amount(amount, bal)
        
        if amount_int <= 0:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        if bal < amount_int:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amount_int, interaction.user.id))
                await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount_int, member.id))
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(ctx, title="Virement", color=discord.Color.purple(), fields=[("De", interaction.user.mention, True), ("Vers", member.mention, True), ("Montant", f"{cog._fmt_amount(amount_int)} {cur_emoji}", True)], txn_id=cog._txn_id())
        await interaction.response.send_message(embed=emb)

    @tree.command(name="deposit", description="Déposer à la banque")
    async def deposit_slash(interaction: discord.Interaction, amount: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance, bank FROM users WHERE user_id=%s", (interaction.user.id,))
                bal, bank = await cur.fetchone()
                amt = cog._parse_bet_amount(amount, bal)
                
                if amt <= 0:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                if bal < amt:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                bal -= amt; bank += amt
                await cur.execute("UPDATE users SET balance=%s, bank=%s WHERE user_id=%s", (bal, bank, interaction.user.id))
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        # Utilisation de _fmt_amount
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
                amt = cog._parse_bet_amount(amount, bank)
                
                if amt <= 0:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                if bank < amt:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez à la banque.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                bank -= amt; bal += amt
                await cur.execute("UPDATE users SET balance=%s, bank=%s WHERE user_id=%s", (bal, bank, interaction.user.id))
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        # Utilisation de _fmt_amount
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
                    # Utilisation de _fmt_amount
                    emb = cog._bank_embed(ctx, title=f"Infos {item}", color=discord.Color.teal(), fields=[("Prix d’achat", f"{cog._fmt_amount(buy)} {cur_emoji}", True), ("Prix de vente", f"{cog._fmt_amount(sell)} {cur_emoji}", True)], actor=interaction.user)
                    return await interaction.response.send_message(embed=emb)
                await cur.execute("SELECT item, buy_price, sell_price FROM shop ORDER BY buy_price ASC")
                rows = await cur.fetchall()
        ctx = _SlashCtx(interaction); cur_emoji = cog._currency_emoji(ctx)
        # Utilisation de _fmt_amount
        desc = "\n".join([f"{i} — buy {cog._fmt_amount(bp)} / sell {cog._fmt_amount(sp)} {cur_emoji}" for i, bp, sp in rows]) or "Shop vide."
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
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(ctx, title="Achat", color=discord.Color.green(), fields=[("Article", item_name, True), ("Prix", f"{cog._fmt_amount(price)} {cur_emoji}", True), ("Acheteur", interaction.user.mention, True)], txn_id=cog._txn_id(), actor=interaction.user)
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
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(ctx, title="Vente", color=discord.Color.orange(), fields=[("Article", item_name, True), ("Prix", f"{cog._fmt_amount(price)} {cur_emoji}", True), ("Vendeur", interaction.user.mention, True)], txn_id=cog._txn_id(), actor=interaction.user)
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
        
        ctx = _SlashCtx(interaction)
        cur = cog._currency_emoji(ctx)
        
        # Amélioration de l'embed du leaderboard (même logique que la commande +lb)
        if not rows:
            desc = "Aucun joueur dans le classement pour l'instant."
            color = discord.Color.blurple()
        else:
            description_lines = [f"**#{i+1}** <@{uid}> — **{cog._fmt_amount(total)} {cur}**" for i, (uid, total) in enumerate(rows)]
            desc = "\n".join(description_lines)
            color = discord.Color.gold()
        
        emb = cog._bank_embed(
            ctx, 
            title=f"🥇 Classement des {len(rows)} meilleurs joueurs 🏆", 
            description=desc, 
            color=color
        )
        emb.set_footer(text="Basé sur le solde total (poche + banque).")
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
        # Utilisation de _fmt_amount
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
        # Utilisation de _fmt_amount
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
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(_SlashCtx(interaction), title="Crédit mensuel", color=discord.Color.green(), fields=[("Montant", f"+{cog._fmt_amount(reward)} {cur_emoji}", True), ("Bénéficiaire", interaction.user.mention, True)], txn_id=cog._txn_id(), actor=interaction.user)
        await interaction.response.send_message(embed=emb)
        
    @tree.command(name="blackjack", description="Jeu de Blackjack contre le croupier")
    @app_commands.checks.cooldown(1, 5)
    async def blackjack_slash(interaction: discord.Interaction, amount: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        
        if interaction.user.id in cog._blackjack_sessions and not cog._blackjack_sessions[interaction.user.id].ended:
            return await interaction.response.send_message(embed=cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Vous avez déjà une partie de Blackjack en cours ! Terminez-la ou attendez qu'elle expire.", color=discord.Color.red()))

        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_user = (await cur.fetchone())[0]
        
        amt = cog._parse_bet_amount(amount, bal_user)
        
        if amt <= 0:
            return await interaction.response.send_message(embed=cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant de mise invalide.", color=discord.Color.red()))
        if bal_user < amt:
            return await interaction.response.send_message(embed=cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Vous n'avez pas assez d'argent en poche pour cette mise.", color=discord.Color.red()))

        # Déduire la mise initialement
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, interaction.user.id))
        
        game = BlackjackGame(cog, interaction.user.id, amt)
        game.start_game()
        cog._blackjack_sessions[interaction.user.id] = game
        
        ctx = _SlashCtx(interaction)
        cur_emoji = cog._currency_emoji(ctx)
        
        # Utiliser la version asynchrone de get_embed
        embed = await game.get_embed(ctx, cur_emoji)
        view = BlackjackView(cog, game, ctx)
        
        await interaction.response.send_message(embed=embed, view=view)
        # Assigner le message envoyé à la session de jeu
        game.message = await interaction.original_response()

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
        # Utilisation de _fmt_amount
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
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(_SlashCtx(interaction), title="Vol", color=discord.Color.dark_gold(), fields=[("Voleur", interaction.user.mention, True), ("Victime", member.mention, True), ("Montant", f"-{cog._fmt_amount(amount)} {cur_emoji} pour la victime", False)], txn_id=cog._txn_id())
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
                if cog.logs_enabled:
                    await cur.execute(
                        "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                        (txid, "credit", interaction.user.id, member.id, amount, col, "pending"),
                    )
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        # Utilisation de _fmt_amount
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
        # Utilisation de _fmt_amount
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
        try:
            await interaction.response.defer(thinking=True)
        except Exception:
            pass
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
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(ctx, title="Khedma", description=f"+{cog._fmt_amount(100)} {cur}", color=discord.Color.green(), actor=interaction.user)
        try:
            await interaction.followup.send(embed=emb)
        except Exception:
            # Fallback si pas de defer
            await interaction.response.send_message(embed=emb)

    @tree.command(name="scoot", description="Course scoot avec pari symétrique")
    @app_commands.checks.cooldown(1, 5)
    async def scoot_slash(interaction: discord.Interaction, membre: discord.Member, montant: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id); await cog._ensure_user(membre.id)
        if interaction.user.id == membre.id:
            return await interaction.response.send_message("Choisis quelqu’un d’autre.")
        
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_user = (await cur.fetchone())[0]
        amt = cog._parse_bet_amount(montant, bal_user)
        
        if amt <= 0:
            return await interaction.response.send_message("Montant invalide.")
        if bal_user < amt:
            return await interaction.response.send_message("Pas assez en poche.")
            
        view = ScootRaceView(cog, _SlashCtx(interaction), membre, amt)
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(_SlashCtx(interaction), title="Scoot", description=f"{interaction.user.mention} défie {membre.mention}. Mise: {cog._fmt_amount(amt)} {cur_emoji} chacun.", color=discord.Color.blurple())
        await interaction.response.send_message(embed=emb, view=view)
        try:
            view.message = await interaction.original_response()
        except Exception:
            pass

    @tree.command(name="coinflip", description="Pile/Face avec mise")
    @app_commands.checks.cooldown(1, 5)
    async def coinflip_slash(interaction: discord.Interaction, side: str, amount: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        s = (side or "").lower()
        if s not in ("pile", "face"):
            return await interaction.response.send_message("Choisis 'pile' ou 'face'.")
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
        amt = cog._parse_bet_amount(str(amount), bal)
        if amt <= 0:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        import random
        txid = None
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if bal < amt:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                flip = random.choice(["pile", "face"])
                if flip == s:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amt, interaction.user.id))
                    txid = cog._txn_id()
                    if cog.logs_enabled:
                        await cur.execute(
                            "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (txid, "win", interaction.user.id, interaction.user.id, amt, "balance", "won"),
                        )
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, interaction.user.id))
        ctx = _SlashCtx(interaction)
        cur = cog._currency_emoji(ctx)
        won = txid is not None
        # Utilisation de _fmt_amount
        desc = f"Coin flip: {flip}. {'Gagné +' + cog._fmt_amount(amt) if won else 'Perdu -' + cog._fmt_amount(amt)} {cur}"
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
            fields=[("Solde", f"{cog._fmt_amount(bal_after)} {cur}", True)], # Utilisation de _fmt_amount
        )
        await interaction.response.send_message(embed=emb)

    @tree.command(name="slots", description="Machines à sous avec mise")
    @app_commands.checks.cooldown(1, 5)
    async def slots_slash(interaction: discord.Interaction, amount: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_user = (await cur.fetchone())[0]
        amt = cog._parse_bet_amount(str(amount), bal_user)
        if amt <= 0:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        import random
        reels = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
        txid = None
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                if bal < amt:
                    return await interaction.response.send_message("Pas assez en poche.")
                r = [random.choice(reels) for _ in range(3)]
                unique = len(set(r))
                if unique == 1:
                    win = amt * 8
                elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
                    win = int(amt * 1.8)
                else:
                    win = 0
                if win > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win, interaction.user.id))
                    txid = cog._txn_id()
                    if cog.logs_enabled:
                        await cur.execute(
                            "INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                            (txid, "win", interaction.user.id, interaction.user.id, win, "balance", "won"),
                        )
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, interaction.user.id))
        ctx = _SlashCtx(interaction)
        cur = cog._currency_emoji(ctx)
        color = discord.Color.green() if win > 0 else discord.Color.red()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur2:
                await cur2.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_after = (await cur2.fetchone())[0]
        # Utilisation de _fmt_amount
        outcome_line = f":tada: __**Vous avez gagné {cog._fmt_amount(win)} {cur} Fcoins !**__" if win > 0 else f":x: **Vous avez perdu {cog._fmt_amount(amt)} {cur} Fcoins**"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Résultats: {' | '.join(r)}\n\n{outcome_line}\n\nVotre solde s'estime à : **{cog._fmt_amount(bal_after)} {cur} Fcoins**{extra_id}"
        emb = cog._bank_embed(ctx, title="Casino • Machines à sous", description=full_desc, color=color, txn_id=txid)
        await interaction.response.send_message(embed=emb)

    @tree.command(name="dice", description="Pari pair/impair ou sur un chiffre")
    @app_commands.checks.cooldown(1, 5)
    async def dice_slash(interaction: discord.Interaction, amount: str, bet_on: int | None = None):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
        if bet_on is not None and not (1 <= bet_on <= 6):
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Parie sur un nombre entre 1 et 6.", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        import random
        txid = None
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                amt = cog._parse_bet_amount(str(amount), bal)
                if amt <= 0:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Montant invalide.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                if bal < amt:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
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
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win, interaction.user.id))
                    txid = cog._txn_id()
                    if cog.logs_enabled:
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
        # Utilisation de _fmt_amount
        gain_line = f":tada: __**Vous avez gagné {cog._fmt_amount(win)} {cur} Fcoins !**__" if win > 0 else f":x: **Vous avez perdu {cog._fmt_amount(abs(win))} {cur} Fcoins**"
        extra_id = f"\n\nID: {txid}" if txid else ""
        full_desc = f"Le dé est tombé sur : {roll} :game_die:\n\n{gain_line}\n\nVotre solde s'estime à : **{cog._fmt_amount(bal_after2)} {cur} Fcoins**{extra_id}"
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
        await interaction.response.send_message(f"Taxe appliquée: {cog._fmt_amount(tax_real)}") # Utilisation de _fmt_amount
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
        # Utilisation de _fmt_amount
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
        # Utilisation de _fmt_amount
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
        LADDER_MIN = 1000
        LADDER_MAX = min(bal_user, 1_000_000)
        if amt < LADDER_MIN:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description=f"Mise minimale: {cog._fmt_amount(LADDER_MIN)} {cog._currency_emoji(_SlashCtx(interaction))}", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        if amt > LADDER_MAX:
            emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description=f"Mise maximale: {cog._fmt_amount(LADDER_MAX)} {cog._currency_emoji(_SlashCtx(interaction))}", color=discord.Color.red())
            return await interaction.response.send_message(embed=emb)
        view = LadderView(cog, _SlashCtx(interaction), amt)
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        # Utilisation de _fmt_amount
        emb = cog._bank_embed(_SlashCtx(interaction), title="Casino • Échelle Push Your Luck", description=f"Mise initiale: **{cog._fmt_amount(amt)} {cur_emoji}**\nChoisis 'Continuer' pour augmenter ton gain ou 'Encaisser' pour récupérer ton gain actuel.", color=discord.Color.blurple())
        await interaction.response.send_message(embed=emb, view=view)

    # système de bourse retiré
    async def bourse_slash(interaction: discord.Interaction, name: str):
        await interaction.response.send_message("Système de bourse retiré.")

    @tree.command(name="roulette", description="Roulette européenne")
    @app_commands.checks.cooldown(1, 5)
    async def roulette_slash(interaction: discord.Interaction, amount: str, bet: str):
        cog: Economy = bot.get_cog("Economy")
        await cog._connect(); await cog._ensure_user(interaction.user.id)
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
        b = bet.strip().lower()
        kind = None; value = None
        if b in ("rouge", "red"):
            kind = "color"; value = "red"
        elif b in ("noir", "black"):
            kind = "color"; value = "black"
        elif b in ("pair", "even"):
            kind = "parity"; value = "even"
        elif b in ("impair", "odd"):
            kind = "parity"; value = "odd"
        elif b in ("1-18", "bas"):
            kind = "range"; value = (1, 18)
        elif b in ("19-36", "haut"):
            kind = "range"; value = (19, 36)
        elif b in ("1st", "premier"):
            kind = "dozen"; value = 1
        elif b in ("2nd", "deuxième"):
            kind = "dozen"; value = 2
        elif b in ("3rd", "troisième"):
            kind = "dozen"; value = 3
        else:
            try:
                num = int(b)
                if not (0 <= num <= 36):
                    raise ValueError
                kind = "number"; value = num
            except Exception:
                emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pari invalide.", color=discord.Color.red())
                return await interaction.response.send_message(embed=emb)
        import random
        wheel_red = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        n = random.randint(0, 36)
        win_amt = 0
        if kind == "color":
            is_red = n in wheel_red
            ok = (value == "red" and is_red) or (value == "black" and n != 0 and not is_red)
            win_amt = int(amt * 2) if ok else -amt
        elif kind == "parity":
            ok = (n != 0 and (n % 2 == 0 and value == "even" or n % 2 == 1 and value == "odd"))
            win_amt = int(amt * 2) if ok else -amt
        elif kind == "range":
            ok = (value[0] <= n <= value[1])
            win_amt = int(amt * 2) if ok else -amt
        elif kind == "dozen":
            group = 1 if (1 <= n <= 12) else 2 if (13 <= n <= 24) else 3 if (25 <= n <= 36) else 0
            ok = (group == value)
            win_amt = int(amt * 3) if ok else -amt
        elif kind == "number":
            ok = (n == value)
            win_amt = int(amt * 36) if ok else -amt
        txid = None
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal = (await cur.fetchone())[0]
                if bal < amt:
                    emb = cog._bank_embed(_SlashCtx(interaction), title="Erreur", description="Pas assez en poche.", color=discord.Color.red())
                    return await interaction.response.send_message(embed=emb)
                if win_amt > 0:
                    await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (win_amt, interaction.user.id))
                    txid = cog._txn_id()
                    if cog.logs_enabled:
                        await cur.execute("INSERT INTO transactions(id,type,requester_id,target_id,amount,account,status) VALUES(%s,%s,%s,%s,%s,%s,%s)", (txid, "win", interaction.user.id, interaction.user.id, win_amt, "balance", "won"))
                else:
                    await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (-win_amt, interaction.user.id))
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (interaction.user.id,))
                bal_after = (await cur.fetchone())[0]
        cur_emoji = cog._currency_emoji(_SlashCtx(interaction))
        color = discord.Color.green() if win_amt > 0 else discord.Color.red()
        result_txt = f"**Résultat : {n} {'🔴' if n in wheel_red else ('⚫' if n != 0 else '🟢')}**"
        if win_amt > 0:
            desc = f"{result_txt}\n\n:tada: __**Vous avez gagné {cog._fmt_amount(win_amt)} {cur_emoji} Fcoins !**__\n\nVotre solde s'estime à : **{cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**"
        else:
            desc = f"{result_txt}\n\n:x: **Vous avez perdu {cog._fmt_amount(abs(win_amt))} {cur_emoji} Fcoins**\n\nVotre solde s'estime à : **{cog._fmt_amount(bal_after)} {cur_emoji} Fcoins**"
        emb = cog._bank_embed(_SlashCtx(interaction), title="Casino • Roulette", description=desc, color=color, txn_id=txid)
        await interaction.response.send_message(embed=emb)
