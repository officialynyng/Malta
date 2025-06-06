# malta_time_logger.py

import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import insert, select, delete, func
from sqlalchemy.orm import Session

from cogs.exp_config import engine
from cogs.database.malta_time.malta_time_table import malta_time_table

def log_malta_time(
    malta_time: datetime.date,
    malta_time_str: str,
    malta_hour: int,
    season: str,
    region: str = None,
    notes: str = None,
    generated_by: str = "auto"
):
    now = datetime.datetime.now(tz=ZoneInfo("America/Chicago"))
    with Session(engine) as session:
        # ✅ Insert the new row
        insert_stmt = insert(malta_time_table).values(
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

        # ✅ If more than 100, delete the oldest entries
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

