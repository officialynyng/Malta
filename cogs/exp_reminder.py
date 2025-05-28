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
            title="⚔️ Hit level 31 or higher?",
            description="**Use** `/crpg retire` to continue your legacy, and earn additional  (🧬) generational multipliers. (Up to 1.48) \n**Use** `/help` for more commands.",
            color=discord.Color.red()
        )
        embed.set_image(url="http://theknightsofmalta.net/wp-content/uploads/2025/05/officialretire.png")
        embed.set_footer(text="Retirement unlocks heirloom points starting at level 31.")

        await channel.send(content="", embed=embed)


async def setup(bot):
    await bot.add_cog(EXPReminder(bot))
