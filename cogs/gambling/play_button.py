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

        # ✅ BLACKJACK (custom view-based game)
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

        # ✅ EXTRA CALLBACK for custom games
        if self.extra_callback:
            # If it's a coroutine (async def), assume it takes interaction & amount
            if asyncio.iscoroutinefunction(self.extra_callback):
                await self.extra_callback(interaction, amount)
            else:
                # If it's a lambda or returns a View (like slots), just show it
                view = self.extra_callback(amount)
                await interaction.edit_original_response(
                    content=f"🎲 You bet **{amount}** gold on {self.game_key.title()}!",
                    embed=None,
                    view=view
                )
            return

        # ✅ DEFAULT fallback handler (e.g., odds-based games)
        from cogs.gambling.gambling_logic import handle_gamble_result
        await handle_gamble_result(interaction, self.user_id, self.game_key, amount)
