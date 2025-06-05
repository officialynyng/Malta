import random
from sqlalchemy.orm import Session
from collections import Counter

from cogs.database.kingdomweather.weather_log_table import weather_log_table


def generate_cloud_condition(session: Session, region: str, temperature_struct: dict):
    temp_c = temperature_struct["temperature_c"]
    descriptor = temperature_struct["descriptor"]
    hour = temperature_struct["hour"]
    season = temperature_struct["season"]

    # Get last 5 entries for regional smoothing
    stmt = weather_log_table.select().where(
        weather_log_table.c.region == region
    ).order_by(weather_log_table.c.timestamp.desc()).limit(5)
    recent_entries = session.execute(stmt).fetchall()

    recent_conditions = [r.cloud_condition for r in recent_entries]
    fog_recent = "fog" in recent_conditions
    overcast_recent = "overcast" in recent_conditions

    # Base cloud pools by season + descriptor + time
    cloud_pool = []

    if season == "summer":
        if descriptor == "🔥 Hot":
            cloud_pool = ["clear", "none", "scattered"]
        elif descriptor == "☀️ Warm":
            cloud_pool = ["clear", "scattered", "cumulus", "cumulonimbus"]
    elif season == "winter":
        cloud_pool = ["stratus", "overcast", "scattered", "nimbostratus"]
        if descriptor in ["🌬️ Cool", "❄️ Cold"] and 4 <= hour <= 9:
            cloud_pool.append("fog")
    elif season == "spring":
        cloud_pool = ["scattered", "cumulus", "stratus", "overcast", "cumulonimbus"]
        if descriptor == "🌬️ Cool" and 5 <= hour <= 9:
            cloud_pool.append("fog")
    elif season == "autumn":
        cloud_pool = ["cumulus", "scattered", "overcast", "stratus", "nimbostratus"]
        if descriptor in ["🌬️ Cool", "❄️ Cold"] and 4 <= hour <= 8:
            cloud_pool.append("fog")

    # Remove fog if conditions are warm or late morning/day
    if descriptor in ["🔥 Hot", "☀️ Warm"] or hour > 10:
        cloud_pool = [c for c in cloud_pool if c != "fog"]

    # Reduce fog if seen recently
    if fog_recent and "fog" in cloud_pool and random.random() < 0.6:
        cloud_pool.remove("fog")

    # Context-aware smoothing
    if recent_conditions:
        last = recent_conditions[0]
        if last == "clear" and "overcast" in cloud_pool and random.random() < 0.5:
            cloud_pool.remove("overcast")
        if last == "clear" and "fog" in cloud_pool and random.random() < 0.7:
            cloud_pool.remove("fog")

    if not cloud_pool:
        cloud_pool = ["clear"]

    cloud_condition = random.choice(cloud_pool)

    # Cloud density and eligible weather conditions
    density = "none"
    eligible_conditions = []
    precipitation_chance = 0.0  # Default no precipitation

    if cloud_condition == "clear" or cloud_condition == "none":
        density = "none"
        eligible_conditions = []
    elif cloud_condition == "scattered":
        density = random.choice(["light", "moderate"])
        eligible_conditions = ["wind"]
    elif cloud_condition == "cumulus":
        density = "moderate"
        eligible_conditions = ["wind", "light rain"]
        precipitation_chance = 0.1 if "light rain" in eligible_conditions else 0.0
    elif cloud_condition == "stratus":
        density = random.choice(["light", "dense"])
        eligible_conditions = ["drizzle", "fog"]
        precipitation_chance = 0.15 if "drizzle" in eligible_conditions else 0.0
    elif cloud_condition == "overcast":
        density = "dense"
        eligible_conditions = ["rain", "fog", "wind"]
        precipitation_chance = 0.25
    elif cloud_condition == "fog":
        density = "dense"
        eligible_conditions = ["fog"]
    elif cloud_condition == "cumulonimbus":
        density = "dense"
        eligible_conditions = ["storm", "lightning", "heavy rain"]
        precipitation_chance = 0.4
    elif cloud_condition == "nimbostratus":
        density = "dense"
        eligible_conditions = ["rain", "storm", "wind"]
        precipitation_chance = 0.35

    # Optional smoothing based on recent storms
    if "storm" in eligible_conditions:
        if any(c in ["cumulonimbus", "nimbostratus"] for c in recent_conditions):
            precipitation_chance += 0.1  # slight increase if stormy recently

    # Clamp between 0–1
    precipitation_chance = round(min(1.0, precipitation_chance), 2)

    return {
        "cloud_condition": cloud_condition,
        "cloud_density": density,
        "eligible_conditions": eligible_conditions,
        "precipitation_chance": precipitation_chance,
    }
