import asyncio
import discord
from discord import Interaction, Embed
from discord.ui import Button, View

from cogs.exp_utils import get_user_data, get_user_data
from cogs.gambling.bet_amount import BetAmountDropdown
from cogs.gambling.play_button import GamblingPlayButton
from cogs.x_utilities.ui_base import BaseCogButton, BaseCogView


class PlayAgainButton(Button):
    def __init__(self, game_key: str):
        print(f"[DEBUG] Constructing PlayAgainButton for game: {game_key}")
        super().__init__(
            label="🔁 Play Again",
            style=discord.ButtonStyle.success,
            custom_id=f"persistent_play_again_{game_key}"
        )

    async def callback(self, interaction: Interaction):
        user_id = interaction.user.id
        print("[DEBUG] PlayAgainButton triggered by user:", interaction.user.id)
        try:
            # Extract game_key from custom_id
            game_key = self.custom_id.removeprefix("persistent_play_again_")
            user_data = get_user_data(user_id) or {"gold": 0}
            gold = user_data.get("gold", 0)

            if game_key == "blackjack":
                from cogs.gambling.gambling_ui_common import BetAmountSelectionView

                cog = interaction.client.get_cog("GamblingGroup")
                if not cog:
                    print("[ERROR] GamblingGroup cog not found!")
                    await interaction.response.send_message("❌ Gambling system is currently unavailable. Please try again later.", ephemeral=True)
                    return

                view = BetAmountSelectionView(
                    user_id=user_id,
                    game_key="blackjack",
                    min_bet=5,            # ✅ provide reasonable values
                    max_bet=gold,           # ✅ this will reflect user's current gold
                    parent=None,
                    cog=cog
                ) 
                view.parent = view

                embed = Embed(
                    title="🃏 Blackjack — Place Your Bet",
                    description="🃏 You've chosen **Blackjack**. Pick your bet to start!",
                    color=discord.Color.green()
                )
                embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/blackjack.png")

                await interaction.response.edit_message(
                    embed=embed,
                    view=view
                )


            elif game_key == "roulette":
                from cogs.gambling.roulette.roulette import RouletteOptionView

                view = RouletteOptionView(
                    user_id=user_id,
                    user_gold=gold,
                    parent=None,
                    cog=interaction.client.get_cog("GamblingGroup")
                )

                await interaction.response.edit_message(
                    content="🎡 Choose your Roulette type:",
                    embed=None,
                    view=view
                )

            else:
                raise ValueError("Unknown game key.")

        except Exception as e:
            print(f"[PlayAgainButton] Failed: {e}")
            await interaction.response.send_message("❌ Something went wrong starting the game again.", ephemeral=True)



class RefreshGoldButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="🔄 Refresh Gold View",
            style=discord.ButtonStyle.grey,
            custom_id="refresh_gold_button"  # ✅ Needed for persistence
        )

    async def callback(self, interaction: Interaction):
        user_data = get_user_data(interaction.user.id)
        gold = user_data.get("gold", 0)

        # 💡 Send updated gold info privately
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"💰 {interaction.user.display_name}'s Gold",
                description=f"You currently have **{gold:,}** gold.",
                color=discord.Color.green()
            ),
            ephemeral=True  # ✅ private and safe
        )






class BackToGameButton(BaseCogButton):
    def __init__(self, *, user_id, parent, cog):
        super().__init__(
            label="⬅️ Back",
            style=discord.ButtonStyle.secondary,
            custom_id="back_to_game_button",  # ✅ Required for persistence
            user_id=user_id,
            cog=cog
        )
        self.user_id = user_id
        self.parent = parent
        self.cog = cog

    async def callback(self, interaction: Interaction):
        from cogs.exp_utils import get_user_data, update_user_gold
        from cogs.exp_config import EXP_CHANNEL_ID
        from cogs.gambling.gambling_ui import GameSelectionView

        user_data = get_user_data(self.user_id) or {"gold": 0}

        # 💥 Penalize if the game was in progress
        if hasattr(self.parent, "player_hand") and self.parent.player_hand:
            penalty = getattr(self.parent, "bet", 100)

            user_data["gold"] -= penalty
            update_user_gold(
                self.user_id,
                user_data["gold"],
                type_="gamble_quit",
                description=f"Left Blackjack early and lost {penalty} gold"
            )

            # 🕵️ Ephemeral to user (safe send)
            embed_notice = discord.Embed(
                title="🏳️ You Left the Game",
                description=f"You lost **{penalty:,}** gold for quitting mid-game.",
                color=discord.Color.red()
            )

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed_notice, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed_notice, ephemeral=True)


            # 📢 Public announcement
            exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"🏳️ **{interaction.user.display_name}** fled from a Blackjack game and forfeited **{penalty:,}** gold!"
                )

        # ↩️ Return to menu
        embed = discord.Embed(
            title="🎰 Welcome to the Gambling Hall",
            description="Pick your game to begin.",
            color=discord.Color.green()
        )
        embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/Gold-Casino.png")
        embed.set_footer(text=f"💰 Gold: {user_data['gold']}")

        # ✅ Ensure interaction hasn't already responded
        if interaction.response.is_done():
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=None,
                embed=embed,
                view=GameSelectionView(user_id=self.user_id, user_gold=user_data["gold"], cog=self.cog)
            )
        else:
            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=GameSelectionView(user_id=self.user_id, user_gold=user_data["gold"], cog=self.cog)
        )







class BetAmountSelectionView(BaseCogView):
    def __init__(self, user_id, game_key, min_bet, max_bet, parent=None, extra_callback=None, cog=None):
        super().__init__(cog=cog, timeout=None)
        self.user_id = user_id
        self.game_key = game_key
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.amount = min_bet
        self.parent = parent
        self.cog = cog

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
        self.add_item(RefreshGoldButton())
        # ✅ Always add a Back button, even if parent is None
        back_parent = self.parent or self  # fallback to self if no parent
        self.add_item(BackToGameButton(user_id=user_id, parent=back_parent, cog=self.cog))



class PersistentPlayAgainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PlayAgainButton(game_key="blackjack"))
        self.add_item(PlayAgainButton(game_key="roulette"))
