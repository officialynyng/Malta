import asyncio
import discord
from discord.ui import Button
from discord import Interaction
from discord.ui import Button, View

from cogs.exp_utils import get_user_data, get_user_data
from cogs.exp_utils import get_user_data, get_user_data
from cogs.gambling.bet_amount import BetAmountDropdown
from cogs.gambling.play_button import GamblingPlayButton


class PlayAgainButton(Button):
    def __init__(self, user_id, parent_view):
        super().__init__(label="🔁 Play Again", style=discord.ButtonStyle.success)
        self.user_id = user_id
        self.parent = parent_view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=None, view=self.parent)

class RefreshGoldButton(discord.ui.Button):
    def __init__(self, user_id):
        super().__init__(label="Refresh Gold View", emoji="🔄", style=discord.ButtonStyle.grey)
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        user_data = get_user_data(self.user_id)
        await interaction.response.send_message(
            f"💰 You now have **{user_data['gold']}** gold.", ephemeral=True
        )

class BackToGameButton(Button):
    def __init__(self, user_id, parent):
        super().__init__(label="⬅️ Back", style=discord.ButtonStyle.secondary)
        self.user_id = user_id
        self.parent = parent

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=None, view=self.parent)


class BetAmountSelectionView(View):
    def __init__(self, user_id, game_key, min_bet, max_bet, parent=None):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.game_key = game_key
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.amount = min_bet
        self.parent = parent

        extra_callback = None  # ← DEFINE THIS FIRST

        if game_key == "roulette":
            async def handle_roulette(interaction: Interaction, amount):
                await interaction.response.send_message("🎯 Pick a number between 0–36 to bet on:", ephemeral=True)

                def check(msg):
                    return msg.author.id == user_id and msg.channel == interaction.channel

                try:
                    msg = await interaction.client.wait_for("message", timeout=30.0, check=check)
                    number = msg.content.strip()

                    if not number.isdigit() or not (0 <= int(number) <= 36):
                        return await interaction.followup.send("❌ Invalid number. Please enter a number between 0–36.", ephemeral=True)

                    user_data = get_user_data(user_id)
                    from cogs.gambling.roulette.roulette import RouletteView

                    await interaction.followup.send(
                        content=f"🎡 You bet **{amount}** gold on Roulette number **{number}**!",
                        embed=None,
                        view=RouletteView(user_id, parent=parent, bet=amount, choice=number, bet_type="Number", user_gold=user_data['gold']),
                        ephemeral=False
                    )

                except asyncio.TimeoutError:
                    await interaction.followup.send("⌛ Timed out waiting for number selection.", ephemeral=True)

            extra_callback = handle_roulette

        # ✅ Now use the callback
        self.dropdown = BetAmountDropdown(self)
        self.play_button = GamblingPlayButton(user_id, game_key, lambda: self.amount, parent=self.parent, extra_callback=extra_callback)

        self.add_item(self.dropdown)
        self.add_item(self.play_button)
        self.add_item(RefreshGoldButton(user_id))
        if self.parent:
            self.add_item(BackToGameButton(user_id, self.parent))

