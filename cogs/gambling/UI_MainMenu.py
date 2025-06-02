import discord
from discord.ui import View, Button
from discord import Interaction, ButtonStyle, Embed

class GamblingMenuView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent!
        self.cog = cog

    @discord.ui.button(label="♠️ Blackjack", style=ButtonStyle.primary, custom_id="gamble_blackjack")
    async def blackjack(self, interaction: Interaction, button: Button):
        # Launch the Blackjack subview/modal here
        await self.cog.open_blackjack(interaction)

    @discord.ui.button(label="🎡 Roulette", style=ButtonStyle.primary, custom_id="gamble_roulette")
    async def roulette(self, interaction: Interaction, button: Button):
        await self.cog.open_roulette(interaction)

    @discord.ui.button(label="🪙 Coinflip", style=ButtonStyle.primary, custom_id="gamble_coinflip")
    async def coinflip(self, interaction: Interaction, button: Button):
        await self.cog.open_coinflip(interaction)

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

