from cogs.chat_modulations.modules.kingdom_weather.weather_generator import generate_weather_for_region
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime

def generate_forecast_for_region(session, region):
    real_weather = generate_weather_for_region(session, region)
    malta_dt = get_malta_datetime()
    
    # Add speculative forecast data
    forecast_data = {
        **real_weather,
        "trend": "Stable",  # TODO: logic later
        "change_chance": "Low",  # TODO: probabilistic model later
        "time_label": "late afternoon",  # optional logic
        "region_time": malta_dt.strftime("%H:%M"),
        "confidence": "Moderate",
        "persistence_note": None  # or logic to simulate
    }

    return forecast_data
