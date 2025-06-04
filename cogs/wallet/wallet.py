import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ui import View, Button
from sqlalchemy import select, desc
from datetime import timezone, timedelta
from cogs.exp_config import engine
from cogs.exp_utils import get_user_data
from cogs.database.transactions_table import transactions
from cogs.wallet.wallet_button import WalletButtonView, WalletButtonCog
from cogs.wallet.wallet_ui import TransactionView
DEBUG = True
WALLET_EMOJI = "💼"
CST = timezone(timedelta(hours=-6))
SHOW_EPHEMERAL = True  # Set to False to make wallet public

class Wallet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_wallet(self, interaction: Interaction):
        user_id = interaction.user.id

        if DEBUG:
            print(f"{WALLET_EMOJI} [DEBUG] Fetching wallet for user {user_id}")

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

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)



async def setup(bot: commands.Bot):
    # Wait until Wallet cog is available
    await bot.wait_until_ready()
    wallet_cog = bot.get_cog("Wallet")
    if wallet_cog:
        bot.add_view(WalletButtonView(wallet_cog))
    else:
        print("⚠️ Wallet cog not loaded — wallet button will not function.")

    await bot.add_cog(WalletButtonCog(bot))
