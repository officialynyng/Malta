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
    """Posts a public Malta time announcement reflecting current Malta time."""
    now = get_malta_datetime()  # current Malta datetime
    malta_day_str = now.strftime("%Y-%m-%d")
    hour = now.hour

    with engine.connect() as conn:
        result = conn.execute(
            db.select(malta_time_table)
            .order_by(malta_time_table.c.id.desc())
            .limit(1)
        ).fetchone()

        # Only skip if it's midnight post and already posted today
        if result and result["malta_time"].strftime("%Y-%m-%d") == malta_day_str and hour < 5:
            print(f"🛑 Malta day already announced: {malta_day_str}")
            return

    # 📆 Dynamic message logic based on hour in Malta
    if 5 <= hour < 8:
        title = "🌅 Dawn Breaks Over Malta"
        description = "The horizon blushes with light. A new day begins in the realm."
    elif 8 <= hour < 12:
        title = "🌤️ Morning Light in Malta"
        description = "The kingdom stirs with life as morning settles over its hills."
    elif 12 <= hour < 14:
        title = "🌞 Midday in Malta"
        description = "High noon reigns. The sun casts its full gaze upon the land."
    elif 14 <= hour < 18:
        title = "🌇 Afternoon in the Realm"
        description = "Shadows stretch as Malta leans toward evening."
    elif 18 <= hour < 21:
        title = "🌆 Dusk in the Kingdom"
        description = "Twilight wraps the realm in golden hues."
    elif 21 <= hour or hour < 1:
        title = "🌙 Night Falls in Malta"
        description = "Lanterns glow. The stars oversee a sleeping kingdom."
    else:
        title = "🕯️ The Witching Hours"
        description = "Silence drapes the land. Few dare wander now."

    embed = discord.Embed(title=title, description=description, color=discord.Color.light_grey())
    embed.add_field(name="📅 Date", value=get_malta_datetime_string(), inline=False)
    embed.add_field(name="🕗 Malta Time", value=now.strftime("%I:%M %p"), inline=True)
    embed.add_field(name="🌤️ Season", value=_get_season(now.month), inline=True)
    embed.set_footer(text="Glory to the realm. Time marches ever onward.")

    channel = bot.get_channel(EXP_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)
        print(f"✅ Malta time post sent at Malta hour {hour}: {malta_day_str}")
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

    await bot.wait_until_ready()

    CST = ZoneInfo("America/Chicago")
    posted_today = {"midnight": False, "noon": False}

    while not bot.is_closed():
        now = datetime.now(CST)
        hour = now.hour
        minute = now.minute

        # Reset tracking at 12:00 AM CST
        if hour == 0 and minute < 10:
            posted_today = {"midnight": False, "noon": False}

        # Post after 12:00 AM CST
        if 0 <= hour < 1 and not posted_today["midnight"]:
            await post_daily_malta_time(bot)
            posted_today["midnight"] = True

        # Post after 12:00 PM CST
        if 12 <= hour < 13 and not posted_today["noon"]:
            await post_daily_malta_time(bot)
            posted_today["noon"] = True

        await asyncio.sleep(1800)  # Check every 5 minutes

