import discord
from discord.ui import View, Button, Select
from discord import Interaction, Embed


from cogs.gambling.roulette.roulette_utils import spin_roulette, payout
from cogs.gambling.x_ui_common import BetAmountSelectionView

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


class RouletteOptionView(View):
    def __init__(self, user_id, user_gold, parent):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_gold = user_gold
        self.parent = parent

        options = [
            discord.SelectOption(label="Red", value="color:Red", emoji="🔴"),
            discord.SelectOption(label="Black", value="color:Black", emoji="⚫"),
            discord.SelectOption(label="Pick a Number (0–36)", value="number", emoji="🔢")
        ]

        self.select = discord.ui.Select(
            placeholder="🎯 Choose Red, Black, or a Number...",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        selection = self.select.values[0]

        if selection.startswith("color:"):
            color = selection.split(":")[1]
            await interaction.response.edit_message(
                content=f"🎯 You selected **{color}**. Now choose your bet.",
                view=BetAmountSelectionView(
                    self.user_id,
                    "roulette",
                    min_bet=100,
                    max_bet=10000,
                    parent=self.parent,
                    extra_callback=lambda bet: RouletteView(
                        self.user_id,
                        parent=self.parent,
                        bet=bet,
                        choice=color,
                        bet_type="Color",
                        user_gold=self.user_gold
                    )
                )
            )
        elif selection == "number":
            # Implement a number picker flow next...
            await interaction.response.send_message("🔢 Number betting not implemented yet.", ephemeral=True)
