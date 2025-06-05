import time
from discord.ext import commands, tasks
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from cogs.database.weather_ts import weather_ts_table
from cogs.database.session import get_session
from cogs.chat_modulations.modules.kingdom_weather.weather_controller import post_weather

COOLDOWN_SECONDS = 600  # 10 minutes buffer to prevent double post on restart

class WeatherScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weather_loop.start()

    @tasks.loop(hours=6)
    async def weather_loop(self):
        now = time.time()

        with get_session() as session:
            stmt = select(weather_ts_table.c.value).where(weather_ts_table.c.key == "loop_last_run")
            last_loop = session.execute(stmt).scalar() or 0.0

            if now - last_loop < COOLDOWN_SECONDS:
                print("[⏳] Skipping weather post – loop recently ran.")
                return

        await post_weather(self.bot)  # ✅ This function already logs loop_last_run

    @weather_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(WeatherScheduler(bot))
