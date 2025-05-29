import json
import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from sqlalchemy import select
from cogs.exp_config import engine
from cogs.database.gambling_stats_table import gambling_stats
from cogs.exp_utils import get_user_data
from cogs.gambling.gambling_ui import GameSelectionView

DEBUG = True

class GamblingGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gamble", description="♠️ ♥️ ♦️ ♣️ Open the gambling hall and choose your game!")
    async def gamble(self, interaction: Interaction):
        user_data = get_user_data(interaction.user.id)
        if not user_data:
            await interaction.response.send_message("❌ Could not fetch user data.", ephemeral=True)
            return

        view = GameSelectionView(interaction.user.id, user_data["gold"])
        embed = Embed(
            title="🎰 Welcome to the Gambling Hall",
            description="Pick your game to begin.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"🎲 Gold: {user_data['gold']}")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    @app_commands.command(name="gamble_stats", description="🎰 - 📊 View your gambling history and performance")
    async def gamble_stats(self, interaction: Interaction):
        user_id = interaction.user.id
        with engine.begin() as conn:
            result = conn.execute(select(gambling_stats).where(gambling_stats.c.user_id == user_id)).fetchone()

        if not result:
            await interaction.response.send_message("❌ No gambling data found.", ephemeral=True)
            return

        embed = Embed(
            title=f"🎰 Gambling Stats for {interaction.user.display_name}",
            color=discord.Color.red()
        )
        embed.add_field(name="Total Bets", value=result.total_bets, inline=True)
        embed.add_field(name="Total Won", value=result.total_won, inline=True)
        embed.add_field(name="Total Lost", value=result.total_lost, inline=True)
        embed.add_field(name="Net Winnings", value=result.net_winnings, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(GamblingGroup(bot))
