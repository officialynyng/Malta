#just here while we wait.
import discord
from discord.ext import tasks, commands
import datetime
import asyncio
import pytz
import random
from cogs.exp_config import EXP_CHANNEL_ID

CENTRAL_TZ = pytz.timezone("America/Chicago")
REMINDER_DAYS = {1, 3, 6}  # Tuesday, Thursday, Sunday
REMINDER_HOUR = 15  # 3 PM CST

REMINDER_VARIANTS = [
    {
        "line": "## *The gambling den hums with energy. A table opens up just for you...* 🎲",
        "img": "https://theknightsofmalta.net/wp-content/uploads/2025/05/malta_gambling_den_1.png"
    },
    {
        "line": "## *A hushed crowd watches as gold coins clink across the table...* 🪙",
        "img": "https://theknightsofmalta.net/wp-content/uploads/2025/05/malta_gambling_den_2.png"
    },
    {
        "line": "## *A shady figure beckons you into the backroom with a crooked smile...* ♣️♦️",
        "img": "https://theknightsofmalta.net/wp-content/uploads/2025/05/malta_gambling_den_3.png"
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
        if now.weekday() in REMINDER_DAYS and now.hour == REMINDER_HOUR and now.minute == 0:
            channel = self.bot.get_channel(EXP_CHANNEL_ID)
            if not channel:
                return

            variant = random.choice(REMINDER_VARIANTS)
            embed = discord.Embed(
                title="🎰 Feeling lucky?",
                description="**Use** `/gamble` to play Blackjack, Coin Flip, or Roulette.\nTake a risk — and maybe take the pot.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=variant["img"])
            embed.set_footer(text="Games are available all day — don't miss your shot!")

            await channel.send(content=variant["line"], embed=embed)

    @gamble_reminder.before_loop
    async def before_gamble_reminder(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(GambleReminder(bot))