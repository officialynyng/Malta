import asyncio
import discord
from discord.ui import View, Button, Modal, TextInput
from discord import Interaction, Embed

from cogs.exp_utils import update_user_gold
from cogs.exp_config import EXP_CHANNEL_ID
from cogs.gambling.roulette.roulette_utils import spin_roulette, payout
from cogs.gambling.gambling_ui_common import BetAmountSelectionView, PlayAgainButton, BackToGameButton, RefreshGoldButton

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
        self.add_item(RefreshGoldButton(user_id))
        self.add_item(BackToRouletteOptionsButton(user_id, user_gold, self.parent))
        self.add_item(BackToGameButton(self.user_id, parent=self.parent))


    async def on_timeout(self):
        if hasattr(self, "message"):
            await self.message.edit(content="🕰️ Roulette session timed out.", view=None)

class RoulettePlayButton(Button):
    def __init__(self, view: RouletteView):
        super().__init__(label="🎡 Play", style=discord.ButtonStyle.danger)
        self.view_ref = view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        await interaction.response.defer()

        payout_amount = int(self.view_ref.bet * self.view_ref.payout_multiplier)
        net_change = payout_amount - self.view_ref.bet

        # ✅ Update user gold
        self.view_ref.user_gold += net_change
        update_user_gold(
            self.view_ref.user_id,
            self.view_ref.user_gold,
            type_="roulette_win" if net_change > 0 else "roulette_loss",
            description=f"Roulette: {self.view_ref.bet} on {self.view_ref.choice} ({self.view_ref.bet_type}) → {self.view_ref.result_number} ({self.view_ref.result_color})"
        )


        # ✅ Broadcast result to EXP_CHANNEL_ID
        exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            if self.view_ref.payout_multiplier > 0:
                net_gain = int(self.view_ref.bet * (self.view_ref.payout_multiplier - 1))
                await exp_channel.send(
                    f"🎡 **{interaction.user.display_name}** bet **{self.view_ref.bet}** gold on **{self.view_ref.choice}** "
                    f"({self.view_ref.bet_type}) and won 🎉 **+{net_gain}**!"
                )
            else:
                await exp_channel.send(
                    f"🎡 **{interaction.user.display_name}** bet **{self.view_ref.bet}** gold on **{self.view_ref.choice}** "
                    f"({self.view_ref.bet_type}) and lost 💀"
                )


        # 🎡 Result embed
        embed = Embed(title="🎡 Roulette Result")
        embed.add_field(name="🎡 Your Bet", value=f"**{self.view_ref.bet}** gold on **{self.view_ref.choice}** ({self.view_ref.bet_type})", inline=False)
        embed.add_field(name="🎲 Result", value=f"**{self.view_ref.result_number}** ({self.view_ref.result_color})", inline=False)
        if self.view_ref.payout_multiplier > 0:
            embed.add_field(name="🎉 Payout", value=f"You won **{payout_amount}** gold!", inline=False)
        else:
            embed.add_field(name="💀", value="You lost your bet.", inline=False)
        embed.set_footer(text=f"💰 Gold: {self.view_ref.user_gold} | Bet: {self.view_ref.bet}")

        self.view_ref.clear_items()
        self.view_ref.add_item(PlayAgainButton(
            user_id=self.view_ref.user_id,
            game_key="roulette",
            parent=self.view_ref.parent,
            bet=self.view_ref.bet,
        ))
        await interaction.edit_original_response(embed=embed, view=self.view_ref)

