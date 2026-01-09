import discord
from discord.ext import commands
import asyncio
import random
import math


class Horse:
    def __init__(self, id, name, emoji, base_speed, variance):
        self.id = id
        self.name = name
        self.emoji = emoji
        self.base_speed = base_speed
        self.variance = variance
        self.position = 0.0
        self.odds = 0.0
        self._calculate_odds()

    def _calculate_odds(self):
        # Higher speed = Lower odds
        # Base logic:
        # Speed ~1.0 -> Odds ~5.0
        # Speed ~1.4 -> Odds ~1.5
        # We invert the speed factor logic roughly
        factor = (1.5 / self.base_speed) ** 3
        # Add some randomness to odds to make it realistic (bookmaker margin)
        self.odds = round(max(1.1, min(50.0, factor * 2.0)), 2)

    def move(self):
        # Random movement based on speed and variance
        # Speed is roughly units per step.
        # Target 100 units in ~12 steps => speed needs to be ~8.
        # So we scale base_speed (0.8-1.4) by 7
        step_speed = self.base_speed * 7

        move = step_speed + random.uniform(-self.variance*5, self.variance*5)

        # Events
        event = random.random()
        if event > 0.95:
            move *= 1.5
        elif event < 0.05:
            move *= 0.5

        self.position += max(0, move)
        return self.position

class HorseRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.race_active = False
        self.bets_open = False
        self.horses = []
        self.bets = {} # user_id: (horse_id, amount)
        self.race_message = None
        self.step_delay = 2.5
        self.horse_owner = {}
        self.board_message = None

        self.horse_names = [
            "Tonnerre", "Lasagne", "Petit Poney", "Kebab", "Fazer Express",
            "Tornado", "Spirit", "Usain Bolt", "Twingo", "Ferrari",
            "RSA", "Bitcoin", "La D", "Zidane", "Mbappé",
            "Chicha Pomme", "Tmax", "Kalash", "Jul", "Sarkozy",
            "Banquier", "Huissier", "Fisc", "Pole Emploi"
        ]
        self.emojis = ["🐎", "🦄", "🦓", "🐫", "🐐", "🐂", "🐕", "🐅"]

    def _generate_horses(self):
        self.horses = []
        # 5 to 6 horses
        num_horses = random.randint(5, 6)
        selected_names = random.sample(self.horse_names, num_horses)
        # Reuse emojis if needed
        selected_emojis = [random.choice(self.emojis) for _ in range(num_horses)]

        for i in range(num_horses):
            # Speed 0.8 - 1.4
            speed = random.uniform(0.9, 1.3)
            # Variance
            var = random.uniform(0.1, 0.3)
            h = Horse(i+1, selected_names[i], selected_emojis[i], speed, var)
            self.horses.append(h)

    @commands.group(name="course", aliases=["race"])
    async def course(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "ℹ️ Commandes : `+course start` (Admin), `+bet [cheval] [mise]`, `+course run` (Admin)"
            )

    @course.command(name="start")
    # Check admin or owner
    async def start(self, ctx, duration: int | None = None):
        # Admin check logic duplicated from economy because cleaner than importing
        is_admin = False
        if ctx.author.id == 1443339902623154207:
            is_admin = True
        elif (
            hasattr(ctx.author, "guild_permissions")
            and ctx.author.guild_permissions.administrator
        ):
            is_admin = True

        if not is_admin:
            return await ctx.send("🚫 Seul un admin peut lancer une course.")

        if self.race_active or self.bets_open:
            return await ctx.send("⚠️ Une course est déjà en cours !")

        self._generate_horses()
        self.bets = {}
        self.bets_open = True
        self.race_active = True
        if duration:
            try:
                d = int(duration)
            except Exception:
                d = None
            if d and d >= 10 and d <= 300:
                self.step_delay = max(1.0, d / 10.0)

        # Display Board
        desc = "🏁 **LA COURSE VA BIENTÔT COMMENCER !** 🏁\n\n"
        desc += "Pariez sur votre cheval favori avec `+bet [numéro] [montant]`\n"
        desc += "*Exemple: +bet 2 500*\n\n"
        desc += "📋 **LISTE DES PARTANTS :**\n"

        for h in self.horses:
            owner_note = ""
            if h.id in self.horse_owner:
                owner_note = f" — 👤 Cheval de <@{self.horse_owner[h.id]}>"
            desc += f"**#{h.id} {h.emoji} {h.name}** | Cote: **{h.odds}**{owner_note}\n"

        embed = discord.Embed(
            title="🐎 PMU STREET - Paris Ouverts",
            description=desc,
            color=discord.Color.green(),
        )
        embed.set_thumbnail(
            url="https://media.discordapp.net/attachments/100000000000000000/100000000000000000/horse.png"
        )
        embed.set_footer(text="L'admin lancera la course avec +course run")
        self.board_message = await ctx.send(embed=embed)

    @commands.command(name="bet")
    async def bet(self, ctx, horse_id: int, amount: str):
        if not self.bets_open:
            return await ctx.send("❌ Les paris sont fermés ou pas de course en cours !")

        # Check horse validity
        valid_ids = [h.id for h in self.horses]
        if horse_id not in valid_ids:
            return await ctx.send(
                f"❌ Cheval #{horse_id} invalide. Choisissez entre {min(valid_ids)} et {max(valid_ids)}."
            )

        # Economy check
        cog = self.bot.get_cog("Economy")
        if not cog:
            return await ctx.send("❌ Erreur système (Economy not found).")

        try:
            amt = cog._parse_amount(amount)
        except Exception:
            # Fallback if _parse_amount is instance method or static
            # It seems to be instance method in previous reads
            amt = 0
            try:
                amt = int(amount)
            except Exception:
                pass

        if amt <= 0:
            return await ctx.send("❌ Montant invalide.")

        # DB Check & Deduct
        await cog._connect()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                res = await cur.fetchone()
                if not res or res[0] < amt:
                    return await ctx.send("❌ Pas assez d'argent en poche.")

                # Deduct money
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (amt, ctx.author.id))

        self.bets[ctx.author.id] = (horse_id, amt)
        await ctx.send(f"✅ {ctx.author.mention} a misé **{cog._fmt_amount(amt)}** sur **#{horse_id}** !")

    @course.command(name="run")
    async def run(self, ctx):
        is_admin = False
        if ctx.author.id == 1443339902623154207:
            is_admin = True
        elif (
            hasattr(ctx.author, "guild_permissions")
            and ctx.author.guild_permissions.administrator
        ):
            is_admin = True

        if not is_admin:
            return await ctx.send("🚫 Admin only.")

        if not self.bets_open:
            return await ctx.send("⚠️ Lancez d'abord les paris avec `+course start`.")

        self.bets_open = False
        await ctx.send("🔔 **LES PARIS SONT FERMÉS ! DÉPART IMMÉDIAT !** 🔔")

        # Race Animation
        race_embed = discord.Embed(
            title="🐎 C'EST PARTI !",
            description="Les chevaux s'élancent...",
            color=discord.Color.orange(),
        )
        self.race_message = await ctx.send(embed=race_embed)

        winner = None
        finish_line = 100

        # Simulation loop
        # 25 seconds duration approx.
        # We update every 2.5 seconds -> 10 steps.

        for step in range(15):
            await asyncio.sleep(self.step_delay)

            # Move horses
            for h in self.horses:
                h.move()
                if h.position >= finish_line and not winner:
                    winner = h

            # Sort for leaderboard in description? No, keep track order.

            track_view = ""
            for h in self.horses:
                # Scale position to 20 chars
                progress = min(1.0, max(0.0, h.position / finish_line))
                # Bar: |------🐎       |
                # Total length 25 chars
                track_len = 25
                pos = int(progress * track_len)

                # Dynamic track building
                line = "`|" + "-" * pos + h.emoji + " " * (track_len - pos) + "|`"

                # Check finish
                if h.position >= finish_line:
                    line = f"**{h.emoji} ARRIVÉ !**"

                track_view += f"**#{h.id} {h.name}**: {line}\n"

            # Commentary
            # Get leader
            leading = max(self.horses, key=lambda x: x.position)

            commentary = f"🎙️ **{leading.name}** mène la danse !"
            if leading.position > 80:
                commentary = f"🎙️ **{leading.name}** FONCE VERS LA LIGNE !"
            if winner:
                commentary = f"🏁 **{winner.name}** L'EMPORTE !"

            race_embed.description = track_view + "\n\n" + commentary
            try:
                await self.race_message.edit(embed=race_embed)
            except Exception:
                pass

            if winner:
                break

        # Fallback winner if no one crossed 100 (should not happen with speed logic)
        if not winner:
            winner = max(self.horses, key=lambda x: x.position)

        await asyncio.sleep(1)

        # Result Embed
        res_embed = discord.Embed(
            title=f"🏆 VICTOIRE DE {winner.name.upper()} !",
            description=(
                f"Le cheval **#{winner.id} {winner.name}** remporte la course !\n"
                f"Cote : **{winner.odds}**"
            ),
            color=discord.Color.gold(),
        )
        await ctx.send(embed=res_embed)

        # Payouts
        cog = self.bot.get_cog("Economy")
        winners_names = []
        total_payout = 0

        if cog:
            await cog._connect()
            async with cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    owner_cut = {}
                    for uid, (hid, amt) in self.bets.items():
                        if hid == winner.id:
                            winnings = int(amt * winner.odds)
                            await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (winnings, uid))
                            winners_names.append(f"<@{uid}> (+{cog._fmt_amount(winnings)})")
                            total_payout += winnings
                        if hid in self.horse_owner:
                            owner_id = self.horse_owner[hid]
                            owner_cut[owner_id] = owner_cut.get(owner_id, 0) + int(amt * 0.10)
                    for oid, cut in owner_cut.items():
                        await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (cut, oid))

        if winners_names:
            msg = f"💸 **Félicitations aux gagnants :**\n{', '.join(winners_names)}"
            if len(msg) > 2000:
                msg = msg[:1990] + "..."
            await ctx.send(msg)
        else:
            await ctx.send("💸 **Aucun gagnant... La banque se régale !** 😋")

        self.race_active = False
        self.bets_open = False

    @commands.command(name="horsebuy", aliases=["buyhorse", "cheval", "chevalbuy"])
    async def horsebuy(self, ctx, *, name: str):
        cog = self.bot.get_cog("Economy")
        if not cog:
            return await ctx.send("❌ Erreur système.")
        price = 50_000_000
        await cog._connect()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT balance FROM users WHERE user_id=%s", (ctx.author.id,))
                row = await cur.fetchone()
                if not row or row[0] < price:
                    return await ctx.send("❌ Pas assez en poche pour acheter le cheval (50m).")
                await cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (price, ctx.author.id))
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_horses (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        owner_id BIGINT NOT NULL,
                        name VARCHAR(64) NOT NULL,
                        emoji VARCHAR(8) NOT NULL,
                        base_speed FLOAT NOT NULL,
                        variance FLOAT NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                emoji = random.choice(self.emojis)
                base_speed = random.uniform(0.95, 1.25)
                variance = random.uniform(0.1, 0.25)
                await cur.execute(
                    "INSERT INTO user_horses(owner_id,name,emoji,base_speed,variance) VALUES(%s,%s,%s,%s,%s)",
                    (ctx.author.id, name, emoji, base_speed, variance),
                )
        await ctx.send(f"✅ Cheval **{name}** acheté pour **50m**.")

    @course.command(name="addhorse")
    async def addhorse(self, ctx, *, name: str):
        if not self.bets_open:
            return await ctx.send("❌ Les paris ne sont pas ouverts.")
        cog = self.bot.get_cog("Economy")
        if not cog:
            return await ctx.send("❌ Erreur système.")
        await cog._connect()
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT emoji, base_speed, variance FROM user_horses WHERE owner_id=%s AND name=%s",
                    (ctx.author.id, name),
                )
                row = await cur.fetchone()
                if not row:
                    return await ctx.send("❌ Tu ne possèdes pas ce cheval.")
                emoji, base_speed, variance = row
        new_id = (max([h.id for h in self.horses]) + 1) if self.horses else 1
        h = Horse(new_id, name, emoji, float(base_speed), float(variance))
        self.horses.append(h)
        self.horse_owner[new_id] = ctx.author.id
        await ctx.send(f"✅ Cheval **#{new_id} {name}** ajouté à la course.")
        await self._refresh_board(ctx)

    async def _refresh_board(self, ctx):
        if not self.bets_open or not self.board_message:
            return
        desc = "🏁 **LA COURSE VA BIENTÔT COMMENCER !** 🏁\n\n"
        desc += "Pariez sur votre cheval favori avec `+bet [numéro] [montant]`\n"
        desc += "*Exemple: +bet 2 500*\n\n"
        desc += "📋 **LISTE DES PARTANTS :**\n"
        for h in self.horses:
            owner_note = ""
            if h.id in self.horse_owner:
                owner_note = f" — 👤 Cheval de <@{self.horse_owner[h.id]}>"
            desc += f"**#{h.id} {h.emoji} {h.name}** | Cote: **{h.odds}**{owner_note}\n"
        embed = discord.Embed(
            title="🐎 PMU STREET - Paris Ouverts",
            description=desc,
            color=discord.Color.green(),
        )
        try:
            await self.board_message.edit(embed=embed)
        except Exception:
            pass

    @commands.command(name="horserename", aliases=["renamehorse", "chevalrename"])
    async def horserename(self, ctx, old_name: str, *, new_name: str):
        cog = self.bot.get_cog("Economy")
        if not cog:
            return await ctx.send("❌ Erreur système.")
        if len(new_name) < 2 or len(new_name) > 32:
            return await ctx.send("❌ Nom invalide (2–32 caractères).")
        await cog._connect()
        updated = False
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE user_horses SET name=%s WHERE owner_id=%s AND name=%s",
                    (new_name, ctx.author.id, old_name),
                )
                if cur.rowcount > 0:
                    updated = True
        if not updated:
            return await ctx.send("❌ Aucun cheval trouvé à ton nom avec ce nom.")
        for h in self.horses:
            if h.name == old_name and self.horse_owner.get(h.id) == ctx.author.id:
                h.name = new_name
        await ctx.send(f"✅ Cheval renommé en **{new_name}**.")
        await self._refresh_board(ctx)

    @commands.command(name="horsesell", aliases=["sellhorse"])
    async def horsesell(self, ctx, *, name: str):
        cog = self.bot.get_cog("Economy")
        if not cog:
            return await ctx.send("❌ Erreur système.")
        if self.bets_open:
            for h in self.horses:
                if h.name == name and self.horse_owner.get(h.id) == ctx.author.id:
                    return await ctx.send("❌ Cheval engagé dans une course, vente impossible.")
        price = int(50_000_000 * 0.7)
        await cog._connect()
        sold = False
        async with cog.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM user_horses WHERE owner_id=%s AND name=%s LIMIT 1",
                    (ctx.author.id, name),
                )
                row = await cur.fetchone()
                if not row:
                    return await ctx.send("❌ Tu ne possèdes pas ce cheval.")
                horse_id = row[0]
                await cur.execute("DELETE FROM user_horses WHERE id=%s", (horse_id,))
                await cur.execute(
                    "UPDATE users SET balance=balance+%s WHERE user_id=%s",
                    (price, ctx.author.id),
                )
                sold = True
        if sold:
            rem = []
            for h in self.horses:
                if h.name == name and self.horse_owner.get(h.id) == ctx.author.id:
                    rem.append(h)
            for h in rem:
                self.horses.remove(h)
                self.horse_owner.pop(h.id, None)
            await ctx.send(f"✅ Cheval vendu pour **{cog._fmt_amount(price)}**.")


async def setup(bot):
    await bot.add_cog(HorseRace(bot))
