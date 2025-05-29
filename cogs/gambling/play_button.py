from cogs.gambling.gambling_logic import handle_gamble_result
from cogs.exp_utils import get_user_data

import discord
from discord import Interaction

class GamblingPlayButton(discord.ui.Button):
    def __init__(self, user_id, game_key, get_amount_callback, parent=None, extra_callback=None):
        super().__init__(label="Play", emoji="🎰", style=discord.ButtonStyle.red)
        self.user_id = user_id
        self.game_key = game_key
        self.get_amount = get_amount_callback
        self.parent = parent
        self.extra_callback = extra_callback

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()

        if interaction.user.id != self.user_id:
            return await interaction.followup.send("❌ Not your session!", ephemeral=True)

        amount = self.get_amount()
        if amount <= 0:
            return await interaction.followup.send("❌ Invalid bet amount.", ephemeral=True)

        user_data = get_user_data(self.user_id)

        # Special handling for blackjack
        if self.game_key == "blackjack":
            from cogs.gambling.blackjack.blackjack import BlackjackGameView
            await interaction.edit_original_response(
                content=f"🃏 You bet **{amount}** gold on Blackjack!",
                embed=None,
                view=BlackjackGameView(
                    self.user_id,
                    user_data['gold'],
                    parent=self.parent,
                    bet=amount
                )
            )
            return

        # Special callback from parent (e.g. roulette, slots, etc.)
        if self.extra_callback:
            result = self.extra_callback
            try:
                # Check if it's a coroutine that takes (interaction, amount)
                await result(interaction, amount)
            except TypeError:
                # Otherwise assume it just returns a View (e.g. from lambda)
                view = result(amount)
                await interaction.edit_original_response(
                    content=f"🎲 You bet **{amount}** gold on {self.game_key.title()}!",
                    embed=None,
                    view=view
                )
            return

        # Fallback to generic game handler
        from cogs.gambling.gambling_logic import handle_gamble_result
        await handle_gamble_result(interaction, self.user_id, self.game_key, amount)
