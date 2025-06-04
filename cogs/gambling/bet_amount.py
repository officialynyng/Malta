import discord
from discord import Interaction
from cogs.gambling.play_button import GamblingPlayButton  # Relative import

class BetAmountDropdown(discord.ui.Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        self.user_id = parent_view.user_id  # Needed for restart-safe validation

        predefined_bets = [1, 5, 10, 25, 50, 100, 200, 250, 300, 500, 750, 1000, 2000, 2500, 3500, 5000]

        options = [
            discord.SelectOption(label=str(x), value=str(x))
            for x in predefined_bets
            if parent_view.min_bet <= x <= parent_view.max_bet
        ]

        if not options and parent_view.min_bet == parent_view.max_bet:
            options = [
                discord.SelectOption(label=str(parent_view.min_bet), value=str(parent_view.min_bet))
            ]

        super().__init__(
            placeholder="💰 Choose your bet amount",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"bet_amount_dropdown:{self.user_id}"  # 👈 Embed user ID for restart-safe
        )

    async def callback(self, interaction: Interaction):
        # ✅ Re-check ownership from custom_id
        actual_user_id = int(self.custom_id.split(":")[1])
        if interaction.user.id != actual_user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        # ✅ Set the bet amount
        self.parent_view.amount = int(self.values[0])
        self.parent_view.play_button.amount = self.parent_view.amount

        # ✅ Update main view
        await interaction.response.edit_message(view=self.parent_view)

        # ✅ Ephemeral confirmation
        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ Bet Selected",
                description=f"You chose to bet **{self.parent_view.amount:,}** gold.",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
