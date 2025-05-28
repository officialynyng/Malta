import sqlalchemy as db
from cogs.database.meta import metadata

recent_activity = db.Table(
    "recent_activity", metadata,
    db.Column("user_id", db.BigInteger, primary_key=True),
    db.Column("last_message_ts", db.Float, nullable=True),
)