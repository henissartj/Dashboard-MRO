import discord
from discord.ext import commands
from gtts import gTTS
import os
import asyncio
import random
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

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

    @commands.group(name="jdr", aliases=["jdrstats", "fiche"], invoke_without_command=True)
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

    @jdr.command(name="map")
    async def jdr_map(self, ctx):
        """Génère une carte aléatoire JDR 100x100."""
        msg = await ctx.send("🎨 Génération de la carte en cours... (ça peut prendre quelques secondes)")
        
        # Grid setup
        width, height = 100, 100
        grid = np.zeros((width, height), dtype=int) # 0 = Herbe

        # Entities config: (ID, Size, Count, Label, ColorCode)
        # 0: Herbe (Green)
        # 1: Capitale (8x8) - Red
        # 2: Ville (3x3) - Blue
        # 3: Village (2x2) - Cyan/Orange
        # 4: Mine (2x2) - Grey
        # 5: Donjon (1x1) - Purple/Black
        
        entities = [
            {"id": 1, "size": 8, "count": 1, "name": "Capitale"},
            {"id": 2, "size": 3, "count": 3, "name": "Ville"},
            {"id": 3, "size": 2, "count": 6, "name": "Village"},
            {"id": 4, "size": 2, "count": 10, "name": "Mine"},
            {"id": 5, "size": 1, "count": 20, "name": "Donjon"},
        ]

        def place_entity(entity_id, size, count):
            placed = 0
            attempts = 0
            max_attempts = 5000 # Safety break
            
            while placed < count and attempts < max_attempts:
                attempts += 1
                # Random pos
                x = random.randint(0, width - size)
                y = random.randint(0, height - size)
                
                # Check collision (slice check)
                # We check the area plus 1px padding to avoid stickiness if desired, 
                # but user didn't ask for padding. Let's stick to strict collision.
                area = grid[x:x+size, y:y+size]
                if np.any(area != 0):
                    continue
                
                # Place
                grid[x:x+size, y:y+size] = entity_id
                placed += 1

        # Generate in order of size (Big first)
        for e in entities:
            place_entity(e["id"], e["size"], e["count"])

        # Render
        # Custom colormap
        # 0=Green(#2ecc71), 1=Red(#e74c3c), 2=Blue(#3498db), 3=Orange(#e67e22), 4=Grey(#95a5a6), 5=Purple(#9b59b6)
        colors = ['#2ecc71', '#e74c3c', '#3498db', '#e67e22', '#7f8c8d', '#8e44ad']
        cmap = ListedColormap(colors)
        
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.imshow(grid.T, cmap=cmap, origin='upper')
        ax.set_xticks(np.arange(-0.5, width, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, height, 1), minor=True)
        ax.grid(which="minor", color="#2c3e50", linestyle='-', linewidth=0.2)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        
        # Add legend manually
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#e74c3c', label='Capitale (8x8)'),
            Patch(facecolor='#3498db', label='Ville (3x3)'),
            Patch(facecolor='#e67e22', label='Village (2x2)'),
            Patch(facecolor='#7f8c8d', label='Mine (2x2)'),
            Patch(facecolor='#8e44ad', label='Donjon (1x1)'),
            Patch(facecolor='#2ecc71', label='Plaine'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))

        plt.title(f"Carte du Monde - Groupe {random.randint(100, 999)}")
        plt.tight_layout()

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        # Send
        file = discord.File(fp=buf, filename="map.png")
        await msg.delete()
        await ctx.send(f"🗺️ **Carte générée pour {ctx.author.display_name}**", file=file)

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
