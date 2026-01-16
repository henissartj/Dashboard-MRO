import os
import sys
import fcntl
import random
import difflib
import discord
from discord import app_commands
from dotenv import load_dotenv, dotenv_values
from discord.ext import commands
import time
import datetime as dt

# ------- SINGLE INSTANCE LOCK -------
def single_instance_check():
    """Ensure only one instance of the bot is running."""
    lock_file_path = '/tmp/bot_fazer.lock'
    try:
        # Open the file in write mode (creates it if it doesn't exist)
        # We keep the file object open to maintain the lock
        fp = open(lock_file_path, 'w')
        # Try to acquire an exclusive lock without blocking
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID for info
        fp.write(str(os.getpid()))
        fp.flush()
        return fp
    except IOError:
        print("⚠️  ERREUR CRITIQUE: Une autre instance du bot est déjà en cours d'exécution.")
        print("    Veuillez arrêter l'ancienne instance avant d'en lancer une nouvelle.")
        sys.exit(1)

# Hold the lock reference globally so it isn't garbage collected
_INSTANCE_LOCK = single_instance_check()

# ------- CONFIG -------
BOT_NAME = "Bot de Fazer"
PRIMARY_PREFIX = "+"
PREFIXES = ["+", "$"]
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True

load_dotenv()
bot = commands.Bot(command_prefix=PREFIXES, intents=INTENTS, help_command=None)
bot.global_cooldown_until = 0.0
bot.repeat_cooldown_seconds = 0
bot._last_command_use = {}

BLOCKED_TARGET_ID = 1429920996080488601
LOVE_ALLOWED_USER_ID = 1443339902623154207
IGNORED_USER_ID = None
ANNOUNCE_CHANNEL_ID = 1443709677212008561
WARNINGS: dict[tuple[int, int], list[dict[str, object]]] = {}
BLACKLISTED_USERS: set[int] = set()
LOCKED_CHANNELS: set[int] = set()
TWITTER_LOGO_URL = "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
try:
    _env_path = os.getenv("DOTENV_PATH", "/home/app/bot-discord/.env")
    _vals = dotenv_values(_env_path)
except Exception:
    _vals = {}
DN_IMAGE_URL = (
    os.getenv("DN_IMAGE_URL")
    or _vals.get("DN_IMAGE_URL")
    or "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
)

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
        await bot.load_extension("bot.cogs.interest")
        print("Cog interest chargé.")
    except Exception as e:
        print(f"Échec chargement interest: {e}")

    try:
        await bot.load_extension("bot.cogs.horserace")
        print("Cog horserace chargé.")
    except Exception as e:
        print(f"Échec chargement horserace: {e}")

    try:
        await bot.load_extension("bot.cogs.fun")
        print("Cog fun chargé.")
    except Exception as e:
        print(f"Échec chargement fun: {e}")

    try:
        await bot.load_extension("bot.cogs.community")
        print("Cog community chargé.")
    except Exception as e:
        print(f"Échec chargement community: {e}")
    
    try:
        names = [c.name for c in bot.commands]
        print(f"Commands chargées: {len(names)}")
        if "work" in names:
            print("Commande 'work' présente.")
        else:
            print("Commande 'work' absente.")
    except Exception as e:
        print(f"Échec check commandes: {e}")

    try:
        await bot.tree.sync()
        print("Slash commands synchronisées.")
    except Exception as e:
        print(f"Échec sync slash: {e}")

@bot.check
async def _global_cooldown(ctx: commands.Context):
    until = getattr(bot, "global_cooldown_until", 0.0)
    now = time.time()
    if until and now < until:
        remaining = int(until - now)
        await ctx.send(f"⛔ Commandes verrouillées encore {remaining}s.")
        return False
    return True

@bot.command(name="cooldown_global", aliases=["cooldown"])
async def cooldown_global(ctx: commands.Context, seconds: int):
    """
    Active/Désactive un cooldown global pour tout le bot.
    Usage: +cooldown <secondes> (0 pour désactiver)
    Admin only.
    """
    is_admin = False
    if ctx.author.id == 1443339902623154207:
        is_admin = True
    elif hasattr(ctx.author, "guild_permissions") and ctx.author.guild_permissions.administrator:
        is_admin = True
    if not is_admin:
        await ctx.send("🚫 Admin only.")
        return
    if seconds < 0:
        await ctx.send("❌ Temps invalide.")
        return
    bot.global_cooldown_until = time.time() + seconds
    if seconds == 0:
        await ctx.send("✅ Cooldown global désactivé.")
    else:
        await ctx.send(f"✅ Cooldown global activé pour {seconds}s.")

@bot.check
async def _repeat_cooldown(ctx: commands.Context):
    secs = getattr(bot, "repeat_cooldown_seconds", 0)
    if not secs or secs <= 0:
        return True
    key = (ctx.author.id, ctx.command.qualified_name if ctx.command else "")
    now = time.time()
    last = bot._last_command_use.get(key, 0.0)
    if last and (now - last) < secs:
        remain = int(secs - (now - last))
        await ctx.send(f"⏳ Répète pas: réessaie {ctx.command.qualified_name} dans {remain}s.")
        return False
    bot._last_command_use[key] = now
    return True

@bot.command(name="cooldown_repeat")
async def cooldown_repeat(ctx: commands.Context, seconds: int):
    """
    Empêche le spam de la même commande.
    Usage: +cooldown_repeat <secondes>
    Admin only.
    """
    is_admin = False
    if ctx.author.id == 1443339902623154207:
        is_admin = True
    elif hasattr(ctx.author, "guild_permissions") and ctx.author.guild_permissions.administrator:
        is_admin = True
    if not is_admin:
        await ctx.send("🚫 Admin only.")
        return
    if seconds < 0:
        await ctx.send("❌ Temps invalide.")
        return
    bot.repeat_cooldown_seconds = seconds
    if seconds == 0:
        await ctx.send("✅ Cooldown de répétition désactivé.")
    else:
        await ctx.send(f"✅ Cooldown de répétition par commande fixé à {seconds}s.")
