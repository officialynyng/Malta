from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import get_time_of_day_label
import random
import json
import os


# Load allowed regions from JSON file
REGION_JSON_PATH = os.path.join(os.path.dirname(__file__), "../regions/region.json")
with open(REGION_JSON_PATH, "r", encoding="utf-8") as f:
    VALID_REGIONS = json.load(f)["regions"]

def infer_precip_chance(main_condition, cloud_density):
    if main_condition in ["storm", "rain"]:
        return 0.8
    elif main_condition in ["drizzle", "fog"]:
        return 0.3
    elif main_condition in ["partly cloudy", "overcast"]:
        if cloud_density == "dense":
            return 0.2
        elif cloud_density == "moderate":
            return 0.1
        else:
            return 0.05
    else:
        return 0.0

CONFIDENCE_WEIGHTS_BY_CONDITION = {
    "clear":         [("High", 0.7), ("Moderate", 0.2), ("Low", 0.1)],
    "partly cloudy": [("High", 0.6), ("Moderate", 0.3), ("Low", 0.1)],
    "overcast":      [("High", 0.5), ("Moderate", 0.4), ("Low", 0.1)],
    "fog":           [("High", 0.3), ("Moderate", 0.5), ("Low", 0.2)],
    "drizzle":       [("High", 0.3), ("Moderate", 0.5), ("Low", 0.2)],
    "rain":          [("High", 0.2), ("Moderate", 0.5), ("Low", 0.3)],
    "storm":         [("High", 0.1), ("Moderate", 0.4), ("Low", 0.5)],
    "wind":          [("High", 0.4), ("Moderate", 0.4), ("Low", 0.2)],
    "Unknown":       [("High", 0.0), ("Moderate", 0.2), ("Low", 0.8)]
}

def generate_forecast_for_region(session, region):
    from cogs.database.kingdomweather.weather_log_table import weather_log_table
    from sqlalchemy import select

    if region not in VALID_REGIONS:
        raise ValueError(f"Region '{region}' is not a valid forecast region.")

    # Step 1: Get last known weather
    stmt = select(weather_log_table).where(
        weather_log_table.c.region == region
    ).order_by(weather_log_table.c.timestamp.desc()).limit(1)
    row = session.execute(stmt).mappings().first()

    if not row:
        return {
            "main_condition": "Unknown",
            "sub_condition": None,
            "temperature": 0,
            "cloud_density": "none",
            "cloud_condition": "clear",
            "precipitation_chance": 0.0,
            "trend": "Unknown",
            "change_chance": "Unknown",
            "time_label": "Unknown time",
            "region_time": "Unknown",
            "confidence": "Low",
            "persistence_note": "No previous data available."
        }

    base_temp = row["temperature_f"]
    forecast_temp = base_temp + random.randint(-5, 5)

    main_condition = row["main_condition"]
    cloud_density = row["cloud_condition"]

    precip = infer_precip_chance(main_condition, cloud_density)
    trend = random.choice(["Stable", "Warming", "Cooling"])
    change_chance = random.choice(["Low", "Moderate", "High"])

    conf_options = CONFIDENCE_WEIGHTS_BY_CONDITION.get(main_condition, CONFIDENCE_WEIGHTS_BY_CONDITION["Unknown"])
    labels, weights = zip(*conf_options)
    confidence = random.choices(labels, weights=weights)[0]

    malta_dt = get_malta_datetime()

    return {
        "main_condition": main_condition,
        "sub_condition": row["sub_condition"],
        "temperature": forecast_temp,
        "cloud_density": cloud_density,
        "cloud_condition": cloud_density,
        "precipitation_chance": precip,
        "trend": trend,
        "change_chance": change_chance,
        "time_label": get_time_of_day_label(),
        "region_time": malta_dt.strftime("%H:%M"),
        "confidence": confidence,
        "persistence_note": None
    }
