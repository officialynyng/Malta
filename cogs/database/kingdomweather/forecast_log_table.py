import sqlalchemy as db
from cogs.database.meta import metadata

forecast_log_table = db.Table(
    "forecast_log", metadata,
    db.Column("id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("region", db.String, nullable=False),
    db.Column("forecast_for", db.Date, nullable=False),  # 🗓️ Date the forecast was made *for*
    db.Column("posted_at", db.DateTime(timezone=True), nullable=False, server_default=db.func.now()),  # 📌 When the forecast was posted
    db.Column("main_condition", db.String, nullable=False),
    db.Column("sub_condition", db.String, nullable=True),
    db.Column("temperature", db.Integer, nullable=False),
    db.Column("temperature_f", db.Integer, nullable=False),
    db.Column("precip_chance", db.Integer, nullable=False),
    db.Column("cloud_density", db.String, nullable=False),
    db.Column("confidence", db.String, nullable=True),  # e.g., Low, Moderate, High
    db.Column("trend", db.String, nullable=True),       # e.g., warming, clearing
    db.Column("triggered_by", db.String, nullable=False, default="auto")
)
