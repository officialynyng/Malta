import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle, Embed
from discord.ui import View, Button
from sqlalchemy import select, desc
from datetime import timezone, timedelta
from cogs.exp_config import engine
from cogs.exp_utils import get_user_data
from cogs.database.transactions_table import transactions
from cogs.wallet.wallet_ui import TransactionView

WALLET_EMOJI = "💼"
CST = timezone(timedelta(hours=-6))
SHOW_EPHEMERAL = True


class WalletButton(Button):
    def __init__(self, wallet_cog):
        super().__init__(label="💼 Wallet", style=ButtonStyle.primary, custom_id="wallet_button")
        self.wallet_cog = wallet_cog

    async def callback(self, interaction: Interaction):
        await self.wallet_cog.send_wallet(interaction)
        user_id = interaction.user.id
        user_data = get_user_data(user_id)

        if not user_data:
            await interaction.response.send_message("❌ Couldn't retrieve your data.", ephemeral=True)
            return

        gold = user_data.get("gold", 0)

        with engine.connect() as conn:
            stmt = (
                select(transactions)
                .where(transactions.c.user_id == user_id)
                .order_by(desc(transactions.c.timestamp))
            )
            all_results = conn.execute(stmt).fetchall()

        embed = Embed(
            title=f"{WALLET_EMOJI} Your Wallet",
            description=f"**Gold:** {gold:,} 💰\n\nClick below to view your recent transactions.",
            color=discord.Color.from_rgb(0, 0, 0)
        )

        async def show_transactions_callback(inner_interaction):
            view = TransactionView(user_id, all_results, gold)
            await inner_interaction.response.edit_message(embed=view.get_embed(), view=view)

        view = View()
        show_button = Button(label="View Transactions", style=ButtonStyle.primary)
        show_button.callback = show_transactions_callback
        view.add_item(show_button)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=SHOW_EPHEMERAL)


class WalletButtonView(View):
    def __init__(self, wallet_cog):
        super().__init__(timeout=None)
        self.add_item(WalletButton(wallet_cog))


class WalletButtonCog(commands.Cog):
    def __init__(self, bot, wallet_cog):
        self.bot = bot
        self.wallet_cog = wallet_cog

    @app_commands.command(name="wallet", description="💼 Post the wallet button (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def wallet_command(self, interaction: Interaction):
        await interaction.response.send_message("✅ Wallet button posted.", ephemeral=True)
        await interaction.channel.send("", view=WalletButtonView(self.wallet_cog))



async def setup(bot: commands.Bot):
    await bot.add_cog(WalletButtonCog(bot))
    bot.add_view(WalletButtonView())  # Register persistent view on bot load
