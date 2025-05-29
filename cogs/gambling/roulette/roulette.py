from discord.ui import View, Button, Select
from discord import Interaction, Embed
from .roulette_utils import spin_roulette, payout

class RouletteView(View):
    def __init__(self, user_id, parent, bet, choice, bet_type, user_gold):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.parent = parent
        self.bet = bet
        self.choice = choice
        self.bet_type = bet_type
        self.user_gold = user_gold
        self.result = spin_roulette()
        self.payout_multiplier = payout(self.bet_type, self.choice, self.result)
        self.result_number, self.result_color = self.result

    async def on_timeout(self):
        if hasattr(self, "message"):
            await self.message.edit(content="🕰️ Roulette session timed out.", view=None)

    async def start_game(self, interaction: Interaction):
        payout_amount = int(self.bet * self.payout_multiplier)
        embed = Embed(title="🎡 Roulette Result")
        embed.add_field(name="Result", value=f"**{self.result_number}** ({self.result_color})", inline=False)

        if self.payout_multiplier > 0:
            embed.add_field(name="🎉 Payout", value=f"You won **{payout_amount}** gold!", inline=False)
        else:
            embed.add_field(name="💀", value="You lost your bet.", inline=False)

        await interaction.response.edit_message(embed=embed, view=None)
