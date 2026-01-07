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
            f"`{prefix}course` : Courses Hippiques (PMU Street) 🐎",
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

        # --- 📸 Images & Fun ---
        fun_cmds = [
            f"`{prefix}parions` : Ticket Parions Street (FDJ)",
            f"`{prefix}perdu <@user>` : Avis de recherche",
            f"`{prefix}idcard <@user>` : Carte d'identité",
            f"`{prefix}diplome <@user>` : Diplôme certifié"
        ]
        embed.add_field(name="📸 Images & Fun", value="\n".join(fun_cmds), inline=False)
        
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
            f"`{prefix}giveitem <@joueur> <item> <qte>` : Donner un objet",
            f"`{prefix}inventory` : Voir votre inventaire"
        ]
        embed.add_field(name="🛍️ Shop & Inventaire", value="\n".join(shop_cmds), inline=False)

        # --- 🏆 Social & Organisation ---
        social_cmds = [
            f"`{prefix}profile` : Voir votre profil complet (Badges, Orga, Mariage)",
            f"`{prefix}marry <@user>` : Demander en mariage",
            f"`{prefix}org` : Menu Organisation (Créer, Rejoindre, Info)",
            f"`{prefix}org set <desc/badge/color> <valeur>` : Personnaliser son Orga",
            f"`{prefix}payall <montant>` : Arroser tout le vocal ($$)",
            f"`{prefix}simulate immo` : Calculer vos revenus immo futurs",
            f"`{prefix}interest` : Intérêts d'immeubles (pallier max requis)"
        ]
        embed.add_field(name="🏆 Social & Organisation", value="\n".join(social_cmds), inline=False)
        
        # --- ℹ️ Divers ---
        misc_cmds = [
            f"`{prefix}maj` : Voir le changelog (Quoi de neuf ?)",
            f"`{prefix}cd` : Voir vos temps d'attente (Cooldowns)"
        ]
        embed.add_field(name="ℹ️ Divers", value="\n".join(misc_cmds), inline=False)

        # --- 🛡️ Admin / Police ---
        if ctx.author.guild_permissions.administrator:
            admin_cmds = [
                f"`{prefix}add_money <@joueur> <montant>` : Give d'argent",
                f"`{prefix}remove_money <@joueur> <montant>` : Retrait d'argent",
                f"`{prefix}reset_user <@joueur>` : Reset complet d'un joueur",
                f"`{prefix}tax <@joueur> <montant>` : Taxer (va dans la poche admin)",
                f"`{prefix}taxrich <taux%>` : Taxer les riches (5% par défaut)",
                f"`{prefix}awardbadge <@joueur> <badge>` : Donner un badge",
                f"`{prefix}payall <montant>` : Arroser le vocal",
                f"`{prefix}admin_fix_badge` : Fix taille colonne badge",
                f"`{prefix}toggle_logs <on/off>` : Activer/Désactiver logs"
            ]
            embed.add_field(name="🛡️ Admin / Police", value="\n".join(admin_cmds), inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="maj")
    async def maj(self, ctx: commands.Context):
        embed = discord.Embed(title="📜 Note de Mise à Jour", color=discord.Color.gold())
        embed.description = "**Patch Note : Images Fun & Courses Hippiques 🐎**"
        
        changes = [
            "📸 **Images Fun** :",
            "• `+parions` : Crée ton ticket Parions Street avec logo FDJ.",
            "• `+perdu <@user>` : Affiche de recherche 'Perdu de vue'.",
            "• `+idcard <@user>` : Carte d'identité du quartier.",
            "• `+diplome <@user>` : Diplôme de la rue selon ta richesse.",
            "",
            "🐎 **Courses de Chevaux (PMU)** :",
            "• Admin lance : `+course start` puis `+course run`.",
            "• Joueurs parient : `+bet [num] [mise]`.",
            "• Course en direct avec animation !",
            "",
            "⚙️ **Améliorations** :",
            "• `+add_money` accepte '1m', '100k' etc.",
            "• `+facture` change de couleur quand payée/refusée.",
            "• Carte bancaire : Texte auto-adaptatif (noir sur blanc) & Patterns corrigés.",
            "• `+interest` corrigé.",
            "• Taxe riche abaissée à 3M."
        ]
        
        embed.add_field(name="Changelog", value="\n".join(changes), inline=False)
        embed.set_footer(text="Bot développé par Fazer")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
