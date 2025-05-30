import asyncio
import discord
from discord import Interaction
from discord.ui import Button, View

from cogs.exp_utils import get_user_data, get_user_data
from cogs.gambling.bet_amount import BetAmountDropdown
from cogs.gambling.play_button import GamblingPlayButton


class PlayAgainButton(Button):
    def __init__(self, user_id, parent_view=None, game_key=None, bet=None):
        super().__init__(label="🔁 Play Again", style=discord.ButtonStyle.success)
        self.user_id = user_id
        self.parent = parent_view
        self.game_key = game_key
        self.bet = bet

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        user_data = get_user_data(self.user_id)
        gold = user_data.get('gold', 0)
        try:
            if self.game_key == "blackjack":
                from cogs.gambling.blackjack.blackjack import BlackjackGameView
                await interaction.response.edit_message(
                    content="🃏 You've chosen **Blackjack**. Ready to draw your cards?",
                    embed=None,
                    view=BlackjackGameView(self.user_id, gold, self.parent, self.bet or 100)
                )
                return

            elif self.game_key == "roulette":
                from cogs.gambling.roulette.roulette import RouletteOptionView
                await interaction.response.edit_message(
                    content="🎡 Choose your Roulette type:",
                    embed=None,
                    view=RouletteOptionView(self.user_id, gold, self.parent)
                )
                return

        except Exception as e:
            print(f"PlayAgain fallback error: {e}")

        # Fallback to game hall
        if self.parent:
            await interaction.response.edit_message(
                content="🎲 Back to the Gambling Hall. Choose your game.",
                embed=None,
                view=self.parent
            )



class RefreshGoldButton(discord.ui.Button):
    def __init__(self, user_id):
        super().__init__(label="Refresh Gold View", emoji="🔄", style=discord.ButtonStyle.grey)
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        user_data = get_user_data(self.user_id)

        # Try to get the original embed and update it
        original_message = interaction.message
        embed = original_message.embeds[0] if original_message.embeds else discord.Embed()

        # Remove any existing gold field
        for i, field in enumerate(embed.fields):
            if field.name == "💰 Gold":
                embed.remove_field(i)
                break

        embed.add_field(name="💰 Gold", value=f"**{user_data['gold']}**", inline=False)

        await interaction.response.edit_message(embed=embed)


class BackToGameButton(Button):
    def __init__(self, user_id, parent):
        super().__init__(label="⬅️ Back", style=discord.ButtonStyle.secondary)
        self.user_id = user_id
        self.parent = parent

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        # ✅ Lazy imports to prevent circular dependency
        from cogs.gambling.gambling_ui import GameSelectionView
        from cogs.exp_utils import get_user_data

        user_data = get_user_data(self.user_id)
        gold = user_data.get("gold", 0)

        embed = discord.Embed(
            title="🎰 Welcome to the Gambling Hall",
            description="Pick your game to begin.",
            color=discord.Color.green()
        )
        embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/Gold-Casino.png")
        embed.set_footer(text=f"💰 Gold: {gold}")

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=GameSelectionView(self.user_id, gold)
        )


class BetAmountSelectionView(View):
    def __init__(self, user_id, game_key, min_bet, max_bet, parent=None, extra_callback=None):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.game_key = game_key
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.amount = min_bet
        self.parent = parent
        self.extra_callback = extra_callback  # ← KEEP THIS

        self.dropdown = BetAmountDropdown(self)
        self.play_button = GamblingPlayButton(
            user_id,
            game_key,
            lambda: self.amount,
            parent=self.parent,
            extra_callback=self.extra_callback  # ← PASS THIS IN
        )

        self.add_item(self.dropdown)
        self.add_item(self.play_button)
        self.add_item(RefreshGoldButton(user_id))
        if self.parent:
            self.add_item(BackToGameButton(user_id, self.parent))

