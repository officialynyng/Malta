from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from cogs.database.weather_log_table import weather_log_table
from cogs.database.weather_ts import weather_ts_table
from sqlalchemy.dialects.postgresql import insert as pg_insert

MAX_LOG_ENTRIES = 100

def log_weather_event(
    session: Session,
    region: str,
    temperature: int,
    descriptor: str,
    hour: int,
    season: str,
    cloud_condition: str,
    main_condition: str,
    sub_condition: str = None,
    narrative: str = None,
    triggered_by: str = "auto"
):
    # ✅ Prevent narrative fatigue (duplicate message back-to-back)
    if narrative:
        last_narr_stmt = (
            select(weather_log_table.c.narrative)
            .where(weather_log_table.c.region == region)
            .order_by(weather_log_table.c.timestamp.desc())
            .limit(1)
        )
        last_narrative = session.execute(last_narr_stmt).scalar()
        if last_narrative == narrative:
            print(f"[⚠️] Duplicate narrative for {region}, skipping log.")
            return  # Do not log or commit

    # ✅ Proceed with logging
    insert_stmt = weather_log_table.insert().values(
        region=region,
        temperature=temperature,
        temperature_f=round((temperature * 9 / 5) + 32),
        descriptor=descriptor,
        hour=hour,
        season=season,
        cloud_condition=cloud_condition,
        main_condition=main_condition,
        sub_condition=sub_condition,
        narrative=narrative,
        triggered_by=triggered_by
    )
    session.execute(insert_stmt)
    session.commit()

    _enforce_log_limit(session)

def _enforce_log_limit(session: Session):
    count_stmt = select(func.count()).select_from(weather_log_table)
    total_entries = session.execute(count_stmt).scalar()

    if total_entries > MAX_LOG_ENTRIES:
        excess = total_entries - MAX_LOG_ENTRIES

        delete_stmt = delete(weather_log_table).where(
            weather_log_table.c.id.in_(
                select(weather_log_table.c.id)
                .order_by(weather_log_table.c.timestamp.asc())
                .limit(excess)
            )
        )
        session.execute(delete_stmt)
        session.commit()


def update_weather_timestamp(session: Session, region: str, timestamp: float):
    stmt = pg_insert(weather_ts_table).values(
        key=region,
        value=timestamp
    ).on_conflict_do_update(
        index_elements=["key"],
        set_={"value": timestamp}
    )
    session.execute(stmt)
    session.commit()

def get_last_weather_timestamp(session: Session, region: str) -> float:
    stmt = select(weather_ts_table.c.value).where(weather_ts_table.c.key == region)
    result = session.execute(stmt).scalar()
    return result or 0.0

def get_last_weather_narrative(session: Session, region: str) -> str:
    stmt = (
        select(weather_log_table.c.narrative)
        .where(weather_log_table.c.region == region)
        .where(weather_log_table.c.narrative.isnot(None))
        .order_by(weather_log_table.c.timestamp.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar()
