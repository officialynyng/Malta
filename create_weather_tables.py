from cogs.database.meta import metadata
from cogs.exp_config import engine
from cogs.database.weather_ts import weather_ts_table
from cogs.database.weather_log_table import weather_log_table

# This will create both tables if they don't exist
metadata.create_all(engine)
print("✅ weather_ts and weather_log tables created (if missing).")
