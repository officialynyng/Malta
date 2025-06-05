import random
from cogs.chat_modulations.modules.kingdom_weather.region_timezone import get_region_hour

import json
import random

ALL_REGIONS = [
    "Fortress of Mdina",
    "Harbor of Birgu",
    "Citadel of Valletta",
    "Isle of Gozo",
    "Northern Slopes of Mellieħa"
]

def readable_duration(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{sec}s")
    return " ".join(parts)

def pick_region() -> str:
    """
    Randomly selects a region from regions.json.
    """
    with open("cogs/chat_modulations/modules/kingdom_weather/regions/regions.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return random.choice(data["regions"])

def get_time_of_day_label(region: str) -> str:
    hour = get_region_hour(region)

    if 5 <= hour < 7:
        return "dawn"
    elif 7 <= hour < 12:
        return "morning"
    elif 12 <= hour < 15:
        return "early afternoon"
    elif 15 <= hour < 18:
        return "late afternoon"
    elif 18 <= hour < 20:
        return "early evening"
    elif 20 <= hour < 23:
        return "nightfall"
    else:
        return "deep night"
