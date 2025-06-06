import random
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime


# Seasonal temperature ranges
SEASONAL_TEMP_RANGES = {
    "winter": {"months": [12, 1, 2], "min": 10, "max": 16},
    "spring": {"months": [3, 4, 5], "min": 14, "max": 22},
    "summer": {"months": [6, 7, 8], "min": 22, "max": 32},
    "autumn": {"months": [9, 10, 11], "min": 18, "max": 26},
}

# Time of day adjustments
TIME_OF_DAY_ADJUSTMENTS = {
    "late_night": {"range": (0, 6), "delta": (-5, -2)},
    "morning": {"range": (6, 12), "delta": (-2, 0)},
    "afternoon": {"range": (12, 17), "delta": (0, 3)},
    "evening": {"range": (17, 21), "delta": (-2, 0)},
    "night": {"range": (21, 24), "delta": (-4, -2)},
}

def get_season(month: int) -> str:
    for season, data in SEASONAL_TEMP_RANGES.items():
        if month in data["months"]:
            return season
    return "unknown"

def apply_time_of_day_adjustment(temp: int, hour: int) -> int:
    for tod in TIME_OF_DAY_ADJUSTMENTS.values():
        start, end = tod["range"]
        if start <= hour < end:
            delta = random.randint(tod["delta"][0], tod["delta"][1])
            return temp + delta
    return temp

def get_temperature_descriptor(temp_c: int) -> str:
    if temp_c < 8:
        return "❄️ Cold"
    elif temp_c < 15:
        return "🌬️ Cool"
    elif temp_c < 24:
        return "🌤️ Mild"
    elif temp_c < 30:
        return "☀️ Warm"
    else:
        return "🔥 Hot"

def c_to_f(celsius: int) -> int:
    return round((celsius * 9/5) + 32)

_shared_kingdom_base_temp = {}

def generate_temperature_structured():

    global _shared_kingdom_base_temp

    malta_dt = get_malta_datetime()
    month = malta_dt.month
    hour = malta_dt.hour

    season = get_season(month)
    temp_range = SEASONAL_TEMP_RANGES[season]

    # Generate once per run
    if season not in _shared_kingdom_base_temp:
        _shared_kingdom_base_temp[season] = random.randint(temp_range["min"], temp_range["max"])
    
    kingdom_base = _shared_kingdom_base_temp[season]

    # Add minor regional variance (±1–2°C)
    local_offset = random.choice([-2, -1, 0, 1, 2])
    local_temp = kingdom_base + local_offset

    adjusted_temp = apply_time_of_day_adjustment(local_temp, hour)
    final_temp_c = max(5, min(adjusted_temp, 40))
    final_temp_f = c_to_f(final_temp_c)
    descriptor = get_temperature_descriptor(final_temp_c)

    return {
        "temperature_c": final_temp_c,
        "temperature_f": final_temp_f,
        "season": season,
        "hour": hour,
        "descriptor": descriptor
    }

