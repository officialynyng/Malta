import discord
from discord.ui import View
from discord import Interaction, Embed

from cogs.exp_utils import get_user_data
from cogs.gambling.games_loader import GAMES
from cogs.gambling.blackjack.blackjack import BlackjackGameView
from cogs.gambling.roulette.roulette import RouletteOptionView
from cogs.gambling.gambling_ui_common import BetAmountSelectionView


class GameSelectionView(View):
    def __init__(self, user_id, user_gold, cog):
        super().__init__(timeout=None)  # Required for persistence
        self.user_id = user_id
        self.user_gold = user_gold
        self.cog = cog
        self.add_item(BackToGamblingMenuButton(self.user_id, self.cog))

    @discord.ui.select(
        placeholder="♠️ ♥️ ♦️ ♣️ What do you wish to play?",
        custom_id="game_selection_menu",  # required for persistence
        options=[
            discord.SelectOption(label=game["name"], value=key, description=game["description"][:100], emoji=game.get("emoji", "🎰"))
            for key, game in GAMES.items()
            if key not in ("big_spender", "blackjack") and not (key == "slot_machine" and "variants" in game)
        ] + [
            discord.SelectOption(label="Big Spender", value="big_spender", description="Bet 10,000 gold for a slim shot at massive returns.", emoji="💰"),
            discord.SelectOption(label="Blackjack", value="blackjack", description="Play a real-time game of Blackjack against the dealer.", emoji="🃏")
        ]
    )
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
            await interaction.response.edit_message(embed=embed, view=BlackjackGameView(self.user_id, self.user_gold, parent=self, bet=100))
            return

        if game_key == "roulette":
            embed = discord.Embed(
                title="🎡 Roulette",
                description="Pick Red, Black, or a Number. Will luck be on your side?",
                color=discord.Color.green()
            )
            embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/roulette.png")
            embed.set_footer(text=f"💰 Gold: {self.user_gold}")
            await interaction.response.edit_message(embed=embed, view=RouletteOptionView(self.user_id, self.user_gold, parent=self))
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


class BackToGamblingMenuButton(discord.ui.Button):
    def __init__(self, user_id, cog):
        super().__init__(label="⬅️ Back to Menu", style=discord.ButtonStyle.secondary, custom_id="back_to_menu")
        self.user_id = user_id
        self.cog = cog

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
