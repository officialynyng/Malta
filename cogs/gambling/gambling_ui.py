import discord
from discord.ui import View, Button
from discord import Interaction, Embed, ButtonStyle

import json
import os

from cogs.gambling.bet_amount import BetAmountDropdown, GamblingPlayButton
from cogs.exp_utils import get_user_data, get_user_data

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "games_config.json")
with open(CONFIG_PATH) as f:
    GAMES = json.load(f)


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
            else:
                options.append(discord.SelectOption(
                    label=game["name"],
                    value=key,
                    description=game["description"][:100],
                    emoji=game.get("emoji", "🎰")
                ))

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

        if game_key == "roulette":
            await interaction.response.send_message(
                "🎡 Choose your roulette bet type:",
                view=RouletteVariantSelectionView(self.user_id, self.user_gold),
                ephemeral=True
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


class BackToGameButton(Button):
    def __init__(self, user_id, parent_view):
        super().__init__(label="⬅️ Back", style=ButtonStyle.blurple)
        self.user_id = user_id
        self.parent_view = parent_view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        await interaction.response.edit_message(
            content=None,
            embed=Embed(
                title="🎰 Welcome back to the Gambling Hall",
                description="Pick your game to begin.",
                color=discord.Color.red()
            ),
            view=self.parent_view
        )

class RouletteVariantSelectionView(View):
    def __init__(self, user_id, user_gold):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_gold = user_gold

        options = [
            discord.SelectOption(label=variant, value=variant,
                description=f"{data['odds']*100:.1f}% chance, x{data['payout']} payout",
                emoji=data.get("emoji", "🎯"))
            for variant, data in GAMES["roulette"]["variants"].items()
        ]

        self.select = discord.ui.Select(
            placeholder="Choose Red, Black, or a Number (0–36)...",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        variant_key = self.select.values[0]
        full_game_key = f"roulette:{variant_key}"
        variant = GAMES["roulette"]["variants"][variant_key]

        await interaction.response.send_message(
            f"🎯 Bet type: **{variant_key}**\n💰 Choose your wager:",
            view=BetAmountSelectionView(self.user_id, full_game_key, min_bet=100, max_bet=10000),
            ephemeral=True
        )


class BetAmountSelectionView(View):
    def __init__(self, user_id, game_key, min_bet, max_bet):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.game_key = game_key
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.amount = min_bet

        self.dropdown = BetAmountDropdown(self)
        self.play_button = GamblingPlayButton(user_id, game_key, lambda: self.amount)

        self.add_item(self.dropdown)
        self.add_item(self.play_button)
        self.add_item(RefreshGoldButton(user_id))


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