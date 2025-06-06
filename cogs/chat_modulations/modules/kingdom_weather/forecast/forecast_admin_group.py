import discord
from discord.ext import commands
from discord import app_commands, Interaction

from cogs.database.session import get_session
from cogs.chat_modulations.modules.kingdom_weather.forecast.forecast_scheduler import post_daily_forecast, post_weekly_forecast
from cogs.chat_modulations.modules.kingdom_weather.forecast.forecast_utils import generate_forecast_for_region
from cogs.chat_modulations.modules.kingdom_weather.forecast.region_picker import get_random_region
from cogs.chat_modulations.modules.kingdom_weather.forecast.forecast_embed import build_forecast_embed  # ✅ uses your final embed
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime


class ForecastAdminGroup(commands.GroupCog, name="forecast"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="post_daily", description="📍🌄🪨 Force post a daily forecast for 1 region.")
    @app_commands.checks.has_permissions(administrator=True)
    async def post_daily(self, interaction: Interaction):
        await post_daily_forecast(interaction.client)
        await interaction.response.send_message("✅ Daily forecast posted to EXP channel.", ephemeral=True)

    @app_commands.command(name="post_weekly", description="📍🌄🪨💣 Force post a full weekly forecast (all 5 regions).")
    @app_commands.checks.has_permissions(administrator=True)
    async def post_weekly(self, interaction: Interaction):
        await post_weekly_forecast(interaction.client)
        await interaction.response.send_message("✅ Weekly forecast posted to EXP channel.", ephemeral=True)

    @app_commands.command(name="preview_random", description="🔍 Preview forecast for a random region (ephemeral)")
    @app_commands.checks.has_permissions(administrator=True)
    async def preview_random(self, interaction: Interaction):
        region = get_random_region()
        malta_dt = get_malta_datetime()
        with get_session() as session:
            forecast = generate_forecast_for_region(session, region)
        embed = build_forecast_embed(region, forecast, malta_dt)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="preview_region", description="🔍 Preview forecast for a specific region (ephemeral)")
    @app_commands.describe(region="Enter region name like 'Citadel of Valletta'")
    @app_commands.checks.has_permissions(administrator=True)
    async def preview_region(self, interaction: Interaction, region: str):
        malta_dt = get_malta_datetime()
        with get_session() as session:
            forecast = generate_forecast_for_region(session, region)
        embed = build_forecast_embed(region, forecast, malta_dt)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ForecastAdminGroup(bot))