@bot.command(name="restart")
async def restart_bot(ctx: commands.Context):
    if ctx.author.id != LOVE_ALLOWED_USER_ID:
        await ctx.send("🚫 Seul le propriétaire peut redémarrer le bot.")
        return
    await ctx.send("♻️ Redémarrage du bot en cours...")
    os._exit(0)
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

    if message.author.id == IGNORED_USER_ID:
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
async def on_member_join(member: discord.Member):
    if member.id in BLACKLISTED_USERS:
        try:
            await member.guild.ban(member, reason="Blacklist")
        except Exception:
            return


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
        cd = int(error.retry_after)
        m = cd // 60
        s = cd % 60
        if m > 0:
            msg = f"⏳ Doucement le spam ! Reviens dans {m}m {s}s."
        else:
            msg = f"⏳ Doucement le spam ! Reviens dans {s}s."
        await ctx.send(msg)
        return
    print(f"[ERROR] Unhandled exception: {error}")
    import traceback
    traceback.print_exc()
    await ctx.send("Y’a eu un bug. Pas toi (j’espère). Réessaye.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    if isinstance(error, app_commands.CommandOnCooldown):
        cd = int(error.retry_after)
        msg = f"⏳ Doucement ! Reviens dans {cd}s."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return
    try:
        if interaction.response.is_done():
            await interaction.followup.send("Y’a eu un bug. Réessaye.", ephemeral=True)
        else:
            await interaction.response.send_message("Y’a eu un bug. Réessaye.", ephemeral=True)
    except Exception:
        pass


# ------- COMMANDES DE BASE -------

class BotInfoView(discord.ui.View):
    def __init__(self, invite_url):
        super().__init__()
        self.add_item(discord.ui.Button(label="Site Web", url="http://www.fazer.city/", emoji="🌐"))
        self.add_item(discord.ui.Button(label="Ajouter au serveur", url=invite_url, emoji="➕"))

@bot.command(name="botinfo", aliases=["bi", "bot"])
async def botinfo(ctx: commands.Context):
    """Affiche les infos du bot et les liens utiles."""
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(administrator=True))
    view = BotInfoView(invite_url)
    
    embed = discord.Embed(title="🤖 Bot de Fazer", description="Le bot du quartier. Validé par le secteur.", color=0xFFD700)
    embed.add_field(name="Développeur", value="Fazer", inline=True)
    embed.add_field(name="Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Serveurs", value=str(len(bot.guilds)), inline=True)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_image(url="http://www.fazer.city/images/video.gif?v=3")
    embed.set_footer(text="Ambiance, Casino, Économie & Quartier")
    
    await ctx.send(embed=embed, view=view)

