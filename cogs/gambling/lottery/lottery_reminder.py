#to remind to enter lottery.
import discord
import random
import asyncio
from discord.ext import commands, tasks
from cogs.exp_config import EXP_CHANNEL_ID
import pytz
from datetime import datetime, timedelta

DEBUG = True
CENTRAL_TZ = pytz.timezone("America/Chicago")

REMINDER_MESSAGES = [
    "🎟️ Don't forget to grab your lottery tickets!",
    "🎟️ Feeling lucky? The Malta Lottery awaits you!",
    "🎟️ A fortune could be yours. Buy your tickets now!",
    "🎟️ Enter the weekly lottery before it's too late!",
    "🎟️ The draw is near — secure your chance at glory!"
]

REMINDER_DAYS = {0, 2, 4, 5}  # Monday, Wednesday, Friday, Saturday

class LotteryReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lottery_reminder.before_loop(self.wait_until_next_reminder)
        self.lottery_reminder.start()

    def cog_unload(self):
        self.lottery_reminder.cancel()

    @tasks.loop(hours=24)
    async def lottery_reminder(self):
        now = datetime.now(CENTRAL_TZ)
        if now.weekday() not in REMINDER_DAYS:
            if DEBUG:
                print(f"[DEBUG]📆 No reminder today ({now.strftime('%A')})")
            return

        channel = self.bot.get_channel(EXP_CHANNEL_ID)
        if not channel:
            if DEBUG:
                print("[DEBUG]❌ EXP_CHANNEL_ID is invalid.")
            return

        message = random.choice(REMINDER_MESSAGES)

        embed = discord.Embed(
            title="🎟️ WEEKLY LOTTERY REMINDER",
            description="**Use** `/lottery` to enter this week's drawing.\nBig rewards await the lucky winner!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Drawing occurs every Sunday at 6 PM CST. Buy tickets anytime before then!")

        await channel.send(content=message, embed=embed)
        if DEBUG:
            print(f"[DEBUG]✅ Lottery reminder sent at {now}")

    async def wait_until_next_reminder(self):
        await self.bot.wait_until_ready()
        now = datetime.now(CENTRAL_TZ)
        target = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        if DEBUG:
            print(f"[DEBUG]⏳ Waiting {wait_seconds:.0f}s until next reminder at {target}")
        await asyncio.sleep(wait_seconds)

async def setup(bot):
    await bot.add_cog(LotteryReminder(bot))
