import discord
from discord.ext import commands
from gtts import gTTS
import os
import asyncio
import random

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tts", help="Le bot rejoint ton vocal et lit ton message.")
    async def tts(self, ctx, *, text: str):
        """Fait parler le bot dans le salon vocal."""
        if not ctx.author.voice:
            await ctx.send("❌ Tu dois être dans un salon vocal pour utiliser cette commande.")
            return

        channel = ctx.author.voice.channel
        vc = ctx.voice_client

        # Connect to voice logic
        try:
            if vc and vc.is_connected():
                if vc.channel.id != channel.id:
                    await vc.move_to(channel)
            else:
                vc = await channel.connect()
        except discord.ClientException:
            # Already connected in a way d.py didn't track well?
            await ctx.send("❌ Je suis déjà connecté ailleurs ou buggé. Essaie +leave et réessaie.")
            return
        except Exception as e:
            await ctx.send(f"❌ Impossible de rejoindre le vocal : {e}")
            return

        # Ensure vc is valid
        if not vc:
             vc = ctx.voice_client

        # Generate TTS
        filepath = f"/tmp/tts_{ctx.message.id}.mp3"
        try:
            # Create TTS file
            tts = gTTS(text=text, lang='fr')
            tts.save(filepath)

            # Play audio
            if vc.is_playing():
                vc.stop()
            
            # FFmpegPCMAudio requires ffmpeg installed on system
            source = discord.FFmpegPCMAudio(filepath)
            
            def after_playing(error):
                if os.path.exists(filepath):
                    os.remove(filepath)
                if error:
                    print(f"Player error: {error}")

            vc.play(source, after=after_playing)
            await ctx.send(f"🗣️ **{ctx.author.name}** fait dire : *{text}*")
            
        except Exception as e:
            await ctx.send(f"❌ Erreur TTS : {e}")
            if os.path.exists(filepath):
                os.remove(filepath)

    @commands.command(name="jdr", aliases=["jdrstats", "fiche"])
    async def jdr(self, ctx):
        vie1 = random.randint(1, 20)
        vie2 = random.randint(1, 20)
        vie = vie1 + vie2
        defense = random.randint(1, 20)
        force = random.randint(1, 20)
        vitesse = random.randint(1, 100)
        esquive = min(random.randint(1, 20), 10)
        mana = random.randint(1, 100) + random.randint(1, 100)
        intelligence = min(random.randint(1, 20), 15)
        marchandage = min(random.randint(1, 20), 15)

        embed = discord.Embed(
            title="🎲 Fiche de personnage JDR",
            color=discord.Color.purple()
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        embed.add_field(name="Vie", value=f"{vie} (2d20)", inline=True)
        embed.add_field(name="Défense", value=f"{defense} (1d20)", inline=True)
        embed.add_field(name="Force", value=f"{force} (1d20)", inline=True)
        embed.add_field(name="Vitesse", value=f"{vitesse} (1d100)", inline=True)
        embed.add_field(name="Esquive", value=f"{esquive} (1d20, max 10)", inline=True)
        embed.add_field(name="Mana", value=f"{mana} (2d100)", inline=True)
        embed.add_field(name="Intelligence", value=f"{intelligence} (1d20, max 15)", inline=True)
        embed.add_field(name="Marchandage", value=f"{marchandage} (1d20, max 15)", inline=True)

        await ctx.send(embed=embed)

    @commands.command(name="leave", aliases=["disconnect", "deco"])
    async def leave(self, ctx):
        """Déconnecte le bot du vocal."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect(force=True)
            await ctx.send("👋 J'me tire.")
        else:
            await ctx.send("❌ J'suis pas en vocal frero.")

async def setup(bot):
    await bot.add_cog(Fun(bot))
