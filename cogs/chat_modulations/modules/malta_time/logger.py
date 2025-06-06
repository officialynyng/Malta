# malta_time_logger.py

from datetime import date
from zoneinfo import ZoneInfo
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func

from cogs.exp_config import engine
from cogs.database.malta_time.malta_time_table import malta_time_table
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime

def log_malta_time(
    malta_time: date,
    malta_time_str: str,
    malta_hour: int,
    season: str,
    region: str = None,
    notes: str = None,
    generated_by: str = "auto"
):
    now = get_malta_datetime()  # ✅ Use Malta time, not Chicago time

    with Session(engine) as session:
        # ✅ Insert the new row
        insert_stmt = pg_insert(malta_time_table).values(
            real_ts=now,
            malta_time=malta_time,
            malta_time_str=malta_time_str,
            malta_hour=malta_hour,
            season=season,
            region=region,
            notes=notes,
            generated_by=generated_by
        )
        session.execute(insert_stmt)

        # ✅ Count total rows
        total_rows = session.scalar(select(func.count()).select_from(malta_time_table))

        # ✅ If more than 100, delete oldest
        if total_rows > 100:
            excess = total_rows - 100
            oldest_ids = session.execute(
                select(malta_time_table.c.id)
                .order_by(malta_time_table.c.id.asc())
                .limit(excess)
            ).scalars().all()

            session.execute(
                delete(malta_time_table).where(malta_time_table.c.id.in_(oldest_ids))
            )

        session.commit()
