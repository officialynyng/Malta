from cogs.gambling.lottery.lottery_halloffame_UI import HallOfFameView
from discord.ui import View, button
from discord import ButtonStyle

class LotteryMainView(View):
    def __init__(self, cog, interaction):
        super().__init__(timeout=60)
        self.cog = cog
        self.interaction = interaction  # store interaction for timeout edits

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except:
            pass

    @button(label="🎟️ Stats", style=ButtonStyle.primary)
    async def stats(self, interaction, _):
        embed = await self.cog.build_stats_embed(interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @button(label="🏆 Leaderboard", style=ButtonStyle.secondary)
    async def leaderboard(self, interaction, _):
        embed = await self.cog.build_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @button(label="📜 History", style=ButtonStyle.secondary)
    async def history(self, interaction, _):
        embed = await self.cog.build_history_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @button(label="⏱️ Next Draw", style=ButtonStyle.secondary)
    async def nextdraw(self, interaction, _):
        embed = await self.cog.build_nextdraw_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @button(label="👑 Hall of Fame", style=ButtonStyle.success)
    async def halloffame(self, interaction, _):
        view = HallOfFameView(self.cog, interaction)
        embed = await self.cog.build_halloffame_embed("all")
        await interaction.response.edit_message(embed=embed, view=view)

    @button(label="ℹ️ Help", style=ButtonStyle.secondary)
    async def help(self, interaction, _):
        embed = await self.cog.build_help_embed()
        await interaction.response.edit_message(embed=embed, view=self)
