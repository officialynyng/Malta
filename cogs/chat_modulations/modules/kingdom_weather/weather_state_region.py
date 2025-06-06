import time
from sqlalchemy import select, insert
from cogs.database.kingdomweather.weather_state_region import weather_state_region_table
from cogs.database.session import get_session
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime

def get_region_weather_state(session, region: str):
    stmt = select(weather_state_region_table).where(weather_state_region_table.c.region == region)
    row = session.execute(stmt).mappings().first()
    return dict(row) if row else None

def upsert_region_weather_state(session, region: str, main_condition: str, sub_condition: str = None,
                                 intensity: str = None, duration: int = 1, timestamp: float = None):
    malta_ts = timestamp or get_malta_datetime().timestamp()

    stmt = insert(weather_state_region_table).values(
        region=region,
        main_condition=main_condition,
        sub_condition=sub_condition,
        intensity=intensity,
        duration=duration,
        last_updated=malta_ts
    ).on_conflict_do_update(
        index_elements=["region"],
        set_={
            "main_condition": main_condition,
            "sub_condition": sub_condition,
            "intensity": intensity,
            "duration": duration,
            "last_updated": malta_ts
        }
    )
    session.execute(stmt)
    session.commit()

