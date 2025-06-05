import sqlalchemy as db
from cogs.database.meta import metadata
from cogs.exp_config import engine

weather_ts_table = db.Table(
    "weather_ts",
    metadata,
    db.Column("key", db.String, primary_key=True),
    db.Column("value", db.Float),
)

# Make sure this gets created when metadata.create_all is run in your app startup
