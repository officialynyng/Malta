import random
from cogs.chat_modulations.modules.kingdom_weather.region_timezone import get_region_hour

import json
import random

def pick_region() -> str:
    """
    Randomly selects a region from regions.json.
    """
    with open("cogs/chat_modulations/modules/kingdom_weather/regions/regions.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return random.choice(data["regions"])


def get_time_of_day_label(region: str) -> str:
    hour = get_region_hour(region)
    
    if 5 <= hour < 8:
        return "early morning"
    elif 8 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 20:
        return "evening"
    elif 20 <= hour < 24:
        return "night"
    else:
        return "deep night"
