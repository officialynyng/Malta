import sqlalchemy as db
from cogs.database.meta import metadata

# Define the inventory table
user_inventory = db.Table(
    "user_inventory", metadata,
    db.Column("user_id", db.BigInteger, primary_key=True),
    db.Column("item_id", db.String, primary_key=True),
    db.Column("item_type", db.String, primary_key=True),
    db.Column("acquired_at", db.DateTime, nullable=False, server_default=db.func.now()),
    db.Column("equipped", db.Boolean, nullable=False, server_default=db.text("false")),
    db.Column("slot_number", db.Integer, nullable=True) 
)