import asyncio
from discord.ext import commands

from cogs.chat_modulations.modules.malta_time.public_time_announcement import malta_public_day_loop

class MaltaTimeScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop_task = bot.loop.create_task(self.start_loops())

    async def start_loops(self):
        await self.bot.wait_until_ready()
        await malta_public_day_loop(self.bot)

async def setup(bot):
    await bot.add_cog(MaltaTimeScheduler(bot))