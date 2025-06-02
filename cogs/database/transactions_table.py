import sqlalchemy as db
from datetime import datetime, timezone, timedelta
from cogs.database.meta import metadata  # assuming you store a shared `metadata` here

# CST = UTC-6
CST = timezone(timedelta(hours=-6))

def now_cst():
    return datetime.now(CST)

transactions = db.Table(
    "transactions",
    metadata,
    db.Column("id", db.Integer, primary_key=True),
    db.Column("user_id", db.BigInteger, index=True),
    db.Column("amount", db.Integer),
    db.Column("type", db.String),         # e.g. 'gamble_win', 'shop_buy'
    db.Column("description", db.String),
    db.Column("timestamp", db.DateTime(timezone=True), default=now_cst),
)

