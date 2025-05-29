import discord
from discord import Interaction
from cogs.gambling.play_button import GamblingPlayButton  # Relative import

class BetAmountDropdown(discord.ui.Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=str(x), value=str(x)) for x in [1, 5, 10, 25, 50, 100, 200, 250, 300, 500, 750, 1000, 2000, 2500, 3500, 5000]
            if parent_view.min_bet <= x <= parent_view.max_bet
        ]
        super().__init__(placeholder="💰 Choose your bet amount", options=options)

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.parent_view.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        self.parent_view.amount = int(self.values[0])
        self.parent_view.play_button.amount = self.parent_view.amount # ← THIS is key
        await interaction.response.send_message(
            f"✅ Bet amount set to **{self.values[0]} gold**. Press play when ready!",
            ephemeral=True
        )


