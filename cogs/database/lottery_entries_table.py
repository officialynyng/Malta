import sqlalchemy as db
from cogs.database.meta import metadata

lottery_entries = db.Table(
    "lottery_entries",
    metadata,
    db.Column("user_id", db.BigInteger, primary_key=True),
    db.Column("user_name", db.String, nullable=False),           # track display name
    db.Column("tickets", db.Integer, nullable=False, default=0), # number of tickets
    db.Column("gold_spent", db.Integer, nullable=False),         # total gold spent on tickets
    db.Column("timestamp", db.BigInteger, nullable=False),       # time of ticket purchase
    db.Column("winnings", db.Integer, nullable=False, default=0) # winnings from this round
)
