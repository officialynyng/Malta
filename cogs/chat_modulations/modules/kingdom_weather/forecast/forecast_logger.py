from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime
from cogs.database.kingdomweather.forecast_log_table import forecast_log_table
from cogs.exp_config import engine

def log_forecast_to_db(region, forecast, forecast_for_date, triggered_by="auto"):
    with Session(engine) as session:
        malta_now = get_malta_datetime()
        stmt = pg_insert(forecast_log_table).values(
            region=region,
            malta_now = get_malta_datetime(),
            forecast_for=forecast_for_date or malta_now.date(),
            posted_at=malta_now,
            main_condition=forecast["main_condition"],
            sub_condition=forecast.get("sub_condition"),
            temperature=forecast["temperature"],
            temperature_f=round((forecast["temperature"] * 9 / 5) + 32),
            precip_chance=int(forecast.get("precip_chance", 0.0) * 100),
            cloud_density=forecast.get("cloud_density", "unknown"),
            confidence=forecast.get("confidence", "Moderate"),
            trend=forecast.get("trend", "Unknown"),
            triggered_by=triggered_by
        )
        session.execute(stmt)
        session.commit()
