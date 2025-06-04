import discord
from discord.ui import View, Button
from discord import Embed, Interaction
from sqlalchemy import select, update, insert

from cogs.gambling.gambling_ui_common import BackToGameButton, PlayAgainButton, RefreshGoldButton
from cogs.exp_utils import get_user_data, update_user_gold
from cogs.exp_config import EXP_CHANNEL_ID, engine

from cogs.gambling.blackjack.blackjack_utils import create_shoe, draw_card, format_hand, hand_value
from cogs.gambling.bet_amount import BetAmountDropdown
from cogs.database.gambling_stats_table import gambling_stats
from cogs.x_utilities.ui_base import BaseCogView
import time


class BlackjackGameView(BaseCogView):
    shared_shoe = create_shoe()

    def __init__(self, user_id, user_gold, parent, bet, cog):
        super().__init__(cog=cog, timeout=None)
        self.user_id = user_id
        self.user_gold = user_gold
        self.parent = parent
        self.cog = cog
        self.bet = bet
        self.min_bet = 1
        self.max_bet = 5000
        self.amount = 100  # default bet
        self.player_hand = []
        self.dealer_hand = []
        self.message = None

        self.play_button = DrawCardsButton(self)
        self.add_item(BetAmountDropdown(self))
        self.add_item(self.play_button)
        self.add_item(BackToGameButton(user_id, self.parent, self.cog))
        self.add_item(RefreshGoldButton())

    def get_embed(self, reveal_dealer=False, final=False):
        embed = Embed(title="🃏 Blackjack", color=discord.Color.green())
        embed.add_field(
            name="Your Hand",
            value=f"{format_hand(self.player_hand)}\n**Total: {hand_value(self.player_hand)}**" if self.player_hand else "No cards yet.",
            inline=False
        )

        embed.add_field(
            name="Dealer's Hand",
            value=f"{format_hand(self.dealer_hand, reveal_all=reveal_dealer)}"
                + (f"\n**Total: {hand_value(self.dealer_hand)}**" if reveal_dealer else ""),
            inline=False
        )

        if final:
            embed.add_field(name="🎲 Result", value=self.evaluate_result(), inline=False)

        embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/blackjack.png")  # replace with your themed blackjack banner
        embed.add_field(name="💰 Gold", value=f"**{get_user_data(self.user_id)['gold']}**", inline=False)
        
        return embed

    def evaluate_result(self):
        player = hand_value(self.player_hand)
        dealer = hand_value(self.dealer_hand)

        if player > 21:
            return "**💥 You busted!**"
        elif dealer > 21:
            return "**🔥 Dealer busted — you win!**"
        elif player > dealer:
            return "**✅ You win!**"
        elif player == dealer:
            return "**🤝 It's a tie.**"
        else:
            return "**❌ Dealer wins.**"

    async def finalize_game(self, interaction: Interaction):
        player = hand_value(self.player_hand)
        dealer = hand_value(self.dealer_hand)
        result = self.evaluate_result()

        payout = 0
        if player > 21:
            payout = 0
        elif player == 21 and len(self.player_hand) == 2:
            payout = int(self.bet * 2.5)  # Blackjack pays 1.5x
        elif dealer > 21 or player > dealer:
            payout = self.bet * 2
        elif player == dealer:
            payout = self.bet
        else:
            payout = 0

        # Gold update
        user_data = get_user_data(self.user_id)
        delta = payout - self.bet
        user_data["gold"] += delta
        update_user_gold(
            self.user_id,
            user_data["gold"],
            type_="gamble_win" if delta > 0 else "gamble_loss" if delta < 0 else "gamble_tie",
            description=f"{'Won' if delta > 0 else 'Lost' if delta < 0 else 'Tied'} Blackjack for {abs(delta)} gold"
        )


        # Stats update
        now = int(time.time())
        with engine.begin() as conn:
            existing = conn.execute(select(gambling_stats).where(gambling_stats.c.user_id == self.user_id)).fetchone()
            values = {
                "total_bets": (existing.total_bets + 1) if existing else 1,
                "total_won": (existing.total_won + payout) if payout > 0 and existing else (payout if payout > 0 else 0),
                "total_lost": (existing.total_lost + self.bet) if payout == 0 and existing else (0 if payout > 0 else self.bet),
                "net_winnings": (existing.net_winnings + delta) if existing else delta,
                "last_gamble_ts": now
            }
            if existing:
                conn.execute(update(gambling_stats).where(gambling_stats.c.user_id == self.user_id).values(**values))
            else:
                conn.execute(insert(gambling_stats).values(user_id=self.user_id, **values))

        # Public result message
        exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            if delta > 0:
                await exp_channel.send(
                    f"🃏 **{interaction.user.display_name}** played Blackjack and won 🎉 **+{delta}**!"
                )
            elif delta < 0:
                await exp_channel.send(
                    f"🃏 **{interaction.user.display_name}** played Blackjack and lost 💀 **{abs(delta)}**"
                )
            else:
                await exp_channel.send(
                    f"🃏 **{interaction.user.display_name}** played Blackjack and tied 🤝"
                )

        self.clear_items()
        self.add_item(BackToGameButton(self.user_id, self.parent, self.cog))
        self.add_item(PlayAgainButton(self.user_id, parent_view=self.parent, game_key="blackjack", bet=self.bet))
        self.add_item(RefreshGoldButton(self.user_id))
        await interaction.response.edit_message(embed=self.get_embed(reveal_dealer=True, final=True), view=self)

class HitButton(Button):
    def __init__(self, game: BlackjackGameView):
        super().__init__(label="Hit", style=discord.ButtonStyle.primary, custom_id="blackjack_hit")
        self.game = game

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        self.game.player_hand.append(draw_card())
        if hand_value(self.game.player_hand) > 21:
            await self.game.finalize_game(interaction)
        else:
            await interaction.response.edit_message(embed=self.game.get_embed(), view=self.game)


class StandButton(Button):
    def __init__(self, game: BlackjackGameView):
        super().__init__(label="Stand", style=discord.ButtonStyle.secondary, custom_id="blackjack_stand")
        self.game = game

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        while hand_value(self.game.dealer_hand) < 17:
            self.game.dealer_hand.append(draw_card())

        await self.game.finalize_game(interaction)

class DrawCardsButton(discord.ui.Button):
    def __init__(self, view: BlackjackGameView):
        super().__init__(label="Draw Cards", emoji="🃏", style=discord.ButtonStyle.green, custom_id="blackjack_draw")
        self.view_ref = view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        self.view_ref.player_hand = [draw_card(), draw_card()]
        self.view_ref.dealer_hand = [draw_card(), draw_card()]

        self.view_ref.bet = getattr(self.view_ref, "amount", 100)
        self.view_ref.clear_items()
        self.view_ref.add_item(HitButton(self.view_ref))
        self.view_ref.add_item(StandButton(self.view_ref))
        self.view_ref.add_item(BackToGameButton(self.view_ref.user_id, self.view_ref.parent))
        self.disabled = True
        await interaction.response.edit_message(
            embed=self.view_ref.get_embed(),
            view=self.view_ref
        )
