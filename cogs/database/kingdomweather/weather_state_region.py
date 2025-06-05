import sqlalchemy as db
from cogs.database.meta import metadata

weather_state_region_table = db.Table(
    "weather_state_region", metadata,
    db.Column("region", db.String, primary_key=True),
    db.Column("main_condition", db.String, nullable=False),     # e.g., "rain", "clear"
    db.Column("sub_condition", db.String, nullable=True),       # e.g., "light drizzle"
    db.Column("intensity", db.String, nullable=True),           # e.g., "light", "moderate", "heavy"
    db.Column("duration", db.Integer, nullable=False, default=0),  # ⏱️ in hours
    db.Column("last_updated", db.Float, nullable=False),        # UNIX timestamp
)
