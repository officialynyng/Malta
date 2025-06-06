from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select, insert, update
from cogs.exp_config import engine
from cogs.database.kingdomweather.forecast_ts import forecast_ts_table


def get_last_forecast_time(key: str = "daily") -> datetime | None:
    with engine.begin() as conn:
        result = conn.execute(
            select(forecast_ts_table.c.last_post).where(forecast_ts_table.c.key == key)
        )
        row = result.scalar_one_or_none()
        return row


def update_forecast_time(key: str = "daily"):
    now = datetime.now(tz=ZoneInfo("America/Chicago"))
    with engine.begin() as conn:
        insert_stmt = insert(forecast_ts_table).values(key=key, last_post=now)
        update_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={"last_post": now}
        )
        conn.execute(update_stmt)
