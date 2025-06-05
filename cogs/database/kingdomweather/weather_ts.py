import sqlalchemy as db
from cogs.database.meta import metadata

weather_ts_table = db.Table(
    "weather_ts",
    metadata,
    db.Column("key", db.String, primary_key=True),
    db.Column("value", db.Float),
)
