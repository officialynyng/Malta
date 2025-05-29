import discord
from discord.ui import View, Button
from discord import Interaction, Embed, ButtonStyle

from cogs.gambling.bet_amount import BetAmountDropdown
from cogs.exp_utils import get_user_data, get_user_data
from cogs.gambling.games_loader import GAMES
from cogs.gambling.play_button import GamblingPlayButton
from cogs.gambling.ui_common import BackToGameButton, PlayAgainButton
from cogs.gambling.blackjack.blackjack import BlackjackGameView
from cogs.gambling.roulette.roulette import RouletteView

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
                    from cogs.gambling.roulette import RouletteView

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