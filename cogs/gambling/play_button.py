from cogs.gambling.gambling_logic import handle_gamble_result
from cogs.gambling.blackjack.blackjack import BlackjackGameView
from cogs.exp_utils import get_user_data

import asyncio
import discord
from discord import Interaction

class GamblingPlayButton(discord.ui.Button):
    def __init__(self, user_id, game_key, get_amount_callback, parent=None):
        super().__init__(label="Play", emoji="🎰", style=discord.ButtonStyle.red)
        self.user_id = user_id
        self.game_key = game_key
        self.get_amount = get_amount_callback
        self.parent = parent

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)
        
        amount = self.get_amount()
        if amount <= 0:
            return await interaction.response.send_message("❌ Invalid bet amount.", ephemeral=True)

        user_data = get_user_data(self.user_id)

        if self.game_key == "blackjack":
            await interaction.response.edit_message(
                content=f"🃏 You bet **{amount}** gold on Blackjack!",
                embed=None,
                view=BlackjackGameView(self.user_id, user_data['gold'], parent=self.parent, bet=amount)
            )
            return
        
        elif self.game_key == "roulette":
            await interaction.response.send_message("🎯 Pick a number between 0–36 to bet on:", ephemeral=True)

            def check(msg):
                return msg.author.id == self.user_id and msg.channel == interaction.channel

            try:
                msg = await interaction.client.wait_for("message", timeout=30.0, check=check)
                number = msg.content.strip()

                if not number.isdigit() or not (0 <= int(number) <= 36):
                    return await interaction.followup.send("❌ Invalid number. Please enter a number between 0–36.", ephemeral=True)

                user_data = get_user_data(self.user_id)
                from cogs.gambling.roulette import RouletteView

                await interaction.followup.send(
                    content=f"🎡 You bet **{amount}** gold on Roulette number **{number}**!",
                    embed=None,
                    view=RouletteView(self.user_id, parent=self.parent, bet=amount, choice=number, bet_type="Number", user_gold=user_data['gold']),
                    ephemeral=False  # Make this public or match your preferred setting
                )
                return
            
            except asyncio.TimeoutError:
                await interaction.followup.send("⌛ Timed out waiting for number selection.", ephemeral=True)



        await handle_gamble_result(interaction, self.user_id, self.game_key, amount)