@bot.tree.command(name="ping", description="Tester la latence du bot")
async def ping_slash(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong ! {latency_ms} ms")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_member(ctx: commands.Context, member: discord.Member, *, reason: str | None = None):
    if not ctx.guild:
        return
    if member == ctx.author or member == bot.user:
        await ctx.send("Action impossible sur ce membre.")
        return
    try:
        await member.kick(reason=reason or f"Kick par {ctx.author}")
        await ctx.send(f"{member.mention} a été expulsé du serveur.")
    except discord.Forbidden:
        await ctx.send("Je ne peux pas expulser ce membre.")
    except Exception as e:
        await ctx.send(f"Erreur kick: {e}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_member(ctx: commands.Context, member: discord.Member, *, reason: str | None = None):
    if not ctx.guild:
        return
    if member == ctx.author or member == bot.user:
        await ctx.send("Action impossible sur ce membre.")
        return
    try:
        await ctx.guild.ban(member, reason=reason or f"Ban par {ctx.author}", delete_message_days=0)
        await ctx.send(f"{member.mention} a été banni du serveur.")
    except discord.Forbidden:
        await ctx.send("Je ne peux pas bannir ce membre.")
    except Exception as e:
        await ctx.send(f"Erreur ban: {e}")


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban_member(ctx: commands.Context, *, target: str):
    if not ctx.guild:
        return
    try:
        bans = await ctx.guild.fetch_bans()
    except Exception as e:
        await ctx.send(f"Impossible de récupérer la liste des bans: {e}")
        return
    target_lower = target.lower().strip()
    user_obj: discord.User | None = None
    if target.isdigit():
        uid = int(target)
        for entry in bans:
            if entry.user.id == uid:
                user_obj = entry.user
                break
    if not user_obj:
        for entry in bans:
            name = f"{entry.user.name}#{entry.user.discriminator}"
            if name.lower() == target_lower or entry.user.name.lower() == target_lower:
                user_obj = entry.user
                break
    if not user_obj:
        await ctx.send("Utilisateur non trouvé dans la liste des bannis.")
        return
    try:
        await ctx.guild.unban(user_obj, reason=f"Unban par {ctx.author}")
        await ctx.send(f"{user_obj.mention} a été débanni.")
    except Exception as e:
        await ctx.send(f"Erreur unban: {e}")


@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn_member(ctx: commands.Context, member: discord.Member, *, reason: str):
    if not ctx.guild:
        return
    if member == ctx.author or member == bot.user:
        embed = discord.Embed(
            title="Avertissement impossible",
            description="Action impossible sur ce membre.",
            color=0xE74C3C,
        )
        await ctx.send(embed=embed)
        return
    key = (ctx.guild.id, member.id)
    if key not in WARNINGS:
        WARNINGS[key] = []
    entry = {
        "moderator_id": ctx.author.id,
        "reason": reason,
        "ts": int(time.time()),
    }
    WARNINGS[key].append(entry)
    ts = dt.datetime.fromtimestamp(entry["ts"])
    embed = discord.Embed(
        title="Nouvel avertissement",
        description=f"{member.mention} a reçu un avertissement.",
        color=0xE67E22,
        timestamp=ts,
    )
    embed.add_field(name="Membre", value=member.mention, inline=True)
    embed.add_field(name="Modérateur", value=ctx.author.mention, inline=True)
    embed.add_field(name="Raison", value=reason[:1024], inline=False)
    await ctx.send(embed=embed)


@bot.command(name="unwarn")
@commands.has_permissions(manage_messages=True)
async def unwarn_member(ctx: commands.Context, member: discord.Member, index: int | None = None):
    if not ctx.guild:
        return
    key = (ctx.guild.id, member.id)
    warns = WARNINGS.get(key, [])
    if not warns:
        embed = discord.Embed(
            title="Avertissements",
            description="Aucun avertissement pour ce membre.",
            color=0x2ECC71,
        )
        await ctx.send(embed=embed)
        return
    if index is None:
        warns.pop()
        if not warns:
            WARNINGS.pop(key, None)
        embed = discord.Embed(
            title="Avertissement retiré",
            description=f"Dernier avertissement retiré pour {member.mention}.",
            color=0x2ECC71,
        )
        await ctx.send(embed=embed)
        return
    idx = index - 1
    if idx < 0 or idx >= len(warns):
        embed = discord.Embed(
            title="Index invalide",
            description="L'index fourni ne correspond à aucun avertissement.",
            color=0xE74C3C,
        )
        await ctx.send(embed=embed)
        return
    warns.pop(idx)
    if not warns:
        WARNINGS.pop(key, None)
    embed = discord.Embed(
        title="Avertissement retiré",
        description=f"Avertissement #{index} retiré pour {member.mention}.",
        color=0x2ECC71,
    )
    await ctx.send(embed=embed)


@bot.command(name="warns", aliases=["voirwarn", "warnings", "wv", "vn"])
@commands.has_permissions(manage_messages=True)
async def list_warns(ctx: commands.Context, member: discord.Member):
    if not ctx.guild:
        return
    key = (ctx.guild.id, member.id)
    warns = WARNINGS.get(key, [])
    if not warns:
        embed = discord.Embed(
            title="Avertissements",
            description=f"Aucun avertissement pour {member.mention}.",
            color=0x2ECC71,
        )
        await ctx.send(embed=embed)
        return
    embed = discord.Embed(
        title=f"Avertissements pour {member.display_name}",
        color=0xE67E22,
    )
    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
    lines = []
    for i, w in enumerate(warns, start=1):
        mod_id = w.get("moderator_id")
        mod = ctx.guild.get_member(mod_id) if mod_id else None
        mod_name = mod.mention if mod else f"ID {mod_id}"
        reason = w.get("reason") or "Aucune raison"
        ts = w.get("ts")
        if isinstance(ts, (int, float)):
            dt_obj = dt.datetime.fromtimestamp(ts)
            ts_str = dt_obj.strftime("%d/%m/%Y %H:%M")
        else:
            ts_str = "date inconnue"
        lines.append(f"{i}. {reason} • par {mod_name} • le {ts_str}")
    text = "\n".join(lines)
    embed.description = text[:4096]
    await ctx.send(embed=embed)


@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge_user(ctx: commands.Context, member: discord.Member, limit: int | None = 100):
    if not ctx.guild:
        return
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("Cette commande doit être utilisée dans un salon texte.")
        return
    amount = limit or 100
    if amount <= 0:
        await ctx.send("Nombre de messages invalide.")
        return
    def check(m: discord.Message) -> bool:
        return m.author.id == member.id
    try:
        deleted = await ctx.channel.purge(limit=amount, check=check)
        await ctx.send(f"{len(deleted)} messages de {member.mention} supprimés.", delete_after=5)
    except Exception as e:
        await ctx.send(f"Erreur purge: {e}")


@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock_channel(ctx: commands.Context, channel: discord.TextChannel | None = None):
    if not ctx.guild:
        return
    target = channel or ctx.channel
    if not isinstance(target, discord.TextChannel):
        await ctx.send("Salon invalide.")
        return
    overwrite = target.overwrites_for(ctx.guild.default_role)
    if overwrite.send_messages is False:
        await ctx.send("Ce salon est déjà verrouillé.")
        return
    overwrite.send_messages = False
    try:
        await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        LOCKED_CHANNELS.add(target.id)
        await ctx.send(f"{target.mention} est maintenant verrouillé.")
    except Exception as e:
        await ctx.send(f"Erreur lock: {e}")


@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock_channel(ctx: commands.Context, channel: discord.TextChannel | None = None):
    if not ctx.guild:
        return
    target = channel or ctx.channel
    if not isinstance(target, discord.TextChannel):
        await ctx.send("Salon invalide.")
        return
    overwrite = target.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None
    try:
        await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        LOCKED_CHANNELS.discard(target.id)
        await ctx.send(f"{target.mention} est maintenant déverrouillé.")
    except Exception as e:
        await ctx.send(f"Erreur unlock: {e}")


@bot.command(name="blacklist", aliases=["bl"])
@commands.has_permissions(ban_members=True)
async def blacklist_member(ctx: commands.Context, member: discord.Member, *, reason: str | None = None):
    if not ctx.guild:
        return
    if member == ctx.author or member == bot.user:
        await ctx.send("Action impossible sur ce membre.")
        return
    BLACKLISTED_USERS.add(member.id)
    try:
        await ctx.guild.ban(member, reason=reason or f"Blacklist par {ctx.author}", delete_message_days=0)
        await ctx.send(f"{member.mention} a été blacklist et banni.")
    except discord.Forbidden:
        await ctx.send("Je ne peux pas bannir ce membre.")
    except Exception as e:
        await ctx.send(f"Erreur blacklist: {e}")



    if not guild or not name:
        return None
    name_lower = name.lower().strip()
    # Exact by display_name or username
    for m in guild.members:
        if m.display_name.lower() == name_lower or m.name.lower() == name_lower:
            return m
    # Startswith
    candidates = [m for m in guild.members if m.display_name.lower().startswith(name_lower) or m.name.lower().startswith(name_lower)]
    if candidates:
        return candidates[0]
    # Fuzzy
    base = {m: m.display_name.lower() for m in guild.members}
    names = list(base.values()) + [m.name.lower() for m in guild.members]
    try:
        import difflib as _difflib
        best = _difflib.get_close_matches(name_lower, names, n=1, cutoff=0.6)
        if best:
            target = best[0]
            for m in guild.members:
                if m.display_name.lower() == target or m.name.lower() == target:
                    return m
    except Exception:
        pass
    return None

@bot.command(name="dn", help="Ban par nom: +dn <nom>")
@commands.has_permissions(ban_members=True)
async def dn(ctx: commands.Context, *, nom: str):
    if not ctx.guild:
        return await ctx.send("Cette commande doit être utilisée dans un serveur.")
    target = _find_member_by_name(ctx.guild, nom)
    if not target:
        return await ctx.send(f"Introuvable: {nom}. Donne le pseudo exact.")
    if target.id == ctx.author.id:
        return await ctx.send("Tu peux pas te ban toi-même frero.")
    if target == bot.user:
        return await ctx.send("Tu veux bannir le bot ? Vaillant mais non.")
    try:
        import aiohttp, io, os
        dm = await target.create_dm()
        sent = False
        src = DN_IMAGE_URL or ""
        if src.startswith("http"):
            try:
                async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
                    async with session.get(src) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            f = discord.File(io.BytesIO(data), filename="botban.png")
                            await dm.send(file=f)
                            sent = True
            except Exception:
                pass
        if not sent:
            path = "/opt/mro_dash/images/botban.png"
            if os.path.exists(path):
                f = discord.File(path, filename="botban.png")
                await dm.send(file=f)
                sent = True
        if not sent:
            embed = discord.Embed(title="Tu dégages", description="Décision: ban.", color=discord.Color.red())
            await dm.send(embed=embed)
    except Exception:
        pass
    try:
        await ctx.guild.ban(target, reason=f"DN par {ctx.author} ({nom})", delete_message_days=0)
        await ctx.send(f"{target.mention} banni. C’est carré.")
    except discord.Forbidden:
        await ctx.send("J’ai pas les perms pour ban ce membre.")
    except Exception as e:
        await ctx.send(f"Échec ban: {e}")



@bot.command(name="interpol")
@commands.cooldown(1, 10, commands.BucketType.user)
async def interpol(ctx: commands.Context, member: discord.Member = None):
    member = member or ctx.author
    
    # Création de l'image
    import io
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import aiohttp

    # --- CONFIGURATION & ASSETS ---
    width, height = 850, 500
    background = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(background)
    
    # Get organization info for the user
    org_name = "Aucune"
    org_role = ""
    org_badge = ""
    try:
        economy_cog = bot.get_cog('Economy')
        if economy_cog:
            await economy_cog._connect()
            async with economy_cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT c.name, m.role, c.badge 
                        FROM clans c 
                        JOIN clan_members m ON c.id = m.clan_id 
                        WHERE m.user_id=%s
                    """, (member.id,))
                    c_row = await cur.fetchone()
                    if c_row:
                        org_name = c_row[0]
                        org_role = f"({c_row[1]})"
                        org_badge = c_row[2] if c_row[2] else ""
    except:
        pass  # Organization info not critical

    # Couleurs (Interpol Style)
    COLOR_NAVY = (24, 46, 88)      # Dark Navy (Left gradient)
    COLOR_BLUE = (0, 75, 141)      # Medium Blue (Right gradient)
    COLOR_RED = (196, 18, 48)      # Interpol Red
    COLOR_TEXT_DARK = (30, 30, 30) # Dark Gray
    COLOR_TEXT_GREY = (80, 80, 80) # Lighter Gray
    COLOR_WHITE = (255, 255, 255)

    # --- HEADER GRADIENT ---
    # Création du dégradé horizontal
    for x in range(width):
        ratio = x / width
        r = int(COLOR_NAVY[0] * (1 - ratio) + COLOR_BLUE[0] * ratio)
        g = int(COLOR_NAVY[1] * (1 - ratio) + COLOR_BLUE[1] * ratio)
        b = int(COLOR_NAVY[2] * (1 - ratio) + COLOR_BLUE[2] * ratio)
        draw.line([(x, 0), (x, 110)], fill=(r, g, b))

    # --- FONTS ---
    try:
        font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_wanted = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_section = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28) # "Identity particulars"
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_val = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8)
        font_stamp = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    except:
        font_name = ImageFont.load_default()
        font_wanted = ImageFont.load_default()
        font_section = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_val = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_stamp = ImageFont.load_default()

    # --- DONNEES ---
    offences = "TRAFIC DE TACOS, EXCÈS DE VITESSE, VOL DE GOUTER"
    gender = "Male"
    nationality = "France"
    place_of_birth = "Marseille, France"
    dob = f"{random.randint(1,28)}/{random.randint(1,12)}/{random.randint(1980, 2005)}"

    # Custom Owner (Fazer)
    if member.id == 1443339902623154207 or "fazer" in member.name.lower():
        gender = "Male"
        offences = "ASSOCIATION DE MALFAITEURS, TRAFIC AGGRAVÉ, BLANCHIMENT, IMPORTATION D'ARMES, PROXÉNÉTISME AGGRAVÉ, FÉTICHISME DES PIEDS"
        place_of_birth = "Marseille, France"

    # Custom User (1430659045026693120)
    if member.id == 1430659045026693120:
        gender = "Male"
        place_of_birth = "Tel Aviv, Israël"
        offences = "DÉBITAGE DISCORD"

    # Custom User (726868923819229195)
    if member.id == 726868923819229195:
        gender = "Male"
        nationality = "France"
        place_of_birth = "Metz, France"
        offences = "PROXÉNÉTISME AGGRAVÉ, TRAITE D'ÊTRES HUMAINS, VIOLENCES, CONDUITE ÉTAT D’IVRESSE"

    # --- IMAGES (AVATAR & LOGO) ---
    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            # 1. Avatar (Pas étirée)
            try:
                async with session.get(member.display_avatar.url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        avatar = Image.open(io.BytesIO(data)).convert("RGBA")
                        
                        # Resize en gardant le ratio
                        avatar.thumbnail((200, 250), Image.Resampling.LANCZOS)
                        # Créer un fond blanc pour la photo si pas remplie
                        photo_bg_w, photo_bg_h = 180, 220
                        # On crop le centre si trop grand ou on resize pour fit ?
                        # Mieux : Crop center to 180x220
                        # Calculer le ratio pour que la plus petite dimension soit >= target
                        ratio = max(photo_bg_w / avatar.width, photo_bg_h / avatar.height)
                        new_size = (int(avatar.width * ratio), int(avatar.height * ratio))
                        avatar = avatar.resize(new_size, Image.Resampling.LANCZOS)
                        
                        # Center crop
                        left = (avatar.width - photo_bg_w) / 2
                        top = (avatar.height - photo_bg_h) / 2
                        avatar = avatar.crop((left, top, left + photo_bg_w, top + photo_bg_h))
                        
                        # Cadre fin gris
                        photo_frame = Image.new('RGB', (182, 222), color=(200, 200, 200))
                        photo_frame.paste(avatar, (1, 1), avatar)
                        
                        # Position Photo (50, 60)
                        background.paste(photo_frame, (50, 60))
            except Exception as e:
                 print(f"Erreur avatar: {e}")

            # 2. Interpol Logo (Header + Badge)
            # Create Badge Placeholder first (Red Square) so it exists even if logo fails
            badge_size = 60
            badge = Image.new('RGB', (badge_size, badge_size), COLOR_RED)
            badge_draw = ImageDraw.Draw(badge)
            
            # Default Text on Badge if logo fails
            badge_draw.text((10, 38), "INTERPOL", fill=COLOR_WHITE, font=font_badge)
            badge_draw.text((20, 46), "RED", fill=COLOR_WHITE, font=font_badge)
            badge_draw.text((14, 52), "NOTICE", fill=COLOR_WHITE, font=font_badge)

            LOGO_URL = "https://upload.wikimedia.org/wikipedia/fr/thumb/e/ea/Interpol_Logo.svg/1200px-Interpol_Logo.svg.png"
            try:
                async with session.get(LOGO_URL) as resp_logo:
                    if resp_logo.status == 200:
                        l_data = await resp_logo.read()
                        logo_img = Image.open(io.BytesIO(l_data)).convert("RGBA")
                        
                        # A. LOGO HEADER (Top Left) -> REMOVED
                        # logo_header = logo_img.resize((80, 80))
                        # background.paste(logo_header, (20, 15), logo_header)

                        # B. BADGE ROUGE (Update with Logo)
                        # White version of logo for badge
                        logo_white = logo_img.resize((30, 30))
                        d = logo_white.getdata()
                        new_d = []
                        for item in d:
                            if item[3] > 0: # If not transparent
                                new_d.append((255, 255, 255, 255)) # White
                            else:
                                new_d.append(item)
                        logo_white.putdata(new_d)
                        
                        badge.paste(logo_white, (15, 5), logo_white)
                        
                        # C. LOGO EN BAS A GAUCHE
                        # Logo officiel couleur, taille moyenne
                        logo_bottom = logo_img.resize((100, 100))
                        # Position: (50, 320) - Sous la photo (qui finit vers 280)
                        background.paste(logo_bottom, (70, 320), logo_bottom)
                        
            except Exception as e:
                print(f"Erreur download logo interpol: {e}")
            
            # Collage du badge (Toujours, même si logo fail)
            background.paste(badge, (50 + 182 - 30, 60), badge)

    except Exception as e:
        print(f"Erreur globale interpol: {e}")


    # --- TEXTES HEADER ---
    # Shift text slightly right because of Logo
    text_x = 260
    draw.text((text_x, 30), f"{member.name.upper()}, {member.display_name.upper()}", fill=COLOR_WHITE, font=font_name)
    
    draw.text((text_x, 75), "Wanted by ", fill=COLOR_WHITE, font=font_wanted)
    w_width = draw.textlength("Wanted by ", font=font_wanted)
    draw.text((text_x + w_width, 75), "France", fill=(100, 200, 255), font=font_wanted)


    # --- CORPS DE PAGE ---
    y_start = 140
    draw.text((text_x, y_start), "Identity particulars", fill=COLOR_TEXT_DARK, font=font_section)

    # Données (Liste clé/valeur)
    y_data = y_start + 50
    gap_x = 150
    line_h = 25
    
    # Organization display
    org_display = f"{org_name} {org_role}".strip()
    if org_name == "Aucune":
        org_display = "Aucune"
    
    info_list = [
        ("Family name", member.name.upper()),
        ("Forename", member.display_name.upper()),
        ("Gender", gender),
        ("Date of birth", dob),
        ("Place of birth", place_of_birth),
        ("Nationality", nationality),
        ("Organization", org_display),
        ("Charges", offences)
    ]

    import textwrap

    for label, val in info_list:
        draw.text((text_x, y_data), label, fill=COLOR_TEXT_GREY, font=font_label)
        
        val_x = text_x + gap_x
        
        if label == "Charges":
            lines = textwrap.wrap(val, width=45)
            for line in lines:
                if y_data > height - 20: break
                draw.text((val_x, y_data), line, fill=COLOR_TEXT_DARK, font=font_val)
                y_data += 20
        else:
            draw.text((val_x, y_data), val, fill=COLOR_TEXT_DARK, font=font_val)
        
        y_data += line_h
        
    # --- TAMPON WANTED REMOVED ---
    
    # Custom Label for Fazer (Suspect N°1)
    if member.id == 1443339902623154207 or "fazer" in member.name.lower():
         # Draw Red Box above photo
         # Photo x=50, w=182. y=60.
         # Box: x=50, y=25, w=182, h=35
         draw.rectangle([(50, 25), (232, 60)], fill=COLOR_RED)
         
         # Text centered
         try:
             font_suspect = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
         except:
             font_suspect = ImageFont.load_default()
             
         text = "SUSPECT N°1"
         # Calculate text position to center using textlength/textbbox
         text_len = draw.textlength(text, font=font_suspect)
         text_x = 50 + (182 - text_len) // 2
         text_y = 30 # Approx vertical center
         
         draw.text((text_x, text_y), text, fill=COLOR_WHITE, font=font_suspect)

    # Sauvegarde
    buffer = io.BytesIO()
    background.save(buffer, format='PNG')
    buffer.seek(0)
    
    await ctx.send(file=discord.File(buffer, filename="interpol.png"))


def _generate_perdu_image_sync(avatar_bytes, member_name):
    import io
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    
    # --- CONFIG ---
    width, height = 600, 800
    background = Image.new('RGB', (width, height), color=(240, 230, 210)) # Papier jauni
    draw = ImageDraw.Draw(background)
    
    try:
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font_header = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # --- HEADER ---
    draw.rectangle([(20, 20), (width-20, height-20)], outline=(0,0,0), width=5)
    
    text = "PERDU DE VUE"
    try:
        length = draw.textlength(text, font=font_header)
    except: length = 300
    draw.text(((width - length) / 2, 50), text, fill=(200, 0, 0), font=font_header)

    # --- PHOTO ---
    if avatar_bytes:
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            avatar = avatar.resize((300, 300))
            # Grayscale
            avatar = ImageOps.grayscale(avatar)
            background.paste(avatar, ((width - 300) // 2, 150))
        except Exception as e:
            print(f"Erreur avatar perdu: {e}")

    # --- TEXTE ---
    y = 500
    name = member_name.upper()
    try: length = draw.textlength(name, font=font_sub)
    except: length = 100
    draw.text(((width - length) / 2, y), name, fill=(0,0,0), font=font_sub)
    
    y += 60
    desc = [
        "Aperçu pour la dernière fois en train de",
        "demander 10 balles à la gare.",
        "",
        "Signes distinctifs :",
        "- N'a pas fait son +daily",
        "- Porte des fausses TN",
        "",
        "Si vous le voyez, dites-lui de",
        "rembourser ses dettes."
    ]
    
    for line in desc:
        try: length = draw.textlength(line, font=font_text)
        except: length = 100
        draw.text(((width - length) / 2, y), line, fill=(50,50,50), font=font_text)
        y += 35

    # Save
    buffer = io.BytesIO()
    background.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

def _generate_idcard_image_sync(avatar_bytes, member_name, member_display_name, join_date, address):
    import io
    from PIL import Image, ImageDraw, ImageFont
    
    width, height = 600, 350
    background = Image.new('RGB', (width, height), color=(200, 220, 240)) # Bleu clair CNI
    draw = ImageDraw.Draw(background)
    
    # Guillochis (fake pattern)
    for i in range(0, width, 20):
        draw.line([(i, 0), (i, height)], fill=(180, 200, 230), width=1)
    
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_val = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_val = ImageFont.load_default()
        
    # Header
    draw.text((20, 15), "RÉPUBLIQUE DU SECTEUR", fill=(0, 50, 100), font=font_title)
    draw.text((20, 40), "CARTE D'IDENTITÉ", fill=(0, 50, 100), font=font_label)
    
    # Photo frame
    if avatar_bytes:
        try:
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            avatar = avatar.resize((100, 100))
            # Extract alpha channel for mask
            mask = avatar.split()[3]
            background.paste(avatar, (20, 80), mask)
        except Exception as e:
            print(f"Erreur avatar idcard: {e}")
            pass
        
    # Info
    x = 140
    y = 80
    
    fields = [
        ("Nom", member_name),
        ("Prénom", member_display_name),
        ("Né(e) le", join_date),
        ("Taille", "1m12 les bras levés"),
        ("Sexe", "Vaillant"),
        ("Adresse", address)
    ]
    
    for label, val in fields:
        draw.text((x, y), label + ":", fill=(100, 100, 100), font=font_label)
        draw.text((x + 80, y), val, fill=(0, 0, 0), font=font_val)
        y += 25
        
    # Signature
    draw.text((x, y+20), "Signature:", fill=(100, 100, 100), font=font_label)
    draw.text((x+80, y+20), member_display_name, fill=(0, 0, 0), font=font_title)

    buffer = io.BytesIO()
    background.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


@bot.command(name="perdu")
@commands.cooldown(1, 10, commands.BucketType.user)
async def perdu(ctx: commands.Context, member: discord.Member = None):
    """Affiche un avis de recherche 'Perdu de vue'"""
    member = member or ctx.author
    
    import aiohttp

    # --- PHOTO (Async) ---
    avatar_bytes = None
    try:
        async with aiohttp.ClientSession() as session:
            url = member.display_avatar.url
            async with session.get(url) as resp:
                if resp.status == 200:
                    avatar_bytes = await resp.read()
    except Exception as e:
        print(f"Erreur avatar perdu: {e}")

    # --- GENERATION (Sync in Executor) ---
    import io
    buffer = await bot.loop.run_in_executor(None, _generate_perdu_image_sync, avatar_bytes, member.display_name)
    
    await ctx.send(file=discord.File(buffer, filename="perdu.png"))


@bot.command(name="idcard")
@commands.cooldown(1, 10, commands.BucketType.user)
async def idcard(ctx: commands.Context, member: discord.Member = None):
    """Affiche la Carte d'Identité du Quartier"""
    member = member or ctx.author
    
    import aiohttp
    
    # --- PHOTO (Async) ---
    avatar_bytes = None
    try:
        async with aiohttp.ClientSession() as session:
            url = member.display_avatar.url
            async with session.get(url) as resp:
                if resp.status == 200:
                    avatar_bytes = await resp.read()
    except Exception:
        pass
        
    # --- DB INFO (Async) ---
    address = "En bas du bloc"
    economy_cog = bot.get_cog('Economy')
    if economy_cog:
        try:
            await economy_cog._connect()
            async with economy_cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT c.name FROM clans c JOIN clan_members m ON c.id=m.clan_id WHERE m.user_id=%s", (member.id,))
                    res = await cur.fetchone()
                    if res:
                        address = f"QG {res[0]}"
        except Exception: pass

    # --- GENERATION (Sync in Executor) ---
    joined_at = getattr(member, "joined_at", None)
    if joined_at:
        join_date = joined_at.strftime("%d/%m/%Y")
    else:
        join_date = "??/??/????"
    
    import io
    buffer = await bot.loop.run_in_executor(
        None, 
        _generate_idcard_image_sync, 
        avatar_bytes, 
        member.name.upper(), 
        member.display_name, 
        join_date, 
        address
    )

    await ctx.send(file=discord.File(buffer, filename="cni.png"))


@bot.command(name="diplome")
@commands.cooldown(1, 10, commands.BucketType.user)
async def diplome(ctx: commands.Context, member: discord.Member = None):
    """Affiche le Diplôme de la Rue"""
    member = member or ctx.author
    import io
    from PIL import Image, ImageDraw, ImageFont
    import aiohttp
    
    width, height = 800, 600
    background = Image.new('RGB', (width, height), color=(255, 250, 240)) # Papier crème
    draw = ImageDraw.Draw(background)
    
    # Cadre
    draw.rectangle([(20, 20), (width-20, height-20)], outline=(150, 100, 50), width=10)
    draw.rectangle([(35, 35), (width-35, height-35)], outline=(200, 150, 100), width=2)
    
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font_title = ImageFont.load_default()
        font_main = ImageFont.load_default()
        font_name = ImageFont.load_default()

    # Content
    y = 100
    
    text = "UNIVERSITÉ DE LA RUE"
    try: length = draw.textlength(text, font=font_title)
    except: length = 400
    draw.text(((width - length) / 2, y), text, fill=(100, 50, 0), font=font_title)
    
    y += 100
    text = "Ce diplôme est décerné à"
    try: length = draw.textlength(text, font=font_main)
    except: length = 300
    draw.text(((width - length) / 2, y), text, fill=(0, 0, 0), font=font_main)
    
    y += 60
    text = member.display_name
    try: length = draw.textlength(text, font=font_name)
    except: length = 200
    draw.text(((width - length) / 2, y), text, fill=(0, 0, 100), font=font_name)
    
    # Determine grade based on money
    grade = "Galérien Certifié"
    economy_cog = bot.get_cog('Economy')
    if economy_cog:
        try:
            await economy_cog._connect()
            async with economy_cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT balance + bank FROM users WHERE user_id=%s", (member.id,))
                    res = await cur.fetchone()
                    if res:
                        total = res[0]
                        if total > 10_000_000: grade = "Master en Blanchiment"
                        elif total > 1_000_000: grade = "Licence de Millionnaire"
                        elif total > 100_000: grade = "BTS Business"
                        elif total > 10_000: grade = "Bac Pro Débrouille"
        except: pass

    y += 80
    text_intro = "Pour l'obtention du grade de :"
    try: length = draw.textlength(text_intro, font=font_main)
    except: length = 300
    draw.text(((width - length) / 2, y), text_intro, fill=(0,0,0), font=font_main)
    
    y += 50
    try: length = draw.textlength(grade, font=font_title)
    except: length = 300
    draw.text(((width - length) / 2, y), grade, fill=(200, 0, 0), font=font_title)
    
    # Sceau
    draw.ellipse([(600, 450), (700, 550)], fill=(150, 0, 0))
    draw.text((620, 490), "VALIDE", fill=(255,255,255), font=font_main)

    buffer = io.BytesIO()
    background.save(buffer, format='PNG')
    buffer.seek(0)
    await ctx.send(file=discord.File(buffer, filename="diplome.png"))


@bot.command(name="parions")
@commands.cooldown(1, 10, commands.BucketType.user)
async def parions(ctx: commands.Context):
    """Génère un ticket de pari sportif fun"""
    import io
    import random
    import datetime
    import aiohttp
    from PIL import Image, ImageDraw, ImageFont

    width, height = 400, 600
    background = Image.new('RGB', (width, height), color=(255, 255, 240)) # Papier thermique un peu jaune
    draw = ImageDraw.Draw(background)
    
    try:
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
        font_status = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        font_header = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_mono = ImageFont.load_default()
        font_status = ImageFont.load_default()

    # Logo / Header
    draw.rectangle([(0,0), (width, 80)], fill=(0, 50, 150)) # Blue header
    
    # Fetch Logo FDJ (Cached)
    logo_img = getattr(bot, "fdj_cache", None)
    
    if logo_img is None:
        try:
            async with aiohttp.ClientSession() as session:
                 async with session.get("https://www.bertrand-sport-avocat.com/images/logos/Institutions%20et%20Tribunaux/logo_FdJ.png") as resp:
                     if resp.status == 200:
                         data = await resp.read()
                         logo_raw = Image.open(io.BytesIO(data)).convert("RGBA")
                         # Resize small
                         ratio = logo_raw.width / logo_raw.height
                         new_h = 30
                         new_w = int(new_h * ratio)
                         logo_img = logo_raw.resize((new_w, new_h))
                         bot.fdj_cache = logo_img
        except Exception as e:
            print(f"Error logo parions: {e}")
            
    if logo_img:
        # Place at top left
        background.paste(logo_img, (15, 20), logo_img)

    text = "PARIONS STREET"
    try: l = draw.textlength(text, font=font_header)
    except: l = 200
    draw.text(((width-l)/2 + 20, 25), text, fill=(255,255,255), font=font_header)
    
    # Info
    y = 100
    date_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    draw.text((20, y), f"Date: {date_str}", fill=(0,0,0), font=font_mono)
    draw.text((20, y+20), f"Joueur: {ctx.author.display_name}", fill=(0,0,0), font=font_mono)
    
    y += 60
    draw.line([(20, y), (width-20, y)], fill=(0,0,0), width=2)
    y += 20
    
    # Bets
    matches = [
        ("OM vs PSG", "1 (OM)", "5.50"),
        ("Nasdas vs Sarkozy", "1 (KO)", "2.10"),
        ("Labubu vs Tung tung sahur", "2 (Tung tung)", "1.80"),
        ("XADV vs Tmax", "2 (Tmax volé)", "1.05"),
        ("Fazer prison 2026 ?", "OUI (Sûr)", "1.01"),
        ("Jul vs Beethoven", "1 (Le J)", "1.10"),
        ("Marseille vs Monde", "1 (Jamais on perd)", "1.00"),
        ("Kebab vs Tacos", "2 (Sauce Algérienne)", "1.50"),
        ("Twingo vs Ferrari", "1 (Stage 3)", "50.0"),
        ("Bitcoin vs RSA", "2 (Sûr)", "1.10"),
        ("Météo Marseille", "Soleil", "1.01"),
        ("Contrôle vs Fuite", "2 (Fuite)", "2.00")
    ]
    
    selected = random.sample(matches, 3)
    total_cote = 1.0
    
    for match, bet, cote in selected:
        draw.text((20, y), match, fill=(0,0,0), font=font_bold)
        draw.text((width-60, y), cote, fill=(0,0,0), font=font_bold)
        y += 20
        draw.text((20, y), f"👉 {bet}", fill=(50,50,50), font=font_mono)
        y += 30
        total_cote *= float(cote)
        
    y += 10
    draw.line([(20, y), (width-20, y)], fill=(0,0,0), width=2)
    y += 20
    
    # Mise & Gain
    mise = random.choice([10, 20, 50, 100, 500])
    gain = int(mise * total_cote)
    
    draw.text((20, y), f"Mise Totale :", fill=(0,0,0), font=font_bold)
    draw.text((width-100, y), f"{mise} €", fill=(0,0,0), font=font_bold)
    y += 30
    draw.text((20, y), f"Cote Totale :", fill=(0,0,0), font=font_bold)
    draw.text((width-100, y), f"{total_cote:.2f}", fill=(0,0,0), font=font_bold)
    y += 30
    draw.text((20, y), f"GAIN POTENTIEL :", fill=(0,0,0), font=font_bold)
    draw.text((width-200, y+30), f"{gain} €", fill=(0,100,0), font=font_header)
    
    # Status Stamp
    status = random.choice(["GAGNÉ", "PERDU", "PERDU", "PERDU"]) # More likely to lose
    color = (0, 150, 0) if status == "GAGNÉ" else (200, 0, 0)
    
    # Rotate text for stamp effect
    stamp = Image.new('RGBA', (300, 100), (0,0,0,0))
    d_stamp = ImageDraw.Draw(stamp)
    d_stamp.rectangle([(10,10), (280, 80)], outline=color, width=5)
    try: l = d_stamp.textlength(status, font=font_status)
    except: l = 100
    d_stamp.text(((290-l)/2, 20), status, fill=color, font=font_status)
    
    stamp = stamp.rotate(15, expand=1)
    background.paste(stamp, (50, 400), stamp)

    # Barcode at bottom
    for i in range(20, width-20, 5):
        h = random.randint(30, 50)
        draw.line([(i, height-60), (i, height-60+h)], fill=(0,0,0), width=2)

    buffer = io.BytesIO()
    background.save(buffer, format='PNG')
    buffer.seek(0)
    await ctx.send(file=discord.File(buffer, filename="parions.png"))








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
        emb.add_field(name="+work / /khedma", value="Travail (+bonus Orga)", inline=False)
        emb.add_field(
            name="PMU Street",
            value="course start [durée], bet <num> <mise>, course run, horsebuy <nom>, course addhorse <nom>, horserename <ancien> <nouveau>",
            inline=False
        )
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
        await bot.reload_extension("cogs.economy")
        await bot.tree.sync()
        await ctx.send("Cog économie rechargé et slash synchronisés.")
    except Exception as e:
        await ctx.send(f"Échec reload: {e}")



# ------- COMMANDES FUN TYPE KOYA -------


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
