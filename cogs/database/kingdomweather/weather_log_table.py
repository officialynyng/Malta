import sqlalchemy as db
from cogs.database.meta import metadata

weather_log_table = db.Table(
    "weather_log", metadata,
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("timestamp", db.DateTime(timezone=True), nullable=False, server_default=db.func.now()),

    # Core environmental descriptors
    db.Column("temperature", db.Integer, nullable=False),  # Celsius
    db.Column("temperature_f", db.Integer, nullable=False),  # Fahrenheit
    db.Column("descriptor", db.String, nullable=False),         # ❄️ Cold, ☀️ Warm, etc.
    db.Column("hour", db.Integer, nullable=False),
    db.Column("season", db.String, nullable=False),
    db.Column("persistence_hours", db.Float, nullable=True),

    # Atmospheric features
    db.Column("cloud_condition", db.String, nullable=False),    # overcast, scattered, etc.
    db.Column("main_condition", db.String, nullable=False),     # rain, snow, fog, etc.
    db.Column("sub_condition", db.String, nullable=True),       # light drizzle, foggy mist, etc.

    # Metadata
    db.Column("region", db.String, nullable=False),
    db.Column("narrative", db.Text, nullable=True),
    db.Column("triggered_by", db.String, nullable=False, server_default="auto")
)
