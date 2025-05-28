import time
import random
import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands, tasks
from sqlalchemy import select, insert, update, func
from datetime import datetime
import pytz

from cogs.exp_utils import get_user_data, update_user_gold
from cogs.exp_config import engine, EXP_CHANNEL_ID
from cogs.database.lottery_entries_table import lottery_entries


DEBUG = True
TICKET_COST = 100
MAX_TICKETS = 10000

CENTRAL_TZ = pytz.timezone("America/Chicago")
DRAW_WEEKDAY = 6  # Sunday
DRAW_HOUR = 18    # 6 PM CST

def get_central_now():
    return datetime.now(CENTRAL_TZ)

class LotteryGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.run_lottery_check.start()

    def cog_unload(self):
        self.run_lottery_check.cancel()

    @app_commands.command(name="lottery", description="🎟️ Buy tickets for the weekly lottery (100 gold each)")
    @app_commands.describe(amount="How many tickets you want to buy (1–99)")
    async def buy_tickets(self, interaction: Interaction, amount: int):
        user_id = interaction.user.id
        username = interaction.user.display_name

        if amount <= 0 or amount > MAX_TICKETS:
            await interaction.response.send_message(f"❌ Invalid amount. Enter between 1 and {MAX_TICKETS}.", ephemeral=True)
            return

        user_data = get_user_data(user_id)
        if not user_data:
            await interaction.response.send_message("❌ User not found in database.", ephemeral=True)
            return

        total_cost = amount * TICKET_COST
        if user_data["gold"] < total_cost:
            await interaction.response.send_message(f"❌ Not enough gold. You need {total_cost} gold.", ephemeral=True)
            return

        new_gold = user_data["gold"] - total_cost
        update_user_gold(user_id, new_gold)

        with engine.begin() as conn:
            for _ in range(amount):
                conn.execute(insert(lottery_entries).values(
                    user_id=user_id,
                    user_name=username,
                    gold_spent=TICKET_COST,
                    winnings=0,
                    timestamp=int(time.time())
                ))

        exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            await exp_channel.send(f"🎟️ **{username}** entered the weekly lottery with **{amount} tickets** (💰 {total_cost} gold)!")

        await interaction.response.send_message(f"🎟️ Bought **{amount}** tickets for 💰 {total_cost} gold!", ephemeral=True)

        if DEBUG:
            print(f"🎟️ [DEBUG] {username} ({user_id}) bought {amount} ticket(s) for {total_cost} gold. Remaining gold: {new_gold}")

    @tasks.loop(minutes=10)
    async def run_lottery_check(self):
        now = get_central_now()
        if now.weekday() == DRAW_WEEKDAY and now.hour == DRAW_HOUR and now.minute < 10:
            if DEBUG:
                print(f"🎟️ [DEBUG] Running weekly draw at {now.isoformat()}")
            await self.draw_lottery()

    async def draw_lottery(self):
        with engine.begin() as conn:
            results = conn.execute(select(lottery_entries)).fetchall()
            if not results:
                if DEBUG:
                    print("🎟️ [DEBUG] No entries found for this week's draw.")
                return

            pot = len(results) * TICKET_COST
            winner_entry = random.choice(results)
            winner_id = winner_entry.user_id
            winner_name = winner_entry.user_name

            conn.execute(
                update(lottery_entries)
                .where(lottery_entries.c.user_id == winner_id)
                .values(winnings=pot)
            )

            user_data = get_user_data(winner_id)
            if user_data:
                update_user_gold(winner_id, user_data["gold"] + pot)

            channel = self.bot.get_channel(EXP_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"🎉🎟️ The weekly lottery has concluded!\n"
                    f"💰 **Jackpot**: {pot} gold\n"
                    f"🏆 **Winner**: <@{winner_id}> (**{winner_name}**)\n\n"
                    f"Congratulations! 🎉"
                )

            if DEBUG:
                print(f"🎟️ [DEBUG] Winner: {winner_name} ({winner_id}), Pot: {pot} gold")

async def setup(bot):
    await bot.add_cog(LotteryGroup(bot))
