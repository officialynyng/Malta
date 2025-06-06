import discord
from discord.ext import commands
from discord import app_commands, Interaction

from cogs.exp_config import ADMIN_ROLE_ID
from cogs.chat_modulations.modules.kingdom_weather.forecast_scheduler import post_daily_forecast, post_weekly_forecast

class ForecastAdminGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    forecast_group = app_commands.Group(
        name="forecast",
        description="🔒🧭 Controls for testing the forecast system"
    )

    @forecast_group.command(name="now", description="📍 Post a forecast for a random region.")
    async def forecast_now(self, interaction: Interaction):
        if not interaction.user.get_role(ADMIN_ROLE_ID):
            await interaction.response.send_message("❌ You do not have access to this.", ephemeral=True)
            return
        await post_daily_forecast(interaction.client)
        await interaction.response.send_message("✅ Daily forecast posted.", ephemeral=True)

    @forecast_group.command(name="weekly", description="📍 Post a forecast for all 5 regions.")
    async def forecast_weekly(self, interaction: Interaction):
        if not interaction.user.get_role(ADMIN_ROLE_ID):
            await interaction.response.send_message("❌ You do not have access to this.", ephemeral=True)
            return
        await post_weekly_forecast(interaction.client)
        await interaction.response.send_message("✅ Weekly forecast posted.", ephemeral=True)
    
    @forecast_group.command(name="now", description="📍 View a test forecast for a random region.")
    async def forecast_now(self, interaction: Interaction):
        if not interaction.user.get_role(ADMIN_ROLE_ID):
            await interaction.response.send_message("❌ You do not have access to this.", ephemeral=True)
            return
        await interaction.response.send_message("⚙️ Forecast testing placeholder.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ForecastAdminGroup(bot))