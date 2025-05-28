import discord
from discord.ext import tasks, commands
import datetime
import asyncio
from cogs.exp_config import EXP_CHANNEL_ID  # Make sure this points to your EXP channel

class EXPReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.exp_reminder.start()

    def cog_unload(self):
        self.exp_reminder.cancel()

    @tasks.loop(hours=4)  # Change to desired interval
    async def exp_reminder(self):
        channel = self.bot.get_channel(EXP_CHANNEL_ID)
        if not channel:
            return

        embed = discord.Embed(
            title="⚔️ Continue your legacy.",
            description="**Use** `/crpg retire` to continue your legacy, and earn additional  (🧬) generational multipliers. (Up to 1.48) \n**Use** `/help` for more commands.",
            color=discord.Color.red()()
        )
        embed.set_thumbnail(url="http://theknightsofmalta.net/wp-content/uploads/2025/05/retire.png")
        embed.set_footer(text="Retirement unlocks heirloom points starting at level 31.")

        await channel.send(content="## *The steward bows low and gestures toward the retirement ledger...*", embed=embed)

    @exp_reminder.before_loop
    async def before_exp_reminder(self):
        await self.bot.wait_until_ready()

        now = datetime.datetime.utcnow()
        next_hour = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)


async def setup(bot):
    await bot.add_cog(EXPReminder(bot))
