import time
from sqlalchemy import select, insert, update
from cogs.database.kingdomweather.weather_state_region import weather_state_region_table
from cogs.database.session import get_session

def get_region_weather_state(region: str):
    with get_session() as session:
        stmt = select(weather_state_region_table).where(weather_state_region_table.c.region == region)
        row = session.execute(stmt).mappings().first()
        return dict(row) if row else None

def upsert_region_weather_state(region: str, main_condition: str, sub_condition: str = None,
                                 intensity: str = None, duration: int = 1):
    now = time.time()
    with get_session() as session:
        stmt = insert(weather_state_region_table).values(
            region=region,
            main_condition=main_condition,
            sub_condition=sub_condition,
            intensity=intensity,
            duration=duration,
            last_updated=now
        ).on_conflict_do_update(
            index_elements=["region"],
            set_={
                "main_condition": main_condition,
                "sub_condition": sub_condition,
                "intensity": intensity,
                "duration": duration,
                "last_updated": now
            }
        )
        session.execute(stmt)
        session.commit()
