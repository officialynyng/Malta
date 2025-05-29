import discord
from discord.ui import View, Button
from discord import Interaction, Embed, ButtonStyle

from cogs.gambling.bet_amount import BetAmountDropdown
from cogs.exp_utils import get_user_data, get_user_data
from cogs.gambling.games_loader import GAMES
from cogs.gambling.play_button import GamblingPlayButton
from cogs.gambling.ui_common import BackToGameButton, PlayAgainButton


class GameSelectionView(View):
    def __init__(self, user_id, user_gold):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_gold = user_gold

        options = []

        for key, game in GAMES.items():
            if key == "slot_machine" and "variants" in game:
                for variant_key, variant in game["variants"].items():
                    options.append(discord.SelectOption(
                        label=variant['name'],
                        value=f"slot_machine:{variant_key}",
                        description=variant["description"][:100],
                        emoji=variant.get("emoji", "🎰")
                    ))
            elif key == "roulette":
                options.append(discord.SelectOption(
                    label=game["name"],
                    value=key,
                    description=game["description"][:100],
                    emoji=game.get("emoji", "🎯")
                ))
            else:
                options.append(discord.SelectOption(
                    label=game["name"],
                    value=key,
                    description=game["description"][:100],
                    emoji=game.get("emoji", "🎰")
                ))


        # ✅ Add Blackjack manually if not in GAMES already
        if "blackjack" not in GAMES:
            options.append(discord.SelectOption(
                label="Blackjack",
                value="blackjack",
                description="Play a real-time game of Blackjack against the dealer.",
                emoji="🃏"
            ))


        # ✅ Create and add the select menu
        self.select = discord.ui.Select(
            placeholder="🎲 Choose a gambling game...",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        game_key = self.select.values[0]

        if game_key == "blackjack":
            from cogs.gambling.blackjack.blackjack import BlackjackView
            await interaction.response.edit_message(
                content="🃏 You've chosen **Blackjack**. Ready to draw your cards?",
                embed=None,
                view=BlackjackView(self.user_id, self.user_gold, parent=self)
            )
            return


        if game_key == "roulette":
            from cogs.gambling.roulette.roulette import RouletteView  # Adjust path as needed
            await interaction.response.edit_message(
                content="🎯 Choose your roulette bet type:",
                embed=None,
                view=RouletteView(self.user_id, parent=self, bet=100, user_gold=self.user_gold)
            )
            return


        if game_key.startswith("slot_machine:"):
            variant_key = game_key.split(":")[1]
            game = GAMES["slot_machine"]["variants"][variant_key]

        else:
            game = GAMES[game_key]

        min_bet = game.get("min_bet", 1)
        max_bet = 5000
        await interaction.response.edit_message(
            content=f"💰 You've selected **{game['name']}**. Now choose your bet amount:",
            embed=None,
            view=BetAmountSelectionView(self.user_id, game_key, min_bet, max_bet, parent=self)
        )


class BetAmountSelectionView(View):
    def __init__(self, user_id, game_key, min_bet, max_bet, parent=None):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.game_key = game_key
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.amount = min_bet
        self.parent = parent
        

        self.dropdown = BetAmountDropdown(self)
        self.play_button = GamblingPlayButton(user_id, game_key, lambda: self.amount, parent=self.parent)


        self.add_item(self.dropdown)
        self.add_item(self.play_button)
        self.add_item(RefreshGoldButton(user_id))
        if self.parent:
            self.add_item(BackToGameButton(user_id, self.parent))


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