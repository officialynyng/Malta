import json
import discord
from discord import app_commands, Interaction, Embed
from discord.app_commands import Group
from discord.ext import commands
from sqlalchemy import select
from cogs.exp_config import engine
from cogs.database.gambling_stats_table import gambling_stats
from cogs.exp_utils import get_user_data
from cogs.gambling.UI_MainMenu import GamblingMenuView


gamble_group = Group(name="gamble", description="🎰 Enter the gambling hall and play games!")
DEBUG = True

@gamble_group.command(name="menu", description="♠️ ♥️ ♦️ ♣️ Open the gambling hall menu!")
async def gamble_menu(interaction: Interaction):
    # Admin check
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
        return

    user_data = get_user_data(interaction.user.id)
    if not user_data:
        await interaction.response.send_message("❌ Could not fetch user data.", ephemeral=True)
        return

    view = GamblingMenuView(interaction.client.get_cog("GamblingGroup"))
    embed = Embed(
        title="🎰 Welcome to the Gambling Hall",
        description="Pick your game or view stats!",
        color=discord.Color.green()
    )
    embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/Gold-Casino.png")
    embed.set_footer(text=f"💰 Gold: {user_data['gold']}")
    await interaction.response.send_message("🎰 Posting the Gambling Hall menu...", ephemeral=True)
    channel = interaction.channel
    await channel.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    from cogs.gambling.gambling_ui import GameSelectionView
    from cogs.gambling.UI_MainMenu import GamblingMenuView
    from cogs.gambling.roulette.roulette import RouletteOptionView
    from cogs.gambling.blackjack.blackjack import BlackjackGameView
    
    from discord.ui import View
    from cogs.gambling.gambling_ui_common import PlayAgainButton


    bot.tree.add_command(gamble_group)

    dummy_user_id = 123456789012345678  # Safe static test ID
    dummy_gold = 1000
    cog = bot.get_cog("GamblingGroup")  # ✅ reuse for all views

    # ✅ Register persistent views
    bot.add_view(GamblingMenuView(cog=cog))
    bot.add_view(GameSelectionView(dummy_user_id, dummy_gold, cog=cog))
    bot.add_view(RouletteOptionView(dummy_user_id, dummy_gold, parent=None, cog=cog))
    bot.add_view(BlackjackGameView(dummy_user_id, dummy_gold, parent=None, bet=100, cog=cog))
    # ✅ Create a persistent View that holds the PlayAgain button
    play_again_view = View(timeout=None)
    play_again_view.add_item(PlayAgainButton(game_key="blackjack"))
    bot.add_view(play_again_view)

    print("[DEBUG] Persistent PlayAgainButton view registered ✅")