import os
import random
import difflib
import discord
from discord import app_commands
from dotenv import load_dotenv, dotenv_values
from discord.ext import commands

# ------- CONFIG -------
BOT_NAME = "Bot de Fazer"
PRIMARY_PREFIX = "+"
PREFIXES = ["+", "$"]
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

load_dotenv()
bot = commands.Bot(command_prefix=PREFIXES, intents=INTENTS, help_command=None)

BLOCKED_TARGET_ID = 1429920996080488601
LOVE_ALLOWED_USER_ID = 1443339902623154207
ANNOUNCE_CHANNEL_ID = 1443709677212008561
TWITTER_LOGO_URL = "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"

# Expressions de vaillant
VAILLANT_REPLIES = [
    "t un vaillant",
    "ewe t un monstre frero",
    "t le sang de l’artère fémorale",
    "t le boss du quartier c carré",
    "total indé mon fratelo"
]

MARSEILLE_ADLIBS = [
    "wsh le secteur",
    "ça dit quoi la mif",
    "celui qui est pas content je le monte en l'air",
    "validé par tasty crousty et graya deluxe",
    "le secteur il parle chinois ou quoi aujourd’hui",
    "smr tu parles trop mgl"
]

FAZER_GENERAL_SPAM_LINES = [
    "Fazer ce tdb il a tenté de trouver du taf mais mm Pôle Emploi l’a ghost",
    "Fazer il a pas le permis, il fait du code en trottinette électrique",
    "Fazer il fait des bots qui crashent plus vite que sa batterie",
    "Fazer il a deux passions : rater le code et rater sa vie",
    "Le mec a autant de diplômes qu’un câble HDMI",
    "Fazer il vit dans le cloud, mais c’est des nuages de galère",
    "Il a voulu investir en crypto mais il a fini en crypté mdr",
    "Fazer il fait des bots économiques alors qu’il a -8€ sur son compte",
    "Même ChatGPT veut pas lui parler à Fazer",
    "Fazer il a codé son avenir en Python mais l’interpréteur a crash",
    "Le gars il a pas de permis, pas de love, pas d’argent, mais il a la wifi du voisin",
    "Quand tu dis \"Fazer\" ton PC il cherche directement les erreurs",
    "Fazer il fait semblant de débug mais il supprime le fichier",
    "Un jour Fazer a voulu monter une start-up, bah wallah elle a même pas start",
    "Fazer c’est le genre de blatrou à rager sur un bug qu’il a lui-même écrit à 4h du mat",
    "Le mec dit qu’il a la dalle mais il parle pas de manger, il parle de la vie"
]

# Réponses agressives (utilisées uniquement dans la chaîne de réponses)
AGGRESSIVE_REPLIES = [
    "vasy ferme ta gueule aller la",
    "aller ftg",
    "nachav"
]


