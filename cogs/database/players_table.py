import sqlalchemy as db
from cogs.database.meta import metadata

players = db.Table(
    "players", metadata,
    db.Column("user_id", db.String, primary_key=True),
    db.Column("exp", db.Integer, nullable=False, default=0),
    db.Column("level", db.Integer, nullable=False, default=0),
    db.Column("gold", db.Integer, nullable=False, default=0),
    db.Column("last_message_ts", db.Float, nullable=False, default=0.0),
    db.Column("retirements", db.Integer, nullable=False, default=0),
    db.Column("heirloom_points", db.Integer, nullable=False, default=0),
    db.Column("multiplier", db.Integer, nullable=False, default=0),
    db.Column("daily_multiplier", db.Integer, nullable=False, default=1),
    db.Column("last_multiplier_update", db.Float, nullable=False, default=0.0),
    db.Column("last_title_announce_ts", db.Float, nullable=False, default=0.0),
    db.Column("last_trail_trigger_ts", db.Float, nullable=False, default=0.0),
)