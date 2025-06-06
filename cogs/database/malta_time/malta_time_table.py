import sqlalchemy as db
from cogs.exp_config import engine
from cogs.database.meta import metadata

malta_time_table = db.Table(
    "malta_time",
    metadata,
    db.Column("id", db.Integer, primary_key=True),
    db.Column("real_ts", db.DateTime, nullable=False),
    db.Column("malta_time", db.Date, nullable=False),
    db.Column("malta_time_str", db.String, nullable=False),  # e.g. "Wednesday, June 3, 1372"
    db.Column("malta_hour", db.SmallInteger, nullable=False),
    db.Column("season", db.String, nullable=False),
    db.Column("region", db.String),  # optional — region focus of that day's lore/weather
    db.Column("notes", db.String),   # optional — lore or system remarks
    db.Column("generated_by", db.String, nullable=False, default="auto")
)

# Create the table if it doesn't already exist
metadata.create_all(engine)
