import discord
from discord.ui import View
from discord import Interaction

from cogs.gambling.games_loader import GAMES
from cogs.gambling.blackjack.blackjack import BlackjackGameView
from cogs.gambling.roulette.roulette import RouletteView
from cogs.gambling
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
            await interaction.response.edit_message(
                content="🃏 You've chosen **Blackjack**. Ready to draw your cards?",
                embed=None,
                view=BlackjackGameView(self.user_id, self.user_gold, parent=self)
            )
            return


        if game_key == "roulette":
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
