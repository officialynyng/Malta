# cogs/chat_modulations/modules/malta_time/public_time_announcement.py

import asyncio
import discord
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlalchemy as db

from cogs.exp_config import engine, EXP_CHANNEL_ID
from cogs.database.malta_time.malta_time_table import malta_time_table
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime, get_malta_datetime_string

async def post_daily_malta_time(bot):
    """Posts a public Malta time announcement if a new day has started."""
    now = get_malta_datetime()
    malta_day_str = now.strftime("%Y-%m-%d")

    with engine.connect() as conn:
        result = conn.execute(
            db.select(malta_time_table)
            .order_by(malta_time_table.c.id.desc())
            .limit(1)
        ).fetchone()

        if result and result["malta_time"].strftime("%Y-%m-%d") == malta_day_str:
            print(f"🛑 No new Malta day to announce ({malta_day_str})")
            return

    # Embed presentation
    embed = discord.Embed(
        title="📜 A New Day Dawns in the Kingdom of Malta",
        color=discord.Color.light_grey()
    )
    embed.add_field(name="📅 Date", value=get_malta_datetime_string(), inline=False)
    embed.add_field(name="🕗 Hour", value=now.strftime("%I:%M %p"), inline=True)
    embed.add_field(name="🌤️ Season", value=_get_season(now.month), inline=True)
    embed.set_footer(text="Glory to the realm. Time marches ever onward.")

    channel = bot.get_channel(EXP_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)
        print(f"✅ Malta day posted publicly: {malta_day_str}")
    else:
        print("❌ EXP_CHANNEL_ID not found.")

def _get_season(month: int) -> str:
    return (
        "❄️ Winter" if month in [12, 1, 2] else
        "🌱 Spring" if month in [3, 4, 5] else
        "☀️ Summer" if month in [6, 7, 8] else
        "🍂 Autumn"
    )

# 🔁 Startup loop (to be called from your bot’s on_ready)
async def malta_public_day_loop(bot):
    while True:
        await post_daily_malta_time(bot)
        await asyncio.sleep(3600)  # 🔁 every hour
