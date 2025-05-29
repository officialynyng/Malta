import sqlalchemy as db
from cogs.database.meta import metadata

lottery_history = db.Table(
    "lottery_history", metadata,
    db.Column("draw_id", db.Integer, primary_key=True, autoincrement=True),
    db.Column("draw_time", db.BigInteger, nullable=False),           # UNIX timestamp
    db.Column("winner_id", db.BigInteger, nullable=False),
    db.Column("winner_name", db.String, nullable=False),
    db.Column("jackpot", db.Integer, nullable=False),
    db.Column("tickets_sold", db.Integer, nullable=False)
)