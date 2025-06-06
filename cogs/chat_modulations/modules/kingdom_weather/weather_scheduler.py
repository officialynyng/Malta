import time
import asyncio
from discord.ext import commands, tasks

from cogs.database.session import get_session
from cogs.chat_modulations.modules.kingdom_weather.weather_controller import post_weather

COOLDOWN_SECONDS = 600  # 10 minutes buffer to prevent double post on restart

class WeatherScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weather_loop.start()

    @tasks.loop(hours=3)
    async def weather_loop(self):
        now = time.time()

        await post_weather(self.bot)  # ✅ Must log loop_last_run inside this

    @weather_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(180)  # ⏳ Extra delay to avoid race condition on restart

async def setup(bot):
    await bot.add_cog(WeatherScheduler(bot))
