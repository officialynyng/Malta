from cogs.gambling.lottery.lottery_halloffame_UI import HallOfFameView
from discord.ui import View, button, Button
from discord import ButtonStyle, Interaction

class LotteryMainView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # 🟢 no timeout = persistent
        self.cog = cog

        # Manually add all buttons since decorators don't persist
        self.add_item(Button(label="🎟️ Stats", style=ButtonStyle.primary, custom_id="lottery_stats"))
        self.add_item(Button(label="🏆 Leaderboard", style=ButtonStyle.secondary, custom_id="lottery_leaderboard"))
        self.add_item(Button(label="📜 History", style=ButtonStyle.secondary, custom_id="lottery_history"))
        self.add_item(Button(label="⏱️ Next Draw", style=ButtonStyle.secondary, custom_id="lottery_nextdraw"))
        self.add_item(Button(label="👑 Hall of Fame", style=ButtonStyle.success, custom_id="lottery_halloffame"))
        self.add_item(Button(label="ℹ️ Help", style=ButtonStyle.secondary, custom_id="lottery_help"))

    @View.button_callback(custom_id="lottery_stats")
    async def stats(self, interaction: Interaction):
        embed = await self.cog.build_stats_embed(interaction.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @View.button_callback(custom_id="lottery_leaderboard")
    async def leaderboard(self, interaction: Interaction):
        embed = await self.cog.build_leaderboard_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @View.button_callback(custom_id="lottery_history")
    async def history(self, interaction: Interaction):
        embed = await self.cog.build_history_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @View.button_callback(custom_id="lottery_nextdraw")
    async def nextdraw(self, interaction: Interaction):
        embed = await self.cog.build_nextdraw_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @View.button_callback(custom_id="lottery_halloffame")
    async def halloffame(self, interaction: Interaction):
        view = HallOfFameView(self.cog, interaction)
        embed = await self.cog.build_halloffame_embed("all")
        await interaction.response.edit_message(embed=embed, view=view)

    @View.button_callback(custom_id="lottery_help")
    async def help(self, interaction: Interaction):
        embed = await self.cog.build_help_embed()
        await interaction.response.edit_message(embed=embed, view=self)
