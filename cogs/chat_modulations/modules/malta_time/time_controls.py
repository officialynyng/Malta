import discord
from discord.ext import commands
from discord import app_commands, Interaction
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from cogs.exp_config import ADMIN_ROLE_ID
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime, MALTA_START_DATE, MALTA_DAY_DURATION, REAL_START_DATE
from cogs.chat_modulations.modules.malta_time.controller import force_update_malta_time

ALLOWED_YEAR_MIN = 1048
ALLOWED_YEAR_MAX = 2025

class TimeControlGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    timectrl_group = app_commands.Group(
        name="timectrl",
        description="🔒🕹️ Malta Time Controls (admin only)"
    )

    @timectrl_group.command(name="set_date", description="📆 Set Malta date manually")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_date(self, interaction: Interaction, year: int, month: int, day: int):
        try:
            new_dt = datetime(year, month, day, tzinfo=ZoneInfo("Europe/Malta"))
        except ValueError:
            await interaction.response.send_message("❌ Invalid date.", ephemeral=True)
            return

        if year < ALLOWED_YEAR_MIN or year > ALLOWED_YEAR_MAX:
            await interaction.response.send_message(
                f"❌ Allowed range is {ALLOWED_YEAR_MIN} to {ALLOWED_YEAR_MAX}.", ephemeral=True
            )
            return

        # Sync real time to align new Malta time with this date
        days_offset = (new_dt - MALTA_START_DATE).days
        new_real_start = datetime.now(tz=ZoneInfo("America/Chicago")) - timedelta(days=days_offset * MALTA_DAY_DURATION.total_seconds() / 86400)

        global REAL_START_DATE
        REAL_START_DATE = new_real_start

        await force_update_malta_time()
        await interaction.response.send_message(f"✅ Malta date set to {new_dt.strftime('%B %d, %Y')}", ephemeral=True)

    @timectrl_group.command(name="advance_days", description="📆⏩ Advance Malta time by X days")
    @app_commands.checks.has_permissions(administrator=True)
    async def advance_days(self, interaction: Interaction, days: int):
        if abs(days) > 999:
            await interaction.response.send_message("❌ Please keep jumps reasonable (< 1000 days).", ephemeral=True)
            return

        current_dt = get_malta_datetime()
        future_dt = current_dt + timedelta(days=days)

        if not (ALLOWED_YEAR_MIN <= future_dt.year <= ALLOWED_YEAR_MAX):
            await interaction.response.send_message(
                f"❌ Resulting year out of range ({ALLOWED_YEAR_MIN}–{ALLOWED_YEAR_MAX}).", ephemeral=True
            )
            return

        global REAL_START_DATE
        now = datetime.now(tz=ZoneInfo("America/Chicago"))
        days_offset = (future_dt - MALTA_START_DATE).days
        REAL_START_DATE = now - timedelta(days=days_offset * MALTA_DAY_DURATION.total_seconds() / 86400)

        await force_update_malta_time()
        await interaction.response.send_message(f"✅ Advanced Malta time to {future_dt.strftime('%B %d, %Y')}", ephemeral=True)

    @timectrl_group.command(name="sync_to_real", description="📆🔁 Sync Malta time to real-world time anchor")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_to_real(self, interaction: Interaction):
        global REAL_START_DATE
        REAL_START_DATE = datetime.now(tz=ZoneInfo("America/Chicago"))
        await force_update_malta_time()
        await interaction.response.send_message("✅ Malta time synced to real-world anchor.", ephemeral=True)

    @timectrl_group.command(name="randomize", description="📆🎲 Set a random Malta date and time")
    @app_commands.checks.has_permissions(administrator=True)
    async def randomize(self, interaction: Interaction):
        import random

        year = random.randint(ALLOWED_YEAR_MIN, ALLOWED_YEAR_MAX)
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # Safe range

        hour = random.randint(0, 23)
        minute = random.randint(0, 59)

        try:
            new_malta_dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Europe/Malta"))
        except ValueError:
            await interaction.response.send_message("❌ Failed to generate a valid date.", ephemeral=True)
            return

        delta_days = (new_malta_dt - MALTA_START_DATE).total_seconds() / 86400
        new_real_start = datetime.now(tz=ZoneInfo("America/Chicago")) - timedelta(days=delta_days * MALTA_DAY_DURATION.total_seconds() / 86400)

        global REAL_START_DATE
        REAL_START_DATE = new_real_start

        await force_update_malta_time()

        embed = discord.Embed(
            title="🎲 Malta Time Randomized!",
            description=f"📅 **{new_malta_dt.strftime('%A, %B %d, %Y')}**\n🕰️ {new_malta_dt.strftime('%I:%M %p')}",
            color=discord.Color.light_grey()
        )
        await interaction.response.send_message(embed=embed)

    


async def setup(bot):
    await bot.add_cog(TimeControlGroup(bot))
