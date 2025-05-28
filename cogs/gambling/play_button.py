from cogs.gambling.gambling_logic import handle_gamble_result
import discord
from discord import Interaction

class GamblingPlayButton(discord.ui.Button):
    def __init__(self, user_id, game_key, get_amount_callback):
        super().__init__(label="Play", emoji="🎰", style=discord.ButtonStyle.red)
        self.user_id = user_id
        self.game_key = game_key
        self.get_amount = get_amount_callback  # A function that returns the current amount

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        amount = self.get_amount()
        await handle_gamble_result(interaction, self.user_id, self.game_key, amount)