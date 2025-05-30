#just here while we wait.
import discord
from discord.ext import tasks, commands
import datetime
import pytz
import random
from cogs.exp_config import EXP_CHANNEL_ID

CENTRAL_TZ = pytz.timezone("America/Chicago")
REMINDER_HOURS = {12, 15, 18}  # 12 PM, 3 PM, 6 PM CST

REMINDER_VARIANTS = [
    {
        "line": "",
        "img": "http://theknightsofmalta.net/wp-content/uploads/2025/05/Gold-Casino.png"
    },
    {
        "line": "",
        "img": "http://theknightsofmalta.net/wp-content/uploads/2025/05/Casino-1.png"
    },
    {
        "line": "",
        "img": "http://theknightsofmalta.net/wp-content/uploads/2025/05/Casino-4.png"
    },
]

class GambleReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gamble_reminder.start()

    def cog_unload(self):
        self.gamble_reminder.cancel()

    @tasks.loop(minutes=1)
    async def gamble_reminder(self):
        now = datetime.datetime.now(CENTRAL_TZ)
        if now.hour in REMINDER_HOURS and now.minute == 0:
            channel = self.bot.get_channel(EXP_CHANNEL_ID)
            if not channel:
                return

            variant = random.choice(REMINDER_VARIANTS)
            embed = discord.Embed(
                title="♠️ ♥️ ♦️ ♣️  Feeling lucky?",
                description="**Use** `/gamble play` to play an assortment of games.\nTake a risk — and maybe take the pot.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=variant["img"])
            embed.set_footer(text="Games are available all day - don't miss your chance!")

            await channel.send(content=variant["line"], embed=embed)

    @gamble_reminder.before_loop
    async def before_gamble_reminder(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(GambleReminder(bot))