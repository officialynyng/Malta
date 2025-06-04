import discord
from discord import Interaction
from cogs.gambling.play_button import GamblingPlayButton  # Relative import

class BetAmountDropdown(discord.ui.Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view

        # Hardcoded list of allowed bet options
        predefined_bets = [1, 5, 10, 25, 50, 100, 200, 250, 300, 500, 750, 1000, 2000, 2500, 3500, 5000]

        options = [
            discord.SelectOption(label=str(x), value=str(x))
            for x in predefined_bets
            if parent_view.min_bet <= x <= parent_view.max_bet
        ]

        # ✅ Add fallback if no options match
        if not options and parent_view.min_bet == parent_view.max_bet:
            options = [
                discord.SelectOption(label=str(parent_view.min_bet), value=str(parent_view.min_bet))
            ]

        super().__init__(placeholder="💰 Choose your bet amount", min_values=1, max_values=1, options=options, custom_id="blackjack_bet_dropdown")


    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.parent_view.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        self.parent_view.amount = int(self.values[0])
        self.parent_view.play_button.amount = self.parent_view.amount

        # 👇 Update the main view
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

