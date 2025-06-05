from datetime import datetime
from zoneinfo import ZoneInfo

# Define region-to-timezone mappings
REGION_TIMEZONES = {
    "Fortress of Mdina": "Europe/Malta",
    "Harbor of Birgu": "Europe/Malta",
    "Citadel of Valletta": "Europe/Malta",
    "Isle of Gozo": "Europe/Malta",
    "Northern Slopes of Mellieħa": "Europe/Malta",
}

def get_region_hour(region: str) -> int:
    """
    Returns the current hour in the given region's timezone.
    Defaults to Malta if region is unknown.
    """
    tz_name = REGION_TIMEZONES.get(region, "Europe/Malta")
    return datetime.now(ZoneInfo(tz_name)).hour

def get_region_time_str(region: str) -> str:
    """
    Returns the time string (HH:MM) for the region.
    """
    tz_name = REGION_TIMEZONES.get(region, "Europe/Malta")
    return datetime.now(ZoneInfo(tz_name)).strftime("%H:%M")

def get_region_month(region: str) -> int:
    """
    Returns the current month (1–12) for the given region.
    """
    tz_name = REGION_TIMEZONES.get(region, "Europe/Malta")
    return datetime.now(ZoneInfo(tz_name)).month

def get_region_timestamp(region: str) -> int:
    tz_name = REGION_TIMEZONES.get(region, "Europe/Malta")
    return int(datetime.now(ZoneInfo(tz_name)).timestamp())