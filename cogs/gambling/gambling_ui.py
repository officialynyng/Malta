import discord
from discord.ui import View
from discord import Interaction

from cogs.gambling.games_loader import GAMES
from cogs.gambling.blackjack.blackjack import BlackjackGameView
from cogs.gambling.roulette.roulette import RouletteOptionView
from cogs.gambling.gambling_ui_common import BetAmountSelectionView


class GameSelectionView(View):
    def __init__(self, user_id, user_gold):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_gold = user_gold

        options = []

        # ✅ Load everything from GAMES except big_spender (we'll add manually)
        for key, game in GAMES.items():
            if key == "big_spender":
                continue

            if key == "slot_machine" and "variants" in game and game["variants"]:
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

        # ✅ Add Big Spender manually
        options.append(discord.SelectOption(
            label="Big Spender",
            value="big_spender",
            description="Bet 10,000 gold for a slim shot at massive returns.",
            emoji="💰"
        ))

        # ✅ Add Blackjack manually if not in GAMES already
        if "blackjack" not in GAMES and "blackjack" not in [opt.value for opt in options]:
            options.append(discord.SelectOption(
                label="Blackjack",
                value="blackjack",
                description="Play a real-time game of Blackjack against the dealer.",
                emoji="🃏"
            ))

        # ✅ Fallback if somehow empty (should never happen now)
        if not options:
            options.append(discord.SelectOption(
                label="No games available.",
                value="none",
                description="No available games to play at this time.",
                emoji="❌"
            ))


        # ✅ Create and add the select menu
        self.select = discord.ui.Select(
            placeholder="♠️ ♥️ ♦️ ♣️ What do you wish to play?",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        game_key = self.select.values[0]

        if game_key == "blackjack":
            embed = discord.Embed(
                title="🃏 Blackjack",
                description="Play a real-time game of Blackjack against the dealer.",
                color=discord.Color.green()
            )
            embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/blackjack.png")  # 🎴 replace with your blackjack image
            embed.set_footer(text=f"💰 Gold: {self.user_gold}")

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=BlackjackGameView(self.user_id, self.user_gold, parent=self, bet=100)
            )
            return


        if game_key == "roulette":
            embed = discord.Embed(
                title="🎡 Roulette",
                description="Pick Red, Black, or a Number. Will luck be on your side?",
                color=discord.Color.green()
            )
            embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/roulette.png")  # 🎡 replace with your roulette image
            embed.set_footer(text=f"💰 Gold: {self.user_gold}")

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=RouletteOptionView(self.user_id, self.user_gold, parent=self)
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

            # ✅ Ensure image is set properly
            if "image_url" in game and game["image_url"]:
                embed.set_image(url=game["image_url"])

            embed.set_footer(text=f"💰 Gold: {self.user_gold}")


            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=BetAmountSelectionView(self.user_id, game_key, bet, bet, parent=self)
            )
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

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=BetAmountSelectionView(self.user_id, f"slot_machine:{variant_key}", min_bet, max_bet, parent=self)
            )
            return

        else:
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

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=BetAmountSelectionView(self.user_id, game_key, min_bet, max_bet, parent=self)
        )


