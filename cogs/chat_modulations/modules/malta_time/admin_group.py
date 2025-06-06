import discord
from discord.ext import commands
from discord import app_commands, Interaction
from datetime import time, datetime
from zoneinfo import ZoneInfo
import sqlalchemy as db

from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime
from cogs.database.malta_time.malta_time_table import malta_time_table
from cogs.exp_config import engine


class TimeAdminGroup(commands.GroupCog, name="time"):
    """🔒📅 Debug Malta time system"""

    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="now", description="Show current Malta time (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def time_now(self, interaction: Interaction):
        real_now = datetime.now(tz=ZoneInfo("America/Chicago")).strftime("%A, %B %d, %Y %I:%M %p")
        malta_dt = get_malta_datetime()
        malta_time_str = malta_dt.strftime("%A, %B %d, %Y")
        malta_hour = malta_dt.strftime("%I:%M %p")

        embed = discord.Embed(
            title="📅 Current Malta Time",
            description=f"**Real Time (CST):** {real_now}\n"
                        f"**Malta Date:** {malta_time_str}\n"
                        f"**Malta Hour:** {malta_hour}",
            color=discord.Color.light_grey()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="📊 View Malta time tracking stats (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def time_stats(self, interaction: Interaction):
        with engine.connect() as conn:
            total_rows = conn.execute(db.select(db.func.count()).select_from(malta_time_table)).scalar()
            last_entry = conn.execute(
                db.select(malta_time_table)
                .order_by(malta_time_table.c.id.desc())
                .limit(1)
            ).fetchone()

        if last_entry:
            embed = discord.Embed(
                title="📊 Malta Time Tracker Stats",
                color=discord.Color.dark_teal()
            )
            embed.add_field(name="🗓️ Total Logged Hours", value=str(total_rows), inline=True)
            embed.add_field(name="🗓️ Last Entry Date", value=last_entry["malta_time_str"], inline=True)

            hour_24 = last_entry["malta_hour"]
            hour_formatted = time(hour_24).strftime("%I:%M %p")
            embed.add_field(name="🕗 Last Hour", value=hour_formatted, inline=True)
            embed.add_field(name="🌤️ Last Season", value=last_entry["season"], inline=True)
            if last_entry["region"]:
                embed.add_field(name="📍🏞️ Region", value=last_entry["region"], inline=True)
            if last_entry["notes"]:
                embed.add_field(name="📝 Notes", value=last_entry["notes"], inline=False)
        else:
            embed = discord.Embed(
                title="📊 Malta Time Tracker Stats",
                description="No logs found.",
                color=discord.Color.light_grey()
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TimeAdminGroup(bot))
