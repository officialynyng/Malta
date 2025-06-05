import time
from discord.ext import commands, tasks
from cogs.chat_modulations.modules.kingdom_weather.weather_controller import post_weather

class WeatherScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weather_loop.start()

    @tasks.loop(hours=6)
    async def weather_loop(self):
        await post_weather(self.bot)

    @weather_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(WeatherScheduler(bot))
