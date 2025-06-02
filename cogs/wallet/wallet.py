import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ui import View, Button
from sqlalchemy import select, desc
from cogs.exp_config import engine
from cogs.exp_utils import get_user_data
from cogs.database.transactions_table import transactions

DEBUG = True
WALLET_EMOJI = "💼"

class TransactionView(View):
    def __init__(self, user_id, transactions, page=0):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.transactions = transactions
        self.page = page
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(PrevPageButton(self))
        self.add_item(NextPageButton(self))

    def get_embed(self):
        embed = Embed(title=f"💼 Recent Transactions", color=discord.Color.dark_gold())
        start = self.page * 5
        end = start + 5
        page_txns = self.transactions[start:end]

        if page_txns:
            for row in page_txns:
                amount_str = f"+{row.amount}" if row.amount >= 0 else f"{row.amount}"
                line = f"`{row.timestamp.strftime('%Y-%m-%d %H:%M')}` → `{amount_str}`g — *{row.description}*"
                embed.add_field(name="", value=line, inline=False)
        else:
            embed.description = "No transactions to display."

        embed.set_footer(text=f"Page {self.page + 1} / {max(1, (len(self.transactions) + 4) // 5)}")
        return embed

class PrevPageButton(Button):
    def __init__(self, view):
        super().__init__(style=ButtonStyle.secondary, label="Previous")
        self.view_ref = view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id:
            return await interaction.response.send_message("❌ Not your wallet.", ephemeral=True)

        if self.view_ref.page > 0:
            self.view_ref.page -= 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(embed=self.view_ref.get_embed(), view=self.view_ref)

class NextPageButton(Button):
    def __init__(self, view):
        super().__init__(style=ButtonStyle.secondary, label="Next")
        self.view_ref = view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id:
            return await interaction.response.send_message("❌ Not your wallet.", ephemeral=True)

        if (self.view_ref.page + 1) * 5 < len(self.view_ref.transactions):
            self.view_ref.page += 1
        self.view_ref.update_buttons()
        await interaction.response.edit_message(embed=self.view_ref.get_embed(), view=self.view_ref)

class Wallet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="wallet", description="💼 Check your gold and recent transactions")
    async def wallet(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        if DEBUG:
            print(f"{WALLET_EMOJI} [DEBUG] Fetching wallet for user {user_id}")

        user_data = get_user_data(user_id)
        if not user_data:
            await interaction.response.send_message("❌ Couldn't retrieve your data.", ephemeral=True)
            return

        gold = user_data.get("gold", 0)

        # Fetch all transactions for paging
        with engine.connect() as conn:
            stmt = (
                select(transactions)
                .where(transactions.c.user_id == user_id)
                .order_by(desc(transactions.c.timestamp))
            )
            all_results = conn.execute(stmt).fetchall()

        # Initial wallet embed
        main_embed = Embed(
            title=f"{WALLET_EMOJI} Your Wallet",
            description=f"**Gold:** {gold:,} 💰\n\nClick below to view your recent transactions.",
            color=discord.Color.from_rgb(0, 0, 0)
        )

        # Button to open transaction view
        async def show_transactions_callback(interaction):
            view = TransactionView(user_id, all_results)
            await interaction.response.edit_message(embed=view.get_embed(), view=view)

        view = View()
        show_button = Button(label="View Transactions", style=ButtonStyle.primary)
        show_button.callback = show_transactions_callback
        view.add_item(show_button)

        await interaction.response.send_message(embed=main_embed, view=view)

async def setup(bot):
    await bot.add_cog(Wallet(bot))