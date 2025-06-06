from cogs.chat_modulations.modules.kingdom_weather.weather_generator import generate_weather_for_region
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import get_time_of_day_label
import random

def generate_forecast_for_region(session, region):
    from cogs.database.kingdomweather.weather_log_table import weather_log_table
    from sqlalchemy import select

    # Step 1: Get last real weather
    stmt = select(weather_log_table).where(
        weather_log_table.c.region == region
    ).order_by(weather_log_table.c.timestamp.desc()).limit(1)
    row = session.execute(stmt).mappings().first()

    if not row:
        # Fallback: use raw generation (like weather generator)
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

    # Step 2: Inject mild forecast variation
    base_temp = row["temperature_f"]
    forecast_temp = base_temp + random.randint(-5, 5)

    forecast_data = {
        "main_condition": row["main_condition"],
        "sub_condition": row["sub_condition"],
        "temperature": forecast_temp,
        "cloud_density": row["cloud_condition"],
        "cloud_condition": row["cloud_condition"],
        "precipitation_chance": random.choice([row["precipitation_chance"], 0.0, 0.2]),
        "trend": random.choice(["Stable", "Warming", "Cooling"]),
        "change_chance": random.choice(["Low", "Moderate", "High"]),
        "time_label": get_time_of_day_label(),  # same as post_weather
        "region_time": get_malta_datetime().strftime("%H:%M"),
        "confidence": "Moderate",
        "persistence_note": None
    }

    return forecast_data
