import os
import time
import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction, Embed
from sqlalchemy import select, insert, func, update

from cogs.exp_config import engine, EXP_CHANNEL_ID
from cogs.database.lottery_entries_table import lottery_entries
from cogs.exp_utils import get_user_data, update_user_gold

import pytz

CENTRAL_TZ = pytz.timezone("America/Chicago")
TICKET_PRICE = 100
DEBUG = True

class LotteryGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.draw_lottery.start()

    def cog_unload(self):
        self.draw_lottery.cancel()

    def get_next_draw_datetime(self):
        now = datetime.now(CENTRAL_TZ)
        days_ahead = (6 - now.weekday()) % 7  # Sunday
        draw = now + timedelta(days=days_ahead)
        return draw.replace(hour=18, minute=0, second=0, microsecond=0)

    @app_commands.command(name="lottery", description="🎟️ Buy a lottery ticket for 100 gold!")
    async def buy_ticket(self, interaction: Interaction):
        user_id = interaction.user.id
        username = interaction.user.display_name
        now = int(time.time())

        user_data = get_user_data(user_id)
        if not user_data or user_data["gold"] < TICKET_PRICE:
            await interaction.response.send_message("❌ You don't have enough gold to buy a ticket.", ephemeral=True)
            return

        with engine.begin() as conn:
            conn.execute(insert(lottery_entries).values(
                user_id=user_id,
                user_name=username,
                gold_spent=TICKET_PRICE,
                winnings=0,
                timestamp=now
            ))
            update_user_gold(user_id, user_data["gold"] - TICKET_PRICE)

        if DEBUG:
            print(f"🎟️ [DEBUG] {username} ({user_id}) bought a ticket for 100 gold")

        await interaction.response.send_message("🎟️ Ticket purchased for 100 gold! Good luck!", ephemeral=True)

        exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            await exp_channel.send(f"🎟️ **{username}** entered the weekly lottery (100 gold).")

    @tasks.loop(minutes=5)
    async def draw_lottery(self):
        now = datetime.now(CENTRAL_TZ)
        if now.weekday() == 6 and now.hour == 18 and now.minute < 5:  # Sunday 6 PM CST/CDT
            with engine.begin() as conn:
                entries = conn.execute(select(lottery_entries)).fetchall()

                if not entries:
                    if DEBUG:
                        print("🎟️ [DEBUG] No lottery entries this week.")
                    return

                pot = len(entries) * TICKET_PRICE
                winner_entry = random.choice(entries)
                winner_id = winner_entry.user_id
                winner_name = winner_entry.user_name

                conn.execute(
                    update(lottery_entries)
                    .where(lottery_entries.c.user_id == winner_id)
                    .values(winnings=pot)
                )

                user_data = get_user_data(winner_id)
                update_user_gold(winner_id, user_data["gold"] + pot)

                exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)
                if exp_channel:
                    await exp_channel.send(
                        f"🏆🎟️ Weekly Lottery Draw!\n"
                        f"Total Jackpot: 💰 **{pot} gold**\n"
                        f"Winner: 🏅 **{winner_name}** (<@{winner_id}>)\n"
                        f"Congratulations!"
                    )

                if DEBUG:
                    print(f"🎟️ [DEBUG] {winner_name} ({winner_id}) won {pot} gold.")

                # Clear all entries
                conn.execute(lottery_entries.delete())

    @draw_lottery.before_loop
    async def before_draw(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(LotteryGroup(bot))
