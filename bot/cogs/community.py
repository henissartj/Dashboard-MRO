import discord
from discord.ext import commands
import asyncio
import time
import datetime

class Community(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_data = {} # {user_id: {'reason': reason, 'time': timestamp}}

    @commands.command(name="userinfo", aliases=["ui", "info", "user"])
    async def userinfo(self, ctx, member: discord.Member = None):
        """Affiche les informations sur un utilisateur."""
        member = member or ctx.author
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        
        embed = discord.Embed(title=f"👤 Info Utilisateur : {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Nom", value=member.name, inline=True)
        if member.nick:
            embed.add_field(name="Surnom", value=member.nick, inline=True)
        embed.add_field(name="Créé le", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="Rejoint le", value=member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Inconnu", inline=True)
        embed.add_field(name=f"Rôles ({len(roles)})", value=" ".join(roles) if roles else "Aucun", inline=False)
        embed.set_footer(text=f"Demandé par {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo", aliases=["si", "server", "serveur"])
    async def serverinfo(self, ctx):
        """Affiche les informations sur le serveur."""
        guild = ctx.guild
        embed = discord.Embed(title=f"🏰 Info Serveur : {guild.name}", color=discord.Color.blue())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="Propriétaire", value=guild.owner.mention, inline=True)
        embed.add_field(name="Membres", value=guild.member_count, inline=True)
        embed.add_field(name="Salons", value=len(guild.channels), inline=True)
        embed.add_field(name="Rôles", value=len(guild.roles), inline=True)
        embed.add_field(name="Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.set_footer(text=f"ID: {guild.id}")
        await ctx.send(embed=embed)

    @commands.command(name="avatar", aliases=["pp", "pdp"])
    async def avatar(self, ctx, member: discord.Member = None):
        """Affiche la photo de profil en grand."""
        member = member or ctx.author
        embed = discord.Embed(title=f"🖼️ Avatar de {member.display_name}", color=member.color)
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="banner", aliases=["banniere", "ban"])
    async def banner(self, ctx, member: discord.Member = None):
        """Affiche la bannière d'un utilisateur."""
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)
        
        if user.banner:
            embed = discord.Embed(title=f"🚩 Bannière de {user.display_name}", color=user.color)
            embed.set_image(url=user.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ **{user.display_name}** n'a pas de bannière.", delete_after=5)

    @commands.command(name="ping", aliases=["latence"])
    async def ping(self, ctx):
        """Affiche la latence du bot."""
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(
            f"Pong {ctx.author.mention} ! T’es vif à {latency_ms} ms, "
            f"t’es une fibre optique mon frero bsaha 💥"
        )

    @commands.command(name="members", aliases=["membres"])
    async def members(self, ctx):
        """Affiche le nombre de membres."""
        embed = discord.Embed(title="👥 Membres", description=f"Il y a **{ctx.guild.member_count}** habitants à Fazer City.", color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(name="afk")
    async def afk(self, ctx, *, reason="AFK"):
        """Te met en mode AFK."""
        self.afk_data[ctx.author.id] = {
            'reason': reason,
            'time': time.time()
        }
        await ctx.send(f"💤 {ctx.author.mention} est maintenant AFK : **{reason}**")
        try:
            if not ctx.author.display_name.startswith("[AFK] "):
                await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}"[:32])
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        # Remove AFK if author sends a message
        if message.author.id in self.afk_data:
            data = self.afk_data[message.author.id]
            # Check if 10 seconds have passed since AFK command
            if time.time() - data['time'] > 10:
                del self.afk_data[message.author.id]
                await message.channel.send(f"👋 Bon retour {message.author.mention}, j'ai enlevé ton AFK.", delete_after=5)
                try:
                    # Remove [AFK] from nick if present
                    if message.author.display_name.startswith("[AFK] "):
                        new_nick = message.author.display_name[6:]
                        await message.author.edit(nick=new_nick)
                except:
                    pass

        # Check mentions
        if message.mentions:
            for user in message.mentions:
                if user.id in self.afk_data:
                    data = self.afk_data[user.id]
                    reason = data['reason']
                    await message.channel.send(f"💤 **{user.display_name}** est AFK : {reason}", delete_after=10)

    @commands.command(name="rep", aliases=["reputation", "+rep"])
    async def rep(self, ctx, member: discord.Member):
        """Donne un point de réputation à un utilisateur (toutes les 24h)."""
        if member.id == ctx.author.id:
            return await ctx.send("❌ Tu ne peux pas te donner de la réputation à toi-même !")
        
        if member.bot:
            return await ctx.send("❌ Tu ne peux pas donner de réputation à un bot.")

        cog_economy = self.bot.get_cog("Economy")
        if not cog_economy:
            return await ctx.send("❌ Le système d'économie est indisponible.")
            
        await cog_economy._connect()
        async with cog_economy.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Ensure columns exist (Migration hack for hot-reload/updates)
                try:
                    await cur.execute("SELECT rep FROM user_stats LIMIT 1")
                except Exception:
                    try:
                        await cur.execute("ALTER TABLE user_stats ADD COLUMN rep INT DEFAULT 0")
                        await cur.execute("ALTER TABLE user_stats ADD COLUMN last_rep_give_time TIMESTAMP NULL")
                    except Exception:
                        pass

                # Check cooldown for giver
                await cur.execute("SELECT last_rep_give_time FROM user_stats WHERE user_id=%s", (ctx.author.id,))
                row = await cur.fetchone()
                
                now = datetime.datetime.now()
                
                if row and row[0]:
                    last_time = row[0]
                    diff = now - last_time
                    if diff.total_seconds() < 86400: # 24 hours
                        next_time = last_time + datetime.timedelta(hours=24)
                        timestamp = int(next_time.timestamp())
                        return await ctx.send(f"⏳ Tu dois attendre <t:{timestamp}:R> avant de redonner de la réputation.")
                
                # Update Giver (last_rep_time)
                await cur.execute("""
                    INSERT INTO user_stats (user_id, last_rep_give_time) 
                    VALUES (%s, %s) 
                    ON DUPLICATE KEY UPDATE last_rep_give_time=%s
                """, (ctx.author.id, now, now))
                
                # Update Receiver (rep + 1)
                await cur.execute("""
                    INSERT INTO user_stats (user_id, rep) 
                    VALUES (%s, 1) 
                    ON DUPLICATE KEY UPDATE rep = rep + 1
                """, (member.id,))
                
                # Get new rep count
                await cur.execute("SELECT rep FROM user_stats WHERE user_id=%s", (member.id,))
                new_rep = (await cur.fetchone())[0]
                
        await ctx.send(f"✅ **{ctx.author.display_name}** a donné un point de réputation à **{member.display_name}** ! (Total: {new_rep})")

    @commands.command(name="top", aliases=["lb_rep", "repleaderboard"])
    async def top(self, ctx):
        """Affiche le classement de réputation."""
        cog_economy = self.bot.get_cog("Economy")
        if not cog_economy:
            return await ctx.send("❌ Le système d'économie est indisponible.")

        await cog_economy._connect()
        async with cog_economy.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute("SELECT user_id, rep FROM user_stats WHERE rep > 0 ORDER BY rep DESC LIMIT 10")
                    rows = await cur.fetchall()
                except Exception:
                     return await ctx.send("❌ Aucun classement disponible (Table non mise à jour).")
        
        if not rows:
            return await ctx.send("❌ Aucun point de réputation n'a été donné pour l'instant.")
            
        description_lines = []
        for i, (uid, rep) in enumerate(rows):
            user = ctx.guild.get_member(uid)
            name = user.display_name if user else f"Utilisateur Inconnu ({uid})"
            description_lines.append(f"**#{i+1}** {name} — **{rep}** rep")
            
        embed = discord.Embed(title="🏆 Classement de Réputation", description="\n".join(description_lines), color=discord.Color.gold())
        await ctx.send(embed=embed)

    @commands.command(name="suggest", aliases=["suggestion", "idee", "idea"])
    async def suggest(self, ctx, *, content: str):
        """
        Propose une idée pour le serveur.
        Usage: +suggest <votre idée>
        """
        # Delete the command message to keep things clean
        try:
            await ctx.message.delete()
        except:
            pass

        # Try to find a suitable channel
        channel_names = ["suggestions", "idées", "idees", "avis", "propositions"]
        channel = None
        for name in channel_names:
            channel = discord.utils.get(ctx.guild.text_channels, name=name)
            if channel:
                break
        
        if not channel:
            return await ctx.send(f"❌ Impossible de trouver un salon de suggestions ({', '.join(channel_names)}). Demande à un admin d'en créer un.", delete_after=10)

        embed = discord.Embed(description=content, color=discord.Color.blue())
        embed.set_author(name=f"Suggestion de {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"ID: {ctx.author.id} • Votez avec les réactions !")
        
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        # Create a thread for discussion
        try:
            await msg.create_thread(name=f"Discussion: {content[:20]}...", auto_archive_duration=1440)
        except:
            # Thread creation might fail if bot lacks permissions or guild doesn't support it
            pass
        
        await ctx.send(f"✅ Ta suggestion a été envoyée dans {channel.mention} !", delete_after=5)

    @commands.command(name="poll", aliases=["sondage"])
    async def poll(self, ctx, question: str, *options):
        """
        Crée un sondage.
        Usage: +poll "Question ?" "Choix 1" "Choix 2" ...
        """
        # Delete command message
        try:
            await ctx.message.delete()
        except:
            pass

        if len(options) > 10:
            return await ctx.send("❌ Maximum 10 options.", delete_after=5)
        
        if not options:
            # Yes/No poll
            embed = discord.Embed(title="📊 Sondage", description=question, color=discord.Color.gold())
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
        else:
            # Multiple choice
            description_lines = []
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            
            for i, option in enumerate(options):
                description_lines.append(f"{emojis[i]} {option}")
            
            embed = discord.Embed(title=question, description="\n\n".join(description_lines), color=discord.Color.gold())
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            
            msg = await ctx.send(embed=embed)
            for i in range(len(options)):
                await msg.add_reaction(emojis[i])

    @commands.command(name="report", aliases=["signaler", "bug"])
    async def report(self, ctx, *, content: str):
        """
        Signale un bug, un problème, ou un utilisateur.
        Usage: +report <description ou @utilisateur raison>
        """
        try:
            await ctx.message.delete()
        except:
            pass

        channel_names = ["reports", "signalements", "bugs", "plaintes", "admin-only"]
        channel = None
        for name in channel_names:
            channel = discord.utils.get(ctx.guild.text_channels, name=name)
            if channel:
                break
        
        if not channel:
            return await ctx.send(f"❌ Impossible de trouver un salon de signalement ({', '.join(channel_names)}). Contactez un admin.", delete_after=10)

        # Detect if a user is mentioned
        reported_user = None
        if ctx.message.mentions:
            reported_user = ctx.message.mentions[0]

        if reported_user:
            # User Report
            embed = discord.Embed(title="🚨 Signalement d'Utilisateur", color=discord.Color.orange())
            embed.add_field(name="Utilisateur Signalé", value=f"{reported_user.mention} (ID: {reported_user.id})", inline=False)
            embed.add_field(name="Raison / Détails", value=content, inline=False)
        else:
            # General Bug/Problem Report
            embed = discord.Embed(title="🐛 Signalement / Bug", description=content, color=discord.Color.red())

        embed.set_author(name=f"Signalé par {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {ctx.author.id} • Channel: #{ctx.channel.name}")
        embed.timestamp = ctx.message.created_at
        
        await channel.send(embed=embed)
        await ctx.send(f"✅ Ton signalement a été transmis à l'équipe !", delete_after=5)



async def setup(bot):
    await bot.add_cog(Community(bot))
