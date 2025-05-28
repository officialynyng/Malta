import sqlalchemy as db
from cogs.database.meta import metadata

lottery_entries = db.Table(
    "lottery_entries",
    metadata,
    db.Column("user_id", db.BigInteger, primary_key=True),
    db.Column("tickets", db.Integer, nullable=False, default=0),
)
