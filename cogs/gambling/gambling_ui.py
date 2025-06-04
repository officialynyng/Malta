import discord
from discord.ui import View
from discord import Interaction, Embed

from cogs.exp_utils import get_user_data
from cogs.gambling.games_loader import GAMES
from cogs.gambling.blackjack.blackjack import BlackjackGameView
from cogs.gambling.roulette.roulette import RouletteOptionView
from cogs.gambling.gambling_ui_common import BetAmountSelectionView
from cogs.x_utilities.ui_base import BaseCogView, BaseCogButton

class GameSelectionView(BaseCogView):
    def __init__(self, user_id, user_gold, cog):
        super().__init__(cog=cog, timeout=None)
        self.user_id = user_id
        self.user_gold = user_gold
        self.cog = cog

        # Build options manually
        options = [
            discord.SelectOption(
                label=variant["name"],
                value=f"slot_machine:{variant_key}",
                description=variant.get("description", "")[:100],
                emoji=variant.get("emoji", "🎰")
            )
            for variant_key, variant in GAMES.get("slot_machine", {}).get("variants", {}).items()
        ] + [
            discord.SelectOption(
                label=game["name"],
                value=key,
                description=game["description"][:100],
                emoji=game.get("emoji", "🎰")
            )
            for key, game in GAMES.items()
            if key not in ("slot_machine", "big_spender", "blackjack")
        ] + [
            discord.SelectOption(
                label="Big Spender",
                value="big_spender",
                description="Bet 10,000 gold for a slim shot at massive returns.",
                emoji="💰"
            ),
            discord.SelectOption(
                label="Blackjack",
                value="blackjack",
                description="Play a real-time game of Blackjack against the dealer.",
                emoji="🃏"
            )
        ]

        # Create the Select manually
        select = discord.ui.Select(
            placeholder="♠️ ♥️ ♦️ ♣️ What do you wish to play?",
            options=options,
            custom_id="game_selection_menu"
        )
        select.callback = lambda interaction: self.select_callback(select, interaction)  # bind the function manually
        self.add_item(select)

        self.add_item(BackToGamblingMenuButton(self.user_id, self.cog))

    async def select_callback(self, select, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        game_key = select.values[0]  # ✅ This is the correct way to get the selected option

        if game_key == "blackjack":
            embed = discord.Embed(
                title="🃏 Blackjack",
                description="Play a real-time game of Blackjack against the dealer.",
                color=discord.Color.green()
            )
            embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/blackjack.png")
            embed.set_footer(text=f"💰 Gold: {self.user_gold}")
            await interaction.response.edit_message(embed=embed, view=BlackjackGameView(self.user_id, self.user_gold, parent=self, bet=100, cog=self.cog))

            return

        if game_key == "roulette":
            embed = discord.Embed(
                title="🎡 Roulette",
                description="Pick Red, Black, or a Number. Will luck be on your side?",
                color=discord.Color.green()
            )
            embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/roulette.png")
            embed.set_footer(text=f"💰 Gold: {self.user_gold}")
            await interaction.response.edit_message(
                embed=embed,
                view=RouletteOptionView(self.user_id, self.user_gold, parent=self, cog=self.cog)
            )
            return

        if game_key == "big_spender":
            game = GAMES[game_key]
            bet = game.get("min_bet", 10000)
            embed = discord.Embed(
                title=f"{game.get('emoji', '🎰')} {game['name']}",
                description=game["description"],
                color=discord.Color.green()
            )
            embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/big_spender_official.png")
            embed.set_footer(text=f"💰 Gold: {self.user_gold}")
            await interaction.response.edit_message(embed=embed, view=BetAmountSelectionView(self.user_id, game_key, bet, bet, parent=self))
            return

        if game_key.startswith("slot_machine:"):
            variant_key = game_key.split(":")[1]
            game = GAMES["slot_machine"]["variants"][variant_key]
            min_bet = game.get("min_bet", 1)
            max_bet = 5000
            embed = discord.Embed(
                title=f"{game.get('emoji', '🎰')} {game['name']}",
                description=game["description"],
                color=discord.Color.green()
            )
            if "image_url" in game:
                embed.set_image(url=game["image_url"])
            embed.set_footer(text=f"💰 Gold: {self.user_gold}")
            await interaction.response.edit_message(embed=embed, view=BetAmountSelectionView(self.user_id, f"slot_machine:{variant_key}", min_bet, max_bet, parent=self))
            return

        # Fallback for all other games
        game = GAMES[game_key]
        min_bet = game.get("min_bet", 1)
        max_bet = 5000
        embed = discord.Embed(
            title=f"{game.get('emoji', '🎰')} {game['name']}",
            description=game["description"],
            color=discord.Color.green()
        )
        if "image_url" in game:
            embed.set_image(url=game["image_url"])
        embed.set_footer(text=f"💰 Gold: {self.user_gold}")
        await interaction.response.edit_message(embed=embed, view=BetAmountSelectionView(self.user_id, game_key, min_bet, max_bet, parent=self))

class BackToGamblingMenuButton(BaseCogButton):
    def __init__(self, user_id, cog):
        super().__init__(
            label="⬅️ Back to Menu",
            style=discord.ButtonStyle.secondary,
            custom_id="back_to_menu",
            user_id=user_id,
            cog=cog
        )


    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your menu!", ephemeral=True)
        from cogs.gambling.UI_MainMenu import GamblingMenuView 
        view = GamblingMenuView(self.cog)
        embed = Embed(
            title="🎰 Welcome to the Gambling Hall",
            description="Pick your game to begin.",
            color=discord.Color.green()
        )
        user_data = get_user_data(self.user_id)
        gold = user_data["gold"] if user_data else 0
        embed.set_footer(text=f"💰 Gold: {gold}")
        await interaction.response.edit_message(embed=embed, view=view)
