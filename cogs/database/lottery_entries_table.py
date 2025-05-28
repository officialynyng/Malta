from sqlalchemy import Table, Column, BigInteger, Integer
from cogs.database.meta import metadata

lottery_entries = Table(
    "lottery_entries",
    metadata,
    Column("user_id", BigInteger, primary_key=True),
    Column("tickets", Integer, nullable=False, default=0),
)