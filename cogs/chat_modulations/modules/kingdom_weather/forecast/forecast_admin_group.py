import discord
from discord.ext import commands
from discord import app_commands, Interaction

from cogs.chat_modulations.modules.kingdom_weather.forecast_scheduler import post_daily_forecast, post_weekly_forecast
from cogs.chat_modulations.modules.kingdom_weather.weather_generator import generate_weather_for_region
from cogs.chat_modulations.modules.kingdom_weather.utils.region_picker import get_random_region
from cogs.chat_modulations.modules.kingdom_weather.forecast.forecast_embed import build_forecast_embed  # ✅ uses your final embed
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime


class ForecastAdminGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    forecast_group = app_commands.Group(
        name="forecast",
        description="🔒🌄 Forecast posting and previewing tools for weather system"
    )

    @forecast_group.command(name="post_daily", description="📍🌄🪨 Force post a daily forecast for 1 region.")
    @app_commands.checks.has_permissions(administrator=True)
    async def post_daily(self, interaction: Interaction):
        await post_daily_forecast(interaction.client)
        await interaction.response.send_message("✅ Daily forecast posted to EXP channel.", ephemeral=True)

    @forecast_group.command(name="post_weekly", description="📍🌄🪨💣 Force post a full weekly forecast (all 5 regions).")
    @app_commands.checks.has_permissions(administrator=True)
    async def post_weekly(self, interaction: Interaction):
        await post_weekly_forecast(interaction.client)
        await interaction.response.send_message("✅ Weekly forecast posted to EXP channel.", ephemeral=True)

    @forecast_group.command(name="preview_random", description="🔍 Preview forecast for a random region (ephemeral)")
    @app_commands.checks.has_permissions(administrator=True)
    async def preview_random(self, interaction: Interaction):
        region = get_random_region()
        malta_dt = get_malta_datetime()
        forecast = generate_weather_for_region(region)
        embed = build_forecast_embed(region, forecast, malta_dt)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @forecast_group.command(name="preview_region", description="🔍 Preview forecast for a specific region (ephemeral)")
    @app_commands.describe(region="Enter region name like 'Citadel of Valletta'")
    @app_commands.checks.has_permissions(administrator=True)
    async def preview_region(self, interaction: Interaction, region: str):
        malta_dt = get_malta_datetime()
        forecast = generate_weather_for_region(region)
        embed = build_forecast_embed(region, forecast, malta_dt)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ForecastAdminGroup(bot))
