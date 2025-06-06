# controller.py

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlalchemy as db

from cogs.exp_config import engine
from cogs.database.malta_time.malta_time_table import malta_time_table
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime, get_malta_datetime_string

CHECK_INTERVAL_SECONDS = 3600  # ⏲️ 1 hour real time

async def malta_time_logger_loop():
    while True:
        await log_malta_time_if_new()
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

async def log_malta_time_if_new(force: bool = False):
    # 📅 Current Malta time
    malta_now = get_malta_datetime()
    malta_day_str = malta_now.strftime("%Y-%m-%d")

    with engine.connect() as conn:
        # 🛑 Check if today's Malta time already logged
        query = db.select(malta_time_table).order_by(malta_time_table.c.id.desc()).limit(1)
        result = conn.execute(query).fetchone()

        if result and result["malta_time"].strftime("%Y-%m-%d") == malta_day_str and not force:
            print(f"🛑 Malta time already logged for {malta_day_str}")
            return

        # 🧾 Insert new Malta time entry
        insert_stmt = malta_time_table.insert().values(
            real_ts=datetime.now(tz=ZoneInfo("America/Chicago")),
            malta_time=malta_now.date(),
            malta_time_str=get_malta_datetime_string(),
            malta_hour=int(malta_now.strftime("%H")),
            season=determine_season(malta_now.month),
            region=None,
            notes=None,
            generated_by="auto"
        )

        conn.execute(insert_stmt)
        conn.commit()
        print(f"✅ Logged new Malta time: {malta_day_str}")

def determine_season(month: int) -> str:
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else:
        return "Autumn"
