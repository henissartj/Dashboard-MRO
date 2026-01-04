import discord
from discord.ext import commands
from datetime import datetime

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["aide", "h"])
    async def help_command(self, ctx):
        """Affiche le menu d'aide catégorisé."""
        
        prefix = ctx.prefix if ctx.prefix else "+"
        
        embed = discord.Embed(
            title="📚 Menu d'Aide - Bot de Fazer",
            description=f"Utilisez `{prefix}commande` pour effectuer une action.\nPour plus de détails sur une commande spécifique (ex: `{prefix}immo`), tapez simplement la commande.",
            color=0x2b2d31, # Dark theme friendly
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_footer(text=f"Demandé par {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

        # --- 🏦 Banque & Paliers ---
        bank_cmds = [
            f"`{prefix}depobank <1-3> <montant>` : Déposer (Plafond selon Palier)",
            f"`{prefix}withbank <1-3> <montant>` : Retirer",
            f"`{prefix}upgrade_bank` : Améliorer son compte bancaire (Augmenter plafond)",
            f"`{prefix}card` : Voir sa carte et ses comptes",
            f"`{prefix}facture <@user> <montant> [motif]` : Envoyer une facture"
        ]
        embed.add_field(name="🏦 Banque & Paliers", value="\n".join(bank_cmds), inline=False)
        
        # --- 🔫 Activités Illégales ---
        illegal_cmds = [
            f"`{prefix}braquage <@user>` : Tenter de braquer un joueur",
            f"`{prefix}gofast` : Lancer un Go-Fast (Risqué)",
            f"`{prefix}work` : Travailler légalement (Gain faible)"
        ]
        embed.add_field(name="🔫 Activités (Risque & Gain)", value="\n".join(illegal_cmds), inline=False)

        # --- 💰 Économie & Banque ---
        eco_cmds = [
            f"`{prefix}balance` : Voir votre solde",
            f"`{prefix}send <@joueur> <montant>` : Envoyer de l'argent",
            f"`{prefix}transactions` : Historique des transactions",
            f"`{prefix}leaderboard` : Classement des richesses"
        ]
        embed.add_field(name="💰 Économie Globale", value="\n".join(eco_cmds), inline=False)

        # --- 🏢 Immobilier & Luxe ---
        immo_cmds = [
            f"`{prefix}immo` : Menu Immobilier (Acheter/Louer/Collecter)",
            f"`{prefix}luxury` : Boutique de Luxe (Sacs, Montres...)",
            f"`{prefix}assets` : Voir votre patrimoine (Immo & Luxe)",
            f"`{prefix}facture <@user> <montant> <motif>` : Créer une facture",
            f"`{prefix}payfacture <id>` : Payer une facture reçue"
        ]
        embed.add_field(name="🏢 Immobilier & Luxe", value="\n".join(immo_cmds), inline=False)

        # --- 🎰 Casino & Jeux ---
        game_cmds = [
            f"`{prefix}slots <mise>` : Machine à sous",
            f"`{prefix}roulette <mise> <choix>` : Roulette Casino",
            f"`{prefix}blackjack <mise>` : Blackjack (21)",
            f"`{prefix}coinflip <mise> <pile/face>` : Pile ou Face",
            f"`{prefix}dice <mise> <choix>` : Jeu de Dés",
            f"`{prefix}mines <mise> <nb_mines>` : Démineur",
            f"`{prefix}ladder <mise>` : Tenter l'échelle de gains",
            f"`{prefix}risk <mise> <min-max>` : Pari sur bande de risque",
            f"`{prefix}scoot <@joueur> <mise>` : Course de scooters",
            f"`{prefix}vol <@joueur>` : Tenter un vol (Risqué !)"
        ]
        embed.add_field(name="🎰 Casino & Jeux", value="\n".join(game_cmds), inline=False)

        # --- 💼 Travail & Revenus ---
        work_cmds = [
            f"`{prefix}khedma` : Travailler (Petits boulots)",
            f"`{prefix}daily` : Récompense journalière",
            f"`{prefix}weekly` : Récompense hebdomadaire",
            f"`{prefix}monthly` : Récompense mensuelle",
            f"`{prefix}portefeuille` : Vos investissements Bourse"
        ]
        embed.add_field(name="💼 Travail & Revenus", value="\n".join(work_cmds), inline=False)

        # --- 🛍️ Shop & Inventaire ---
        shop_cmds = [
            f"`{prefix}shop` : Boutique générale",
            f"`{prefix}buy <item>` : Acheter un objet",
            f"`{prefix}sell <item>` : Vendre un objet",
            f"`{prefix}inventory` : Voir votre inventaire"
        ]
        embed.add_field(name="🛍️ Shop & Inventaire", value="\n".join(shop_cmds), inline=False)

        # --- 🛡️ Admin / Police ---
        if ctx.author.guild_permissions.administrator:
            admin_cmds = [
                f"`{prefix}audit <@user>` : Voir tout le patrimoine d'un joueur",
                f"`{prefix}admin_assets list/remove <user>` : Gérer les assets d'un joueur",
                f"`{prefix}toggle_logs <on/off>` : Activer/Désactiver les logs"
            ]
            embed.add_field(name="🛡️ Admin / Police", value="\n".join(admin_cmds), inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
