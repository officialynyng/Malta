import sqlalchemy as db
from cogs.database.meta import metadata

forecast_ts_table = db.Table(
    "forecast_ts",
    metadata,
    db.Column("key", db.String, primary_key=True),  # "daily", "weekly", etc.
    db.Column("last_post", db.DateTime(timezone=True))
)
