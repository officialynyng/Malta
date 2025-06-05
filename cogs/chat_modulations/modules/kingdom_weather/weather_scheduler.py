import time
from discord.ext import commands, tasks
from sqlalchemy.dialects.postgresql import insert as pg_insert

from cogs.database.weather_ts import weather_ts_table
from cogs.database.session import get_session
from cogs.chat_modulations.modules.kingdom_weather.weather_controller import post_weather

class WeatherScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weather_loop.start()

    @tasks.loop(hours=6)
    async def weather_loop(self):
        await post_weather(self.bot)
        update_last_loop_time()

    @weather_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(WeatherScheduler(bot))

def update_last_loop_time():
    now = time.time()
    with get_session() as session:
        stmt = pg_insert(weather_ts_table).values(
            key="loop_last_run",
            value=now
        ).on_conflict_do_update(
            index_elements=["key"],
            set_={"value": now}
        )
        session.execute(stmt)
        session.commit()