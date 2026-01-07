import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta

class Interest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cog = bot.get_cog('Economy')
        if not self.cog:
            print("⚠️  Interest cog: Economy cog not found. Interest system disabled.")
            return
        
        # Start the interest task
        self.interest_task.start()

    def cog_unload(self):
        self.interest_task.cancel()

    @tasks.loop(hours=24)
    async def interest_task(self):
        """Automatically award interest to eligible users every 24h"""
        if not self.cog or not hasattr(self.cog, 'pool'):
            return
            
        try:
            await self.cog._connect()
            async with self.cog.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Get all users with max bank tier (5) and properties
                    await cur.execute("""
                        SELECT u.user_id, SUM(p.income) as total_income, COUNT(p.property_type) as property_count
                        FROM users u
                        LEFT JOIN user_properties p ON u.user_id = p.user_id
                        WHERE u.bank_tier = 5 AND p.quantity > 0
                        GROUP BY u.user_id
                        HAVING total_income > 0
                    """)
                    
                    eligible_users = await cur.fetchall()
                    
                    for user_id, total_income, property_count in eligible_users:
                        # Calculate interest (10% of total income)
                        interest_amount = int(total_income * 0.1)
                        
                        # Award interest
                        await cur.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (interest_amount, user_id))
                        
                        # Try to send notification to user
                        try:
                            user = await self.bot.fetch_user(user_id)
                            if user:
                                embed = discord.Embed(
                                    title="💰 Intérêts d'Immeubles Collectés !",
                                    description=f"Vous avez reçu **{self.cog._fmt_amount(interest_amount)}** d'intérêts sur vos immeubles !",
                                    color=discord.Color.gold(),
                                    timestamp=datetime.now()
                                )
                                embed.add_field(name="Immeubles possédés", value=f"{property_count}", inline=True)
                                embed.add_field(name="Revenus totaux", value=f"{self.cog._fmt_amount(total_income)}/h", inline=True)
                                embed.add_field(name="Taux d'intérêt", value="10%", inline=True)
                                embed.set_footer(text="Les intérêts sont versés automatiquement tous les jours")
                                
                                await user.send(embed=embed)
                        except:
                            pass  # User might have DMs disabled
                            
        except Exception as e:
            print(f"Error in interest task: {e}")

    @interest_task.before_loop
    async def before_interest_task(self):
        """Wait until the bot is ready and then wait for next midnight"""
        await self.bot.wait_until_ready()
        
        # Wait until next midnight
        now = datetime.now()
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_time = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait_time)

    # Manual interest command removed - use the one in economy cog instead

async def setup(bot):
    await bot.add_cog(Interest(bot))