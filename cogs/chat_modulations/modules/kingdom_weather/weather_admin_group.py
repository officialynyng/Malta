import time
import discord
from sqlalchemy import select
from discord import app_commands, Interaction
from discord.ext import commands

from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import readable_duration
from cogs.database.kingdomweather.weather_ts import weather_ts_table
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import ALL_REGIONS, readable_duration
from cogs.database.session import get_session
from cogs.chat_modulations.modules.kingdom_weather.weather_controller import post_weather

WEATHER_COOLDOWN = 1800  # same cooldown as weather_controller

class WeatherAdminGroup(commands.GroupCog, name="weather"):

    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="test", description="🌧️ - Post test weather for a random region.")
    @app_commands.checks.has_permissions(administrator=True)
    async def weather_test(self, interaction: Interaction):
        embed = await post_weather(interaction.client, triggered_by="admin")
        if embed:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Failed to generate weather.", ephemeral=True)

    @app_commands.command(name="next", description="🕰️ - See when the next weather post is allowed.")
    @app_commands.checks.has_permissions(administrator=True)
    async def weather_next(self, interaction: Interaction):
        now = time.time()
        lines = []

        with get_session() as session:
            # Per-region cooldowns
            for region in ALL_REGIONS:
                stmt = select(weather_ts_table.c.value).where(weather_ts_table.c.key == region)
                last_posted = session.execute(stmt).scalar()
                if not last_posted:
                    lines.append(f"✅ **{region}** is ready now.")
                else:
                    time_left = (last_posted + WEATHER_COOLDOWN) - now
                    if time_left <= 0:
                        lines.append(f"✅ **{region}** is ready now.")
                    else:
                        lines.append(f"⏳ **{region}**: ready in {readable_duration(time_left)}")

            # Task loop (3-hour) time
            loop_stmt = select(weather_ts_table.c.value).where(weather_ts_table.c.key == "loop_last_run")
            loop_last = session.execute(loop_stmt).scalar()
            if loop_last:
                next_loop_ts = loop_last + 3 * 3600
                loop_info = f"🌀 Next system check in {readable_duration(next_loop_ts - now)}"
            else:
                loop_info = "🌀 **Next system check**: unknown (loop has not run yet)"

        embed = discord.Embed(
            title="📅 Next Weather Post Times",
            description="\n".join(lines),
            color=discord.Color.from_rgb(0, 32, 96)
        )
        embed.set_footer(text=loop_info)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(WeatherAdminGroup(bot))