# ------- EVENTS -------
@bot.event
async def on_ready():
    print(f"{bot.user} est connecté.")
    await bot.change_presence(
        activity=discord.Game(name="au quartier tu connais frero en bien")
    )
    
    # Force removal of default help just in case
    if bot.help_command:
        bot.help_command = None
    bot.remove_command("help")

    try:
        await bot.load_extension("bot.cogs.economy")
        print("Cog économie chargé.")
    except Exception as e:
        print(f"Échec chargement économie: {e}")

    try:
        await bot.load_extension("bot.cogs.help")
        print("Cog help chargé.")
    except Exception as e:
        print(f"Échec chargement help: {e}")

    try:
        await bot.tree.sync()
        print("Slash commands synchronisées.")
    except Exception as e:
        print(f"Échec sync slash: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Global Error Handler"""
    if hasattr(ctx.command, 'on_error'):
        return

    ignored = (commands.CommandNotFound, )
    error = getattr(error, 'original', error)

    if isinstance(error, ignored):
        return

    if isinstance(error, commands.DisabledCommand):
        await ctx.send(f'{ctx.command} has been disabled.')
    elif isinstance(error, commands.NoPrivateMessage):
        try:
            await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
        except discord.HTTPException:
            pass
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas les permissions nécessaires.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ Je n'ai pas les permissions nécessaires pour faire ça.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Doucement ! Réessaie dans {error.retry_after:.2f}s.")
    else:
        print(f'Ignoring exception in command {ctx.command}: {error}')

    try:
        import asyncio as _asyncio
        from importlib import import_module as _import_module
        async def _autoreload():
            import os as _os, sys as _sys
            base = _os.path.dirname(__file__)
            files = []
            for root, _dirs, names in _os.walk(base):
                for n in names:
                    if n.endswith(".py"):
                        files.append(_os.path.join(root, n))
            mt = {f: _os.stat(f).st_mtime for f in files}
            while True:
                await _asyncio.sleep(2)
                changed = None
                for f in files:
                    try:
                        m = _os.stat(f).st_mtime
                    except Exception:
                        continue
                    if m != mt.get(f):
                        changed = f
                        break
                if changed:
                    try:
                        print(f"[autoreload] modification détectée: {changed} → restart")
                    except Exception:
                        pass
                    _os.execv(_sys.executable, [_sys.executable, "-u", "-m", "bot.bot_de_fazer"])
                    return
        _asyncio.create_task(_autoreload())
    except Exception:
        pass

    try:
        import asyncio as _asyncio
        import random as _random
        # Désactivation du spam général (anti-spam retiré)
        # async def _general_spam():
        #     while True:
        #         await _asyncio.sleep(5 * 60 * 60)
        #         try:
        #             channel = bot.get_channel(ANNOUNCE_CHANNEL_ID) or await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
        #             # Mixte Fazer (moins) et Secteur (plus)
        #             # On multiplie MARSEILLE_ADLIBS pour augmenter la proba de tomber dessus
        #             pool = MARSEILLE_ADLIBS * 5 + FAZER_GENERAL_SPAM_LINES
        #             await channel.send(_random.choice(pool))
        #         except Exception:
        #             pass
        # _asyncio.create_task(_general_spam())
    except Exception:
        pass


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    print(f"[DEBUG] Message: '{message.content}' from {message.author} (len={len(message.content)})")
    
    content_lower = message.content.lower()

    ref = message.reference
    if ref and (getattr(ref, "resolved", None) or getattr(ref, "message_id", None)):
        try:
            replied_msg = getattr(ref, "resolved", None) or await message.channel.fetch_message(ref.message_id)
        except Exception:
            replied_msg = None
        if replied_msg and replied_msg.author == bot.user:
            phrases = VAILLANT_REPLIES + MARSEILLE_ADLIBS + AGGRESSIVE_REPLIES
            if replied_msg.content in phrases:
                try:
                    await message.channel.send(random.choice(phrases))
                except Exception:
                    pass
                await bot.process_commands(message)
                return

    # Si quelqu’un dit merci → réponse custom
    if "merci" in content_lower or "mrc" in content_lower or "thanks" in content_lower:
        reply = random.choice(VAILLANT_REPLIES)
        adlib = random.choice(MARSEILLE_ADLIBS)
        chosen = random.choice([reply, adlib])
        await message.channel.send(chosen)

    try:
        print(f"[DEBUG] Processing commands for message: {message.content}")
        await bot.process_commands(message)
    except Exception as e:
        print(f"[ERROR] process_commands failed: {e}")


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        raw = ctx.message.content
        pref = next((p for p in PREFIXES if raw.startswith(p)), "")
        tried = raw[len(pref):].split()[0] if pref else raw.split()[0]
        names = [c.name for c in bot.commands]
        suggestion = difflib.get_close_matches(tried, names, n=1, cutoff=0.6)
        msg = f"Wsh {ctx.author.mention}, la commande `{tried}` n’existe pas."
        if suggestion:
            msg += f" Tu voulais dire `{PRIMARY_PREFIX}{suggestion[0]}` ?"
        else:
            msg += " Tu crois t un dev t un tasty crousty."
        await ctx.send(msg)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"T’as oublié des paramètres, {ctx.author.mention}. Remets propre : `{PRIMARY_PREFIX}{ctx.command.name}`.")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("Argu chelou détecté. Mets des valeurs carrées tu me deuh.")
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("T’as pas les perms pour ça mon fils. Appelle le staff.")
        return
    if isinstance(error, commands.CommandOnCooldown):
        try:
            # Désactivation de l'anti-spam (cooldown bypass pour tout le monde pour l'instant)
            # if ctx.author.guild_permissions.administrator:
            #     pass
            await ctx.reinvoke() # Tente de relancer la commande sans cooldown
            return
        except Exception:
            pass
        # Si le reinvoke échoue ou si on veut quand même afficher le message (commenté pour "retirer l'anti-spam")
        # cd = int(error.retry_after)
        # m = cd // 60
        # s = cd % 60
        # if m > 0:
        #     msg = f"Doucement le spam respire un peu fils. Reviens dans {m}m {s}s."
        # else:
        #     msg = f"Doucement le spam respire un peu fils. Reviens dans {s}s."
        # await ctx.send(msg)
        return
    await ctx.send("Y’a eu un bug. Pas toi (j’espère). Réessaye.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    if isinstance(error, app_commands.CommandOnCooldown):
        try:
            # Même logique : bypass cooldown
            # cd = int(error.retry_after)
            # m = cd // 60
            # s = cd % 60
            # if m > 0:
            #     msg = f"Doucement le spam respire un peu fils. Reviens dans {m}m {s}s."
            # else:
            #     msg = f"Doucement le spam respire un peu fils. Reviens dans {s}s."
            
            # if interaction.response.is_done():
            #     await interaction.followup.send(msg, ephemeral=True)
            # else:
            #     await interaction.response.send_message(msg, ephemeral=True)
            pass # On ignore l'erreur silencieusement ou on pourrait tenter de relancer la commande slash mais c'est plus complexe
        except Exception:
            pass
        return
    try:
        if interaction.response.is_done():
            await interaction.followup.send("Y’a eu un bug. Réessaye.", ephemeral=True)
        else:
            await interaction.response.send_message("Y’a eu un bug. Réessaye.", ephemeral=True)
    except Exception:
        pass


# ------- COMMANDES DE BASE -------

@bot.command(name="ping")
async def ping(ctx: commands.Context):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(
        f"Pong {ctx.author.mention} ! T’es vif à {latency_ms} ms, "
        f"t’es une fibre optique mon frero bsaha 💥"
    )

@bot.tree.command(name="ping", description="Tester la latence du bot")
async def ping_slash(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong ! {latency_ms} ms")


@bot.command(name="avatar")
async def avatar(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(
        f"We kho {member.display_name}, voici ta tête de vaillant : {member.avatar.url}"
    )


@bot.command(name="userinfo")
async def userinfo(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(
        title=f"Fiche Interpol de {member.display_name}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Pseudo", value=member.name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Rejoint le serveur", value=member.joined_at.strftime("%d/%m/%Y"), inline=False)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
async def serverinfo(ctx: commands.Context):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"Infos de {guild.name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Membres", value=guild.member_count, inline=True)
    embed.add_field(name="Proprio", value=guild.owner, inline=True)
    embed.add_field(name="Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=False)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.page = 1

    def _page1(self):
        emb = discord.Embed(title="Aide (1/2)", color=discord.Color.blurple(), description="Commandes principales")
        emb.add_field(name="+balance / /balance", value="Afficher poche et banque", inline=False)
        emb.add_field(name="+market / +shop", value="🏪 Marché unifié (Immo, Luxe, Objets)", inline=False)
        emb.add_field(name="+deposit / +withdraw", value="Gestion Banque", inline=False)
        emb.add_field(name="+buy / +sell", value="Achat/Vente rapide", inline=False)
        emb.add_field(name="+inventory", value="Inventaire", inline=False)
        emb.add_field(name="+send", value="Virements", inline=False)
        emb.add_field(name="+khedma", value="Travail (+100)", inline=False)
        emb.add_field(name="+gofast", value="Go-Fast (Risqué)", inline=False)
        emb.add_field(name="+braquage", value="Braquer un joueur", inline=False)
        emb.add_field(name="Jeux d'argent", value="coin_flip, slots, dice, ladder, scoot, risk", inline=False)
        emb.add_field(name="Revenus", value="daily, weekly, monthly", inline=False)
        return emb

    def _page2(self):
        emb = discord.Embed(title="Aide (2/2)", color=discord.Color.teal(), description="Avancé & Admin")
        emb.add_field(name="+immo", value="🏠 Immobilier (Achat, Vente, Collecte)", inline=False)
        emb.add_field(name="+luxury", value="💎 Luxe (Achat, Transfert)", inline=False)
        emb.add_field(name="+assets", value="🏰 Voir son patrimoine", inline=False)
        emb.add_field(name="+add_money / +remove_money", value="Gestion Admin", inline=False)
        emb.add_field(name="+reset_user", value="Reset joueur (Admin)", inline=False)
        emb.add_field(name="+tax", value="Taxer (Owner)", inline=False)
        return emb

    @discord.ui.button(label="Page 1", style=discord.ButtonStyle.primary)
    async def page1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self._page1())

    @discord.ui.button(label="Page 2", style=discord.ButtonStyle.secondary)
    async def page2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self._page2())


@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    view = HelpView()
    await ctx.send(embed=view._page1(), view=view)

@bot.tree.command(name="help", description="Aide en deux pages")
async def help_slash(interaction: discord.Interaction):
    view = HelpView()
    await interaction.response.send_message(embed=view._page1(), view=view)


@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx: commands.Context, *, message: str):
    await ctx.message.delete()
    await ctx.send(f"{message}\n\n— signé un vaillant du quartier")


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx: commands.Context, amount: int = 5):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(
        f"J’ai effacé {len(deleted) - 1} messages, bien soignééé",
        delete_after=5
    )

@bot.command(name="invite")
@commands.has_permissions(create_instant_invite=True)
async def invite(ctx: commands.Context, max_age: int = 86400):
    invite = await ctx.channel.create_invite(max_age=max_age, max_uses=100)
    await ctx.send(f"🔗 **OEE LA TÉLÉ** : {invite.url}\nValable {max_age//3600}h, 100 uses max.")


# ------- ADMIN UTILS -------

@bot.command(name="reload")
@commands.is_owner()
async def reload_cmd(ctx: commands.Context):
    try:
        await bot.reload_extension("bot.cogs.economy")
        await bot.tree.sync()
        await ctx.send("Cog économie rechargé et slash synchronisés.")
    except Exception as e:
        await ctx.send(f"Échec reload: {e}")



# ------- COMMANDES FUN TYPE KOYA -------

@bot.command(name="scoot")
async def scoot(ctx: commands.Context, member1: discord.Member, member2: discord.Member = None):
    member2 = member2 or ctx.author if member1 != ctx.author else None
    if not member2:
        await ctx.send("Faut 2 reufs pour la course fréro t con ou quoi ??")
        return
    
    vitesse1 = random.randint(40, 120)
    vitesse2 = random.randint(40, 120)
    
    embed = discord.Embed(title="🏍️ **SCOOT RACE QUARTIER**", color=discord.Color.red())
    embed.add_field(name=member1.display_name, value=f"{vitesse1} km/h 🏍️", inline=True)
    embed.add_field(name=member2.display_name, value=f"{vitesse2} km/h 🏍️", inline=True)
    
    if vitesse1 > vitesse2:
        embed.description = f"**{member1.display_name}** arrive premier ! 🥇 {random.choice(VAILLANT_REPLIES)}"
    elif vitesse2 > vitesse1:
        embed.description = f"**{member2.display_name}** arrive premier ! 🥇 {random.choice(VAILLANT_REPLIES)}"
    else:
        embed.description = "Égalité ! Deux grosses merdes 😭"
    
    await ctx.send(embed=embed)

@bot.command(name="8ball")
async def eight_ball(ctx: commands.Context, *, question: str):
    réponses = [
        "Tu me fais la commande 8ball alors que ta mm pas 8 balles sur ton compte trou dbal",
        "Jconnais pas l'invisible nachav",
        "Singe",
        "Nachav",
        "Nn ça pue la douille."
    ]
    await ctx.send(
        f"🎱 Question de {ctx.author.mention} : {question}\n"
        f"Réponse : {random.choice(réponses)}"
    )


@bot.command(name="choose")
async def choose(ctx: commands.Context, *choices: str):
    if len(choices) < 2:
        await ctx.send("Donne au moins deux options frero deuh pas. Exemple : `!choose pizza tacos burger`")
        return
    choice = random.choice(choices)
    await ctx.send(f"Entre tout ça, le quartier a voté pour : **{choice}** ✅")


@bot.command(name="love")
async def love(ctx: commands.Context, member1: discord.Member, member2: discord.Member = None):
    member2 = member2 or ctx.author
    if ((member1.id == BLOCKED_TARGET_ID) or (member2 and member2.id == BLOCKED_TARGET_ID)) and ctx.author.id != LOVE_ALLOWED_USER_ID:
        await ctx.send("🚫 Action impossible.")
        return
    pourcentage = random.randint(0, 100)
    await ctx.send(
        f"💗 Love entre **{member1.display_name}** et **{member2.display_name}** : **{pourcentage}%**.\n"
        f"C’est validé par le ghetto." if pourcentage > 60 else
        f"Les sangs… {pourcentage}% c’est harrr."
    )


@bot.command(name="rps")
async def rps(ctx: commands.Context, choix: str):
    options = ["pierre", "feuille", "ciseaux"]
    bot_choice = random.choice(options)

    choix = choix.lower()
    if choix not in options:
        await ctx.send("Choisis entre `pierre`, `feuille` ou `ciseaux`, on n’est pas au loto là.")
        return

    result = ""
    if choix == bot_choice:
        result = "Égalité, t’es aussi con que moi."
    elif (choix == "pierre" and bot_choice == "ciseaux") or \
         (choix == "feuille" and bot_choice == "pierre") or \
         (choix == "ciseaux" and bot_choice == "feuille"):
        result = "T’as gagné t’es un monstre mon frangin."
    else:
        result = "J’ai gagné, normal chui le boss du quartier mon frero"

    await ctx.send(f"Tu as joué **{choix}**, j’ai joué **{bot_choice}**.\n{result}")


@bot.command(name="roll")
async def roll(ctx: commands.Context, minimum: int = 1, maximum: int = 100):
    if minimum >= maximum:
        await ctx.send("Minimum doit être plus petit que maximum, t’essaies de douiller le système ou quoi ?")
        return
    number = random.randint(minimum, maximum)
    await ctx.send(f"🎲 Tu as tiré **{number}** entre {minimum} et {maximum}. T bon fils.")


@bot.command(name="gift")
async def gift(ctx: commands.Context):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    try:
        user = await bot.fetch_user(BLOCKED_TARGET_ID)
        await user.send("💐")
    except Exception:
        pass


@bot.command(name="testvaillant")
async def testvaillant(ctx: commands.Context, member: discord.Member):
    pourcentage = random.randint(0, 100)
    if pourcentage < 30:
        commentaire = "T’es un vaillant en stage d’observation seulement."
    elif pourcentage < 70:
        commentaire = "Validé par le quartier, mais pas encore par la daronne."
    else:
        commentaire = "On grave ton blaze sur le mur du hall."
    await ctx.send(
        f"💪 Vaillance de **{member.display_name}** : **{pourcentage}%**.\n{commentaire}"
    )


@bot.command(name="tweet")
async def tweet(ctx: commands.Context, *, texte: str):
    handle = f"@{ctx.author.name.lower()}"
    embed = discord.Embed(description=texte, color=discord.Color(0x1DA1F2))
    embed.title = "Tweet"
    avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
    embed.set_author(name=f"{ctx.author.display_name} • {handle}", icon_url=avatar_url)
    embed.set_footer(text="Twitter", icon_url=TWITTER_LOGO_URL)
    try:
        await ctx.message.delete()
    except Exception:
        pass
    message = await ctx.send(embed=embed)
    for emoji in ["💬", "🔁", "❤️"]:
        try:
            await message.add_reaction(emoji)
        except Exception:
            pass


@bot.command(name="on")
async def on_cmd(ctx: commands.Context):
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID) or await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
    await channel.send("Le bot est ON")


@bot.command(name="vaillant")
async def vaillant(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    phrase = random.choice(VAILLANT_REPLIES)
    adlib = random.choice(MARSEILLE_ADLIBS)
    await ctx.send(f"{member.mention}, {phrase} — {adlib}.")

import aiohttp
import asyncio

async def test_discord():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://discord.com/api/v10/gateway') as resp:
                print(f"✅ Discord OK: {resp.status}")
    except Exception as e:
        print(f"❌ Erreur: {e}")

asyncio.run(test_discord())



# ------- LANCEMENT DU BOT -------

def main():
    env_path = os.getenv("DOTENV_PATH", "/home/app/bot-discord/.env")
    try:
        env_vals = dotenv_values(env_path)
    except Exception:
        env_vals = dotenv_values()
    # Priorité au .env explicite
    token = env_vals.get("DISCORD_TOKEN") or env_vals.get("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
    if token:
        token = token.strip()
    if not token:
        raise RuntimeError("Variable d’environnement DISCORD_BOT_TOKEN/DISCORD_TOKEN manquante.")
    bot.run(token)


if __name__ == "__main__":
    main()
