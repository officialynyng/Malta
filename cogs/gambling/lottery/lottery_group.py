import time
import random
import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands, tasks
from sqlalchemy import select, insert, update, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

from cogs.exp_utils import get_user_data, update_user_gold
from cogs.gambling.lottery.lottery_menu_UI import LotteryMainView
from cogs.gambling.lottery.lottery_halloffame_UI import HallOfFameView
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
        self.announcement_counters = defaultdict(lambda: {"count": 0, "first_ts": 0, "blocked_until": 0})
        self.last_halloffame_ts = 0
        self.run_lottery_check.start()

    def cog_unload(self):
        self.run_lottery_check.cancel()

    async def build_stats_embed(self, user):
        user_id = user.id
        user_data = get_user_data(user_id)

        if not user_data:
            return Embed(title="❌ User not found", color=discord.Color.blue())

        with engine.begin() as conn:
            total_tickets = conn.execute(select(func.sum(lottery_entries.c.tickets))).scalar_one_or_none() or 0
            user_tickets = conn.execute(
                select(func.sum(lottery_entries.c.tickets))
                .where(lottery_entries.c.user_id == user_id)
            ).scalar_one_or_none() or 0

        odds = (user_tickets / total_tickets * 100) if total_tickets else 0
        jackpot = total_tickets * TICKET_COST

        embed = Embed(title="🎟️ Your Lottery Stats", color=discord.Color.blue())
        embed.add_field(name="Tickets Bought", value=f"**{user_tickets}**", inline=True)
        embed.add_field(name="Current Jackpot", value=f"**{jackpot}** gold", inline=True)
        embed.add_field(name="Your Odds", value=f"{odds:.2f}%", inline=True)
        return embed
    
    async def buy_tickets(self, interaction, amount):
        user_id = interaction.user.id
        user_name = interaction.user.display_name

        # Validation
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be greater than zero.", ephemeral=True)
            return

        user_data = get_user_data(user_id)
        if not user_data:
            await interaction.response.send_message("❌ User not found.", ephemeral=True)
            return

        gold = user_data["gold"]
        ticket_cost = amount * TICKET_COST

        if gold < ticket_cost:
            await interaction.response.send_message(
                f"❌ You need {ticket_cost} gold, but you only have {gold}.", ephemeral=True
            )
            return

        # Subtract gold
        update_user_gold(user_id, gold - ticket_cost)

        # Insert or update lottery_entries
        with engine.begin() as conn:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(lottery_entries).values(
                user_id=user_id,
                user_name=user_name,
                tickets=amount,
                gold_spent=ticket_cost,
                timestamp=int(time.time()),
                winnings=0
            ).on_conflict_do_update(
                index_elements=[lottery_entries.c.user_id],
                set_={
                    "tickets": lottery_entries.c.tickets + amount,
                    "gold_spent": lottery_entries.c.gold_spent + ticket_cost,
                    "timestamp": int(time.time())
                }
            )
            conn.execute(stmt)

        user_id = interaction.user.id
        now = time.time()
        counter = self.announcement_counters[user_id]

        # Reset counter if last buy was more than 20 minutes ago
        if now > counter["blocked_until"]:
            counter["count"] = 0
            counter["first_ts"] = now

        # Block announcements if in cooldown window
        if now < counter["blocked_until"]:
            return  # Skip announcement

        counter["count"] += 1

        if counter["count"] <= 3:
            channel = self.bot.get_channel(EXP_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"🎟️ {interaction.user.mention} just bought **{amount}** ticket{'s' if amount != 1 else ''} for this week's Malta Lottery!"
                )
            # If this is the 3rd announcement, block further ones for 20 minutes
            if counter["count"] == 3:
                counter["blocked_until"] = now + 20 * 60  # 20 minutes
        else:
            # Do nothing, user is now rate limited
            pass

        # Optionally send a silent ephemeral confirmation or update the UI
        # await interaction.followup.send("Tickets bought!", ephemeral=True)

    async def build_leaderboard_embed(self):
        with engine.begin() as conn:
            rows = conn.execute(
                select(lottery_entries.c.user_name, func.sum(lottery_entries.c.tickets).label("total"))
                .group_by(lottery_entries.c.user_name)
                .order_by(func.sum(lottery_entries.c.tickets).desc())
                .limit(10)
            ).fetchall()

        if not rows:
            return Embed(title="No ticket purchases yet.", color=discord.Color.blue())

        desc = "\n".join([f"`{i+1}.` **{row.user_name}** — 🎟️ {row.total}" for i, row in enumerate(rows)])
        embed = Embed(title="🏆 Top Ticket Holders", description=desc, color=discord.Color.purple())
        return embed

    async def build_history_embed(self):
        with engine.begin() as conn:
            rows = conn.execute(
                select(lottery_history.c.draw_time, lottery_history.c.winner_name, lottery_history.c.jackpot)
                .order_by(lottery_history.c.draw_time.desc())
                .limit(5)
            ).fetchall()

        if not rows:
            return Embed(title="❌ No lottery draws yet.", color=discord.Color.blue())

        desc = ""
        for row in rows:
            time_str = datetime.fromtimestamp(row.draw_time, CENTRAL_TZ).strftime("%b %d, %Y %I:%M %p")
            desc += f"**{row.winner_name}** won 💰 **{row.jackpot}** gold — *{time_str}*\n"

        embed = Embed(title="📜 Recent Lottery Winners", description=desc, color=discord.Color.blue())
        return embed

    async def build_nextdraw_embed(self):
        now = get_central_now()
        days_ahead = (DRAW_WEEKDAY - now.weekday()) % 7
        next_draw = (now + timedelta(days=days_ahead)).replace(hour=DRAW_HOUR, minute=0, second=0, microsecond=0)

        time_left = next_draw - now
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes = remainder // 60

        embed = Embed(
            title="🕰️ Next Lottery Draw",
            description=f"Next draw in **{hours} hours, {minutes} minutes**\n(Sunday 6 PM CST)",
            color=discord.Color.blue()
        )
        return embed

    async def build_help_embed(self):
        embed = discord.Embed(
            title="🎟️ How the Malta Lottery Works",
            description=(
                "**Buy Tickets:** Use the **Buy Tickets** button below to purchase entries (100 gold each).\n"
                "**Draw Time:** Every Sunday at 6 PM CST.\n"
                "**Jackpot:** Grows with every ticket bought.\n"
                "**Winner:** One player is randomly chosen based on ticket weight.\n"
                "**Cooldown:** 30s between purchases.\n\n"
                "🏆 Use the buttons to view stats, top holders, winners, draw time, Hall of Fame, and help—all here in this menu!"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Good luck! The next draw might crown you champion. 🎉")
        return embed

    async def build_halloffame_embed(self, scope="all"):
        now = int(time.time())
        if scope == "weekly":
            time_filter = now - 7 * 86400
        elif scope == "monthly":
            time_filter = now - 30 * 86400
        else:
            time_filter = None  # all-time

        with engine.begin() as conn:
            query = select(
                lottery_history.c.winner_name,
                lottery_history.c.winner_id,
                func.sum(lottery_history.c.jackpot).label("total_won"),
                func.count().label("wins"),
                func.sum(lottery_history.c.tickets_sold).label("tickets_in_winning_rounds")
            ).group_by(
                lottery_history.c.winner_id, lottery_history.c.winner_name
            ).order_by(
                func.sum(lottery_history.c.jackpot).desc()
            ).limit(10)

            if time_filter:
                query = query.where(lottery_history.c.draw_time >= time_filter)

            rows = conn.execute(query).fetchall()

        if not rows:
            return Embed(title="❌ No results for this timeframe.", color=discord.Color.blue())

        desc = ""
        for i, row in enumerate(rows):
            desc += (
                f"`{i+1}.` <@{row.winner_id}> (**{row.winner_name}**)\n"
                f" 💰 {row.total_won} gold | 🏆 {row.wins} win(s) | 🎟️ {row.tickets_in_winning_rounds} tickets (in wins)\n"
            )

        titles = {
            "weekly": "🗓️ Weekly",
            "monthly": "📅 Monthly",
            "all": "🏆 All-Time"
        }

        embed = discord.Embed(
            title=f"{titles.get(scope, '🏆')} Malta Lottery Hall of Fame",
            description=desc,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Top 10 gold earners in this timeframe")
        return embed

    @tasks.loop(minutes=60)
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
            weighted_pool = [row for row in results for _ in range(row.tickets)]

            if not weighted_pool:
                if DEBUG:
                    print("🎟️ [DEBUG] No tickets found.")
                return

            winner_entry = random.choice(weighted_pool)
            winner_id = winner_entry.user_id
            winner_name = winner_entry.user_name

            conn.execute(
                update(lottery_entries)
                .where(lottery_entries.c.user_id == winner_id)
                .values(winnings=pot)
            )

            conn.execute(
                insert(lottery_history).values(
                    draw_time=int(get_central_now().timestamp()),
                    winner_id=winner_id,
                    winner_name=winner_name,
                    jackpot=pot,
                    tickets_sold=tickets_sold
                )
            )

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

            conn.execute(lottery_entries.delete())
            if DEBUG:
                print("🎟️ [DEBUG] Lottery entries have been reset.")

            await channel.send("🧹 All lottery entries have been cleared for the next round. Good luck next week!")

@lottery_group.command(name="menu", description="🎟️ Open the full lottery menu")
async def lottery_menu(interaction: Interaction):
    cog = interaction.client.get_cog("LotteryGroup")
    if cog:
        view = LotteryMainView(cog)
        embed = await cog.build_stats_embed(interaction.user)

        await interaction.response.defer()  # Acknowledge silently (no visible response)

        channel = interaction.channel
        await channel.send(embed=embed, view=view)  # Send embed as a new message


async def setup(bot):
    cog = LotteryGroup(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(lottery_group)
    
    # ✅ Register persistent view with the bot so it works after restart
    bot.add_view(LotteryMainView(cog))
    bot.add_view(HallOfFameView(cog))