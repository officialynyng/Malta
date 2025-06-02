import discord
from discord.ui import View, Button
from discord import Interaction, ButtonStyle, Embed

from cogs.exp_utils import get_user_data
from cogs.gambling.gambling_ui import GameSelectionView

class GamblingMenuView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent!
        self.cog = cog

    @discord.ui.button(label="🎲 Games", style=ButtonStyle.primary, custom_id="gamble_games")
    async def games(self, interaction: Interaction, button: Button):
        user_id = interaction.user.id
        user_data = get_user_data(user_id)
        user_gold = user_data["gold"] if user_data else 0

        view = GameSelectionView(user_id, user_gold, self.cog)
        embed = Embed(
            title="🎲 Choose a Game",
            description="Pick which game you'd like to play.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)


    @discord.ui.button(label="📊 Stats", style=ButtonStyle.secondary, custom_id="gamble_stats")
    async def stats(self, interaction: Interaction, button: Button):
        embed = await self.cog.build_gambling_stats_embed(interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏆 Leaderboard", style=ButtonStyle.secondary, custom_id="gamble_leaderboard")
    async def leaderboard(self, interaction: Interaction, button: Button):
        embed = await self.cog.build_gambling_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="📜 History", style=ButtonStyle.secondary, custom_id="gamble_history")
    async def history(self, interaction: Interaction, button: Button):
        embed = await self.cog.build_gambling_history_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❓ Help", style=ButtonStyle.secondary, custom_id="gamble_help")
    async def help(self, interaction: Interaction, button: Button):
        embed = await self.cog.build_gambling_help_embed()
        await interaction.response.edit_message(embed=embed, view=self)

# If you want, you can add a "Home" button or back-to-menu logic in your subviews
