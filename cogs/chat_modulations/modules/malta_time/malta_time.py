from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Malta time settings
REAL_START_DATE = datetime(2025, 6, 5, tzinfo=ZoneInfo("America/Chicago"))
MALTA_START_DATE = datetime(1372, 6, 3, tzinfo=ZoneInfo("Europe/Malta"))
MALTA_DAY_DURATION = timedelta(days=2)

def get_malta_datetime(now: datetime = None) -> datetime:
    """Return the current Malta datetime based on real time progression."""
    if now is None:
        now = datetime.now(tz=ZoneInfo("America/Chicago"))
    elapsed = now - REAL_START_DATE
    malta_days = elapsed.total_seconds() / MALTA_DAY_DURATION.total_seconds()
    return MALTA_START_DATE + timedelta(days=malta_days)

def get_malta_datetime_string() -> str:
    """Return a formatted Malta date string, e.g., 'Wednesday, June 3, 1372'."""
    malta_dt = get_malta_datetime()
    return malta_dt.strftime("%A, %B %d, %Y")