import sqlalchemy as db
from cogs.database.meta import metadata

gambling_stats = db.Table(
    "gambling_stats", metadata,
    db.Column("user_id", db.BigInteger, primary_key=True),
    db.Column("total_bets", db.Integer, nullable=False, default=0),
    db.Column("total_won", db.Integer, nullable=False, default=0),
    db.Column("total_lost", db.Integer, nullable=False, default=0),
    db.Column("net_winnings", db.Integer, nullable=False, default=0),
    db.Column("last_gamble_ts", db.BigInteger, nullable=False, default=0),
)