class RouletteOptionView(View):
    def __init__(self, user_id, user_gold, parent):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_gold = user_gold
        self.parent = parent

        options = [
            discord.SelectOption(label="Red", value="color:Red", emoji="🔴"),
            discord.SelectOption(label="Black", value="color:Black", emoji="⚫"),
            discord.SelectOption(label="Pick a Number (0–36)", value="number", emoji="🔢")
        ]
    
        self.add_item(BackToGameButton(self.user_id, self.parent))
    @discord.ui.select(
        placeholder="🎡 Choose Red, Black, or a Number...",
        custom_id="roulette_bet_selector",  # must be unique globally
        options=[
            discord.SelectOption(label="Red", value="color:Red", emoji="🔴"),
            discord.SelectOption(label="Black", value="color:Black", emoji="⚫"),
            discord.SelectOption(label="Pick a Number (0–36)", value="number", emoji="🔢")
        ]
    )
    async def select_callback(self, interaction: Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        selection = select.values[0]

        if selection.startswith("color:"):
            color = selection.split(":")[1]

            async def roulette_color_callback(interaction: Interaction, bet: int):
                await interaction.edit_original_response(
                    content=f"🎡 Spinning for **{bet}** gold on **{color}**!",
                    embed=None,
                    view=RouletteView(
                        self.user_id,
                        parent=self.parent,
                        bet=bet,
                        choice=color,
                        bet_type="Color",
                        user_gold=self.user_gold
                    )
                )

            embed = Embed(
                title=f"🎡 Roulette — Bet on {color}",
                description="Choose your bet amount below.",
                color=discord.Color.green()
            )
            embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/roulette.png")  # ⬅️ Replace with your actual roulette banner
            embed.set_footer(text=f"💰 Gold: {self.user_gold}")

            await interaction.response.edit_message(
                content=None,
                embed=embed,
                view=BetAmountSelectionView(
                    self.user_id,
                    "roulette",
                    min_bet=10,
                    max_bet=10000,
                    parent=self.parent,
                    extra_callback=roulette_color_callback
                )
            )


        elif selection == "number":
            await interaction.response.send_modal(
                RouletteNumberModal(self.user_id, self.user_gold, self.parent)
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

                async def roulette_number_callback(interaction: Interaction, bet: int):
                    await interaction.edit_original_response(
                        content=f"🎡 Spinning for **{bet}** gold on **{number_choice}**!",
                        embed=None,
                        view=RouletteView(
                            self.user_id,
                            parent=self.parent,
                            bet=bet,
                            choice=str(number_choice),
                            bet_type="Number",
                            user_gold=self.user_gold
                        )
                    )

                await interaction.edit_original_response(
                    content=f"🎡 You chose **{number_choice}**. Now choose your bet amount:",
                    view=BetAmountSelectionView(
                        self.user_id,
                        "roulette",
                        min_bet=10,
                        max_bet=5000,
                        parent=self.parent,
                        extra_callback=roulette_number_callback
                    )
                )

            except asyncio.TimeoutError:
                await interaction.edit_original_response(
                    content="⌛ Timed out waiting for number input.",
                    view=None
                )


class RouletteNumberModal(Modal):
    def __init__(self, user_id, user_gold, parent):
        super().__init__(title="🎡 Enter a Number (0–36)")
        self.user_id = user_id
        self.user_gold = user_gold
        self.parent = parent

        self.number_input = TextInput(
            label="Pick a number to bet on",
            placeholder="0 to 36",
            max_length=2,
            required=True
        )
        self.add_item(self.number_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your modal.", ephemeral=True)
            return

        try:
            number_choice = int(self.number_input.value)
            if not 0 <= number_choice <= 36:
                raise ValueError("Invalid range")

        except Exception:
            await interaction.response.send_message("❌ Please enter a valid number between 0–36.", ephemeral=True)
            return

        async def roulette_number_callback(interaction: discord.Interaction, bet: int):
            await interaction.edit_original_response(
                content=f"🎡 Spinning for **{bet}** gold on **{number_choice}**!",
                embed=None,
                view=RouletteView(
                    self.user_id,
                    parent=self.parent,
                    bet=bet,
                    choice=str(number_choice),
                    bet_type="Number",
                    user_gold=self.user_gold
                )
            )

        await interaction.response.defer()  # acknowledges the modal submit to prevent "This interaction failed"
        embed = Embed(
            title=f"🎡 Roulette — Number {number_choice}",
            description="Choose your bet amount below.",
            color=discord.Color.green()
        )
        embed.set_image(url="https://theknightsofmalta.net/wp-content/uploads/2025/05/roulette.png")  # ⬅️ Replace with your roulette art
        embed.set_footer(text=f"💰 Gold: {self.user_gold}")

        await interaction.followup.send(
            embed=embed,
            view=BetAmountSelectionView(
                self.user_id,
                "roulette",
                min_bet=10,
                max_bet=10000,
                parent=self.parent,
                extra_callback=roulette_number_callback
            ),
            ephemeral=True
        )



class BackToRouletteOptionsButton(Button):
    def __init__(self, user_id, user_gold, parent):
        super().__init__(label="🎡 Back to Roulette Options", style=discord.ButtonStyle.secondary)
        self.user_id = user_id
        self.user_gold = user_gold
        self.parent = parent  # should be GameSelectionView or similar

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Not your session!", ephemeral=True)
            return

        from cogs.gambling.roulette.roulette import RouletteOptionView

        await interaction.response.edit_message(
            content="🎡 Pick Red, Black, or a Number:",
            embed=None,
            view=RouletteOptionView(self.user_id, self.user_gold, parent=self.parent)
        )