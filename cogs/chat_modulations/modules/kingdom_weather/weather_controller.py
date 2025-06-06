import time
import discord
import random
import json
from discord.ext import tasks

from sqlalchemy.orm import Session
from cogs.exp_config import EXP_CHANNEL_ID
from cogs.database.session import get_session
from cogs.database.kingdomweather.weather_ts import weather_ts_table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from cogs.database.kingdomweather.weather_log_table import weather_log_table
from cogs.database.session import get_session
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_logger import get_last_weather_narrative
from cogs.chat_modulations.modules.kingdom_weather.weather_generator import generate_weather_for_region
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime, get_malta_datetime_string
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import get_time_of_day_label, pick_region
from cogs.chat_modulations.modules.kingdom_weather.weather_state_region import get_region_weather_state
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import condition_emojis

# Configurable cooldown per region
WEATHER_COOLDOWN = 1800  # 30 minutes

cloud_visuals = {
    "none": "[     ] clear",
    "light": "[░░░  ] light",
    "scattered": "[░░░░░] scattered",  # ✅ NEW ENTRY
    "moderate": "[▓▓▓░░] moderate",
    "dense": "[█████] heavy"
}


def temperature_descriptor(temp_f: int) -> str:
    if temp_f <= 32:
        return "🥶 Freezing"
    elif temp_f <= 50:
        return "🧊 Cold"
    elif temp_f <= 68:
        return "🌬️ Cool"
    elif temp_f <= 80:
        return "🌤️ Warm"
    elif temp_f <= 90:
        return "🔥 Hot"
    else:
        return "☀️ Scorching"

# Load weather narrative templates
with open("cogs/chat_modulations/modules/kingdom_weather/conditions/conditions.json", "r", encoding="utf-8") as f:
    WEATHER_NARRATIVES = json.load(f)

def get_last_weather_ts(session: Session, region: str) -> float:
    stmt = select(weather_ts_table.c.value).where(weather_ts_table.c.key == region)
    return session.execute(stmt).scalar() or 0.0

def update_weather_ts(session: Session, key: str, now: float):
    stmt = pg_insert(weather_ts_table).values(
        key=key,
        value=now
    ).on_conflict_do_update(
        index_elements=["key"],
        set_={"value": now}
    )
    session.execute(stmt)
    session.commit()

async def post_weather(bot, triggered_by: str = "auto"):
    # Global cooldown check
    COOLDOWN_SECONDS = 600
    with get_session() as session:
        stmt = select(weather_ts_table.c.value).where(weather_ts_table.c.key == "loop_last_run")
        last_loop = session.execute(stmt).scalar() or 0.0

    if triggered_by != "admin" and time.time() - last_loop < COOLDOWN_SECONDS:
        print(f"[⏳] Skipping weather due to global cooldown.")
        return

    region = pick_region()
    now = time.time()

    with get_session() as session:
        last_ts = get_last_weather_ts(session, region)
        if triggered_by != "admin" and now - last_ts < WEATHER_COOLDOWN:
            print(f"[⏳] Skipping weather for {region} due to cooldown.")
            return

        weather = generate_weather_for_region(session, region)
        state = get_region_weather_state(session, region) or {}
        last_main = state.get("main_condition")
        last_updated = state.get("last_updated")

        if isinstance(last_updated, (int, float)) and last_updated > 1000000000:
            elapsed = time.time() - last_updated
        else:
            elapsed = 0  # fallback if last_updated is missing or bad



        if elapsed > 600 and weather["main_condition"] == last_main:
            hours = round(elapsed / 3600, 1)
            persistence_note = f"🧭 Weather has persisted for {hours} hours."
        elif last_main and last_main != weather["main_condition"]:
            persistence_note = f"↪️ Shifted from {last_main} to {weather['main_condition']}."
        else:
            persistence_note = None

        update_weather_ts(session, key=region, now=now)  # per-region tracking
        if triggered_by == "auto":
            update_weather_ts(session, key="loop_last_run", now=now)

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

    malta_dt = get_malta_datetime()
    malta_time_str = get_malta_datetime_string()
    hour = malta_dt.hour

    time_label = get_time_of_day_label()
    region_time = malta_dt.strftime("%H:%M")


    embed = discord.Embed(
        title=f"🛰️ Weather Update – {region}",
        description=narrative,
        color=discord.Color.from_rgb(0, 32, 96)
    )

    emoji = condition_emojis.get(main.lower(), "❓")
    embed.add_field(name="Condition", value=f"{emoji} {main}", inline=True)
    embed.add_field(name="Temp", value=f"{temp}°F - {temperature_descriptor(temp)}", inline=True)
    cloud_density = weather.get("cloud_density", "none")
    cloud_field = cloud_visuals.get(cloud_density, f"[?????] {cloud_density}")
    embed.add_field(name="Clouds", value=cloud_field, inline=True)
    embed.add_field(name="🌧️ Precipitation", value=f"{precip}%", inline=True)
    embed.add_field(name="📅 Malta Time", value=f"{time_label} — {region_time} MT", inline=False)
    if persistence_note:
        embed.description += f"\n\n{persistence_note}"
    embed.set_footer(text=f"• Dynamic Weather System | {malta_time_str}")

    # Send to EXP channel
    channel = bot.get_channel(EXP_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)
        print(f"[✅] Weather update posted to #{channel.name}")
        log_weather_to_db(weather, region, narrative, triggered_by)



        if triggered_by == "admin":
            return embed

    else:
        print("[⚠️] EXP_CHANNEL_ID not found. Cannot post weather.")
        if triggered_by == "admin":
            return embed  # ⬅️ Return even if channel missing

    return None  # Default case


def log_weather_to_db(weather, region, narrative, triggered_by):
    with get_session() as session:
        stmt = weather_log_table.insert().values(
            temperature=weather["temperature"],
            temperature_f=round((weather["temperature"] * 9/5) + 32),
            descriptor=weather["descriptor"],
            hour=weather["hour"],
            season=weather["season"],
            cloud_condition=weather["cloud_condition"],
            main_condition=weather["main_condition"],
            sub_condition=weather.get("sub_condition"),
            region=region,
            narrative=narrative,
            triggered_by=triggered_by
        )
        session.execute(stmt)
        session.commit()
