from discord import app_commands, Interaction
from discord.ext import commands
from cogs.chat_modulations.modules.kingdom_weather.weather_controller import post_weather

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

async def setup(bot):
    await bot.add_cog(WeatherAdminGroup(bot))