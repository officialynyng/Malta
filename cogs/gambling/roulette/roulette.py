import asyncio
import discord
from discord.ui import View, Button, Select
from discord import Interaction, Embed


from cogs.gambling.roulette.roulette_utils import spin_roulette, payout
from cogs.gambling.gambling_ui_common import BetAmountSelectionView

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

        self.add_item(RoulettePlayButton(self))

    async def on_timeout(self):
        if hasattr(self, "message"):
            await self.message.edit(content="🕰️ Roulette session timed out.", view=None)

class RoulettePlayButton(Button):
    def __init__(self, view: RouletteView):
        super().__init__(label="🎰 Play", style=discord.ButtonStyle.danger)
        self.view_ref = view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        await interaction.response.defer()

        payout_amount = int(self.view_ref.bet * self.view_ref.payout_multiplier)
        embed = Embed(title="🎡 Roulette Result")

        embed.add_field(
            name="🎯 Your Bet",
            value=f"**{self.view_ref.bet}** gold on **{self.view_ref.choice}** ({self.view_ref.bet_type})",
            inline=False
        )
        embed.add_field(
            name="🎲 Result",
            value=f"**{self.view_ref.result_number}** ({self.view_ref.result_color})",
            inline=False
        )

        if self.view_ref.payout_multiplier > 0:
            embed.add_field(
                name="🎉 Payout",
                value=f"You won **{payout_amount}** gold!",
                inline=False
            )
        else:
            embed.add_field(
                name="💀",
                value="You lost your bet.",
                inline=False
            )

        embed.set_footer(
            text=f"💰 Gold: {self.view_ref.user_gold} | Bet: {self.view_ref.bet}"
        )

        self.view_ref.clear_items()
        self.view_ref.add_item(Button(label="🔁 Play Again", style=discord.ButtonStyle.success, disabled=True))

        await interaction.edit_original_response(embed=embed, view=self.view_ref)

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
                    min_bet=10,
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
            await interaction.response.edit_message(
                content="🔢 Pick a number between 0–36 to bet on:",
                view=None
            )

            def check(msg):
                return msg.author.id == self.user_id and msg.channel == interaction.channel

            try:
                msg = await interaction.client.wait_for("message", timeout=30.0, check=check)
                if not msg.content.isdigit() or not (0 <= int(msg.content) <= 36):
                    await interaction.edit_original_response(
                        content="❌ Invalid number. Please enter a value between 0 and 36.",
                        view=None
                    )
                    return


                number_choice = int(msg.content)

                await interaction.edit_original_response(
                    content=f"🎯 You chose **{number_choice}**. Now choose your bet amount:",
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
                            choice=str(number_choice),
                            bet_type="Number",
                            user_gold=self.user_gold
                        )
                    )
                )
            except asyncio.TimeoutError:
                await interaction.edit_original_response(
                    content="⌛ Timed out waiting for number input.",
                    view=None
                )
