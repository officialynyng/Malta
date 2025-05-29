import time
import random
import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands, tasks
from sqlalchemy import select, insert, update, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime, timedelta
import pytz
import time
from collections import defaultdict

from cogs.exp_utils import get_user_data, update_user_gold
from cogs.exp_config import engine, EXP_CHANNEL_ID
from cogs.database.lottery_entries_table import lottery_entries
from cogs.database.lottery_history_table import lottery_history

lottery_group = app_commands.Group(name="lottery", description="🎟️ Malta's Weekly Lottery")

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
        self.cooldowns = defaultdict(lambda: 0)
        self.run_lottery_check.start()

    def cog_unload(self):
        self.run_lottery_check.cancel()


    @lottery_group.command(name="buy", description="🎟️ - 💰 Buy tickets for the weekly lottery (100 gold each)")
    @app_commands.describe(amount="How many tickets you want to buy")
    async def buy_tickets(self, interaction: Interaction, amount: int):
        user_id = interaction.user.id
        username = interaction.user.display_name
        now = int(time.time())
        if now - self.cooldowns[user_id] < 30:
            remaining = 30 - (now - self.cooldowns[user_id])
            await interaction.response.send_message(
                f"⏳ Please wait **{remaining}** more seconds before buying more tickets.", ephemeral=True
            )
            return

        self.cooldowns[user_id] = now

        if amount <= 0:
            await interaction.response.send_message("❌ You must buy at least 1 ticket.", ephemeral=True)
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
            conn.execute(
                pg_insert(lottery_entries)
                .values(
                    user_id=user_id,
                    user_name=username,
                    tickets=amount,
                    gold_spent=total_cost,
                    winnings=0,
                    timestamp=int(time.time())
                )
                .on_conflict_do_update(
                    index_elements=['user_id'],
                    set_={
                        "tickets": lottery_entries.c.tickets + amount,
                        "gold_spent": lottery_entries.c.gold_spent + total_cost,
                        "timestamp": int(time.time())
                    }
                )
            )


            # Total live stats
            total_tickets = conn.execute(
                select(func.count()).select_from(lottery_entries)
            ).scalar_one_or_none() or 0

            jackpot = total_tickets * TICKET_COST


        if amount >= 0:  # Only announce big purchases
            exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"🎟️ **{username}** bought **{amount}** ticket{'s' if amount > 1 else ''} "
                    f"for 💰 {total_cost} gold!\n"
                    f"💰 Current jackpot: **{jackpot}** gold with **{total_tickets}** total tickets sold!"
                )

        await interaction.response.send_message(f"🎟️ Bought **{amount}** tickets for 💰 {total_cost} gold!", ephemeral=True)

        if DEBUG:
            print(f"🎟️ [DEBUG] {username} ({user_id}) bought {amount} ticket(s) for {total_cost} gold. Remaining gold: {new_gold}")
    
    ##
    @lottery_group.command(name="stats", description="🎟️ - 📊 View your current ticket count, jackpot, and odds")
    async def lottery_stats(self, interaction: Interaction):
        user_id = interaction.user.id
        user_data = get_user_data(user_id)

        if not user_data:
            await interaction.response.send_message("❌ Could not fetch user data.", ephemeral=True)
            return

        with engine.begin() as conn:
            total_tickets = conn.execute(select(func.sum(lottery_entries.c.tickets))).scalar_one_or_none() or 0
            user_tickets = conn.execute(
                select(func.sum(lottery_entries.c.tickets))
                .where(lottery_entries.c.user_id == user_id)
            ).scalar_one_or_none() or 0

        odds = (user_tickets / total_tickets * 100) if total_tickets else 0
        jackpot = total_tickets * TICKET_COST

        embed = Embed(title="🎟️ Your Lottery Stats", color=discord.Color.gold())
        embed.add_field(name="Tickets Bought", value=f"**{user_tickets}**", inline=True)
        embed.add_field(name="Current Jackpot", value=f"**{jackpot}** gold", inline=True)
        embed.add_field(name="Your Odds", value=f"{odds:.2f}%", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    ##
    @lottery_group.command(name="leaderboard", description="🎟️ - 🏆 See who holds the most tickets this round")
    async def lottery_leaderboard(self, interaction: Interaction):
        with engine.begin() as conn:
            rows = conn.execute(
                select(lottery_entries.c.user_name, func.sum(lottery_entries.c.tickets).label("total"))
                .group_by(lottery_entries.c.user_name)
                .order_by(func.sum(lottery_entries.c.tickets).desc())
                .limit(10)
            ).fetchall()

        if not rows:
            await interaction.response.send_message("No tickets have been purchased yet.", ephemeral=True)
            return

        desc = "\n".join([f"`{i+1}.` **{row.user_name}** — 🎟️ {row.total}" for i, row in enumerate(rows)])
        embed = Embed(title="🏆 Top Ticket Holders", description=desc, color=discord.Color.purple())
        await interaction.response.send_message(embed=embed, ephemeral=False)

    #
    @lottery_group.command(name="history", description="🎟️ - 📜 View the last few lottery winners")
    async def lottery_history_cmd(self, interaction: Interaction):
        with engine.begin() as conn:
            rows = conn.execute(
                select(lottery_history.c.draw_time, lottery_history.c.winner_name, lottery_history.c.jackpot)
                .order_by(lottery_history.c.draw_time.desc())
                .limit(5)
            ).fetchall()

        if not rows:
            await interaction.response.send_message("❌ No lottery draws have been recorded yet.", ephemeral=True)
            return

        desc = ""
        for row in rows:
            time_str = datetime.fromtimestamp(row.draw_time, CENTRAL_TZ).strftime("%b %d, %Y %I:%M %p")
            desc += f"**{row.winner_name}** won 💰 **{row.jackpot}** gold — *{time_str}*\n"

        embed = Embed(title="📜 Recent Lottery Winners", description=desc, color=discord.Color.dark_gold())
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @lottery_group.command(name="nextdraw", description="🎟️ - 🕰️ Time until the next lottery draw")
    async def lottery_nextdraw(self, interaction: Interaction):
        now = get_central_now()
        days_ahead = (DRAW_WEEKDAY - now.weekday()) % 7
        next_draw = (now + timedelta(days=days_ahead)).replace(hour=DRAW_HOUR, minute=0, second=0, microsecond=0)

        time_left = next_draw - now
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes = remainder // 60

        await interaction.response.send_message(
            f"🕰️ Next draw in **{hours} hours, {minutes} minutes** (Sunday 6 PM CST)", ephemeral=True
        )

    @lottery_group.command(name="help", description="🎟️ - ❓ Learn how Malta's weekly lottery works")
    async def lottery_help(self, interaction: Interaction):
        embed = discord.Embed(
            title="🎟️ How the Malta Lottery Works",
            description=(
                "**Buy Tickets:** Use `/lottery buy` to purchase entries (100 gold each).\n"
                "**Draw Time:** Every Sunday at 6 PM CST.\n"
                "**Jackpot:** Grows with every ticket bought.\n"
                "**Winner:** One player is randomly chosen based on ticket weight.\n"
                "**Cooldown:** 30s between purchases.\n\n"
                "🏆 View stats with `/lottery stats`, top holders with `/lottery leaderboard`, "
                "previous winners with `/lottery history`, and next draw time with `/lottery nextdraw`."
            ),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Good luck! The next draw might crown you champion. 🎉")
        await interaction.response.send_message(embed=embed)



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

            tickets_sold = sum(row.tickets for row in results)
            pot = tickets_sold * TICKET_COST
            # Expand entries by ticket count
            weighted_pool = [
                row for row in results for _ in range(row.tickets)
            ]

            if not weighted_pool:
                if DEBUG:
                    print("🎟️ [DEBUG] No tickets found.")
                return

            winner_entry = random.choice(weighted_pool)
            winner_id = winner_entry.user_id
            winner_name = winner_entry.user_name


            # Award winnings
            conn.execute(
                update(lottery_entries)
                .where(lottery_entries.c.user_id == winner_id)
                .values(winnings=pot)
            )

            # Record history
            conn.execute(
                insert(lottery_history).values(
                    draw_time=int(get_central_now().timestamp()),
                    winner_id=winner_id,
                    winner_name=winner_name,
                    jackpot=pot,
                    tickets_sold=tickets_sold
                )
            )

            # Update user's gold
            user_data = get_user_data(winner_id)
            if user_data:
                update_user_gold(winner_id, user_data["gold"] + pot)

            channel = self.bot.get_channel(EXP_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"# 🎉🎟️ The weekly lottery has concluded!\n"
                    f"## 💰 **Jackpot**: {pot} gold\n"
                    f"🏆 **Winner**: <@{winner_id}> (**{winner_name}**)\n\n"
                    f"Congratulations! 🎉"
                )

            if DEBUG:
                print(f"🎟️ [DEBUG] Winner: {winner_name} ({winner_id}), Pot: {pot} gold")

            # Clear all lottery entries after the draw
            conn.execute(lottery_entries.delete())
            if DEBUG:
                print("🎟️ [DEBUG] Lottery entries have been reset.")

            # Announce reset in Discord
            await channel.send("🧹 All lottery entries have been cleared for the next round. Good luck next week!")

async def setup(bot):
    await bot.add_cog(LotteryGroup(bot))
    bot.tree.add_command(lottery_group)
