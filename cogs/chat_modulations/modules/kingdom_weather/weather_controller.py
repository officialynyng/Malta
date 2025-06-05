import time
import discord
import random
import json
from discord.ext import tasks

from sqlalchemy.orm import Session
from cogs.exp_config import EXP_CHANNEL_ID
from cogs.database.session import get_session
from cogs.database.weather_ts import weather_ts_table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_logger import get_last_weather_narrative
from cogs.chat_modulations.modules.kingdom_weather.weather_generator import generate_weather_for_region
from cogs.chat_modulations.modules.kingdom_weather.region_timezone import get_region_hour, get_region_time_str
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import get_time_of_day_label, pick_region

# Configurable cooldown per region
WEATHER_COOLDOWN = 1800  # 30 minutes

# Load weather narrative templates
with open("cogs/chat_modulations/modules/kingdom_weather/conditions/conditions.json", "r", encoding="utf-8") as f:
    WEATHER_NARRATIVES = json.load(f)

def get_last_weather_ts(session: Session, region: str) -> float:
    stmt = select(weather_ts_table.c.value).where(weather_ts_table.c.key == region)
    return session.execute(stmt).scalar() or 0.0

def update_weather_ts(session: Session, region: str, now: float):
    stmt = pg_insert(weather_ts_table).values(
        key=region,
        value=now
    ).on_conflict_do_update(
        index_elements=["key"],
        set_={"value": now}
    )
    session.execute(stmt)
    session.commit()

async def post_weather(bot, triggered_by: str = "auto"):
    region = pick_region()
    now = time.time()

    with get_session() as session:
        last_ts = get_last_weather_ts(session, region)
        if now - last_ts < WEATHER_COOLDOWN:
            print(f"[⏳] Skipping weather for {region} due to cooldown.")
            return

        weather = generate_weather_for_region(session, region)
        update_weather_ts(session, region, now)

    # Format values
    main = weather["main_condition"]
    sub = weather["sub_condition"]
    temp = round((weather["temperature"] * 9 / 5) + 32)
    precip = int(weather.get("precipitation_chance", 0.0) * 100)

    try:
        # Get last narrative from DB
        with get_session() as session:
            last_narrative = get_last_weather_narrative(session, region)

        # Select pool
        narrative_pool = []
        if sub and sub in WEATHER_NARRATIVES.get(main, {}):
            narrative_pool = WEATHER_NARRATIVES[main][sub]
        if not narrative_pool:
            narrative_pool = WEATHER_NARRATIVES[main]["default"]

        # Remove last narrative if it's in pool (fatigue prevention)
        cleaned_pool = [n for n in narrative_pool if n != last_narrative]

        # If all were the same, fallback to full pool
        chosen = random.choice(cleaned_pool or narrative_pool)
        narrative = chosen.replace("{region}", region)
    except KeyError:
        narrative = f"The weather over {region} is currently {main}."

    hour = get_region_hour(region)
    time_label = get_time_of_day_label(region)
    region_time = get_region_time_str(region)

    embed = discord.Embed(
        title=f"🛰️ Weather Update – {region}",
        description=narrative,
        color=discord.Color.blue()
    )
    embed.add_field(name="Condition", value=main, inline=True)
    embed.add_field(name="Temp", value=f"{temp}°F", inline=True)
    embed.add_field(name="Clouds", value=weather["cloud_condition"], inline=True)
    embed.add_field(name="☔ Precipitation", value=f"{precip}%", inline=True)
    embed.add_field(name="🕰️ Local Time", value=f"{time_label} — {region_time}", inline=False)
    embed.set_footer(text="• Dynamic Weather Generator")

    # Send to EXP channel
    channel = bot.get_channel(EXP_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)
        print(f"[✅] Weather update posted to #{channel.name}")

        if triggered_by == "auto":
            with get_session() as session:
                update_weather_ts(session, "loop_last_run", now)

        if triggered_by == "admin":
            return embed

    else:
        print("[⚠️] EXP_CHANNEL_ID not found. Cannot post weather.")
        if triggered_by == "admin":
            return embed  # ⬅️ Return even if channel missing

    return None  # Default case
