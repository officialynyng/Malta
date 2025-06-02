from cogs.gambling.lottery.lottery_halloffame_UI import HallOfFameView

import discord
from discord.ui import View, Button
from discord import ButtonStyle

class LotteryMainView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # persistent
        self.cog = cog

    @discord.ui.button(label="🎟️ Stats", style=discord.ButtonStyle.primary, custom_id="lottery_stats")
    async def stats(self, interaction: discord.Interaction, button: Button):
        embed = await self.cog.build_stats_embed(interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏆 Leaderboard", style=discord.ButtonStyle.secondary, custom_id="lottery_leaderboard")
    async def leaderboard(self, interaction: discord.Interaction, button: Button):
        embed = await self.cog.build_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="📜 History", style=discord.ButtonStyle.secondary, custom_id="lottery_history")
    async def history(self, interaction: discord.Interaction, button: Button):
        embed = await self.cog.build_history_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🕰️ Next Draw", style=discord.ButtonStyle.secondary, custom_id="lottery_nextdraw")
    async def nextdraw(self, interaction: discord.Interaction, button: Button):
        embed = await self.cog.build_nextdraw_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏅 Hall of Fame", style=discord.ButtonStyle.success, custom_id="lottery_halloffame")
    async def halloffame(self, interaction: discord.Interaction, button: Button):
        embed = await self.cog.build_halloffame_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❓ Help", style=discord.ButtonStyle.secondary, custom_id="lottery_help")
    async def help(self, interaction: discord.Interaction, button: Button):
        embed = await self.cog.build_help_embed()
        await interaction.response.edit_message(embed=embed, view=self)

