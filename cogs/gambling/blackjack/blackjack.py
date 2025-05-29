import discord
from discord.ui import View, Button
from discord import Embed, Interaction
from sqlalchemy import select, update, insert

from cogs.gambling import BackToGameButton
from cogs.gambling. import PlayAgainButton
from cogs.exp_utils import get_user_data, update_user_gold
from cogs.exp_config import EXP_CHANNEL_ID, engine

from cogs.gambling.blackjack.blackjack_utils import create_deck, draw_card, hand_value, card_to_emoji, format_hand
from cogs.database.gambling_stats_table import gambling_stats
import time

class BlackjackGameView(View):
    def __init__(self, user_id, user_gold, parent, bet):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_gold = user_gold
        self.parent = parent
        self.bet = bet
        self.deck = create_deck()
        self.player_hand = [draw_card(self.deck), draw_card(self.deck)]
        self.dealer_hand = [draw_card(self.deck), draw_card(self.deck)]

        self.add_item(HitButton(self))
        self.add_item(StandButton(self))
        self.add_item(BackToGameButton(user_id, self.parent))
        self.add_item(PlayAgainButton(self.user_id, self.parent))
        self.message = None

    def get_embed(self, reveal_dealer=False, final=False):
        embed = Embed(title="🃏 Blackjack", color=discord.Color.red())
        embed.add_field(
            name="Your Hand",
            value=f"{format_hand(self.player_hand)}\n**Total: {hand_value(self.player_hand)}**",
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
        update_user_gold(self.user_id, user_data["gold"])

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
            await exp_channel.send(
                f"🃏 **{interaction.user.display_name}** played Blackjack and "
                f"{'won 🎉' if delta > 0 else 'lost 💀' if delta < 0 else 'tied 🤝'} "
                f"**{abs(delta)}** gold!"
            )

        await interaction.response.edit_message(embed=self.get_embed(reveal_dealer=True, final=True), view=None)


class HitButton(Button):
    def __init__(self, game: BlackjackGameView):
        super().__init__(label="Hit", style=discord.ButtonStyle.primary)
        self.game = game

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        self.game.player_hand.append(draw_card(self.game.deck))
        if self.game.hand_value(self.game.player_hand) > 21:
            await self.game.finalize_game(interaction)
        else:
            await interaction.response.edit_message(embed=self.game.get_embed(), view=self.game)


class StandButton(Button):
    def __init__(self, game: BlackjackGameView):
        super().__init__(label="Stand", style=discord.ButtonStyle.secondary)
        self.game = game

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        while self.game.hand_value(self.game.dealer_hand) < 17:
            self.game.dealer_hand.append(draw_card(self.game.deck))

        await self.game.finalize_game(interaction)
