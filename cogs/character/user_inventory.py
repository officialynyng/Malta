import os
import sqlalchemy as db
from discord.ext import commands
from sqlalchemy.sql import select

class UserInventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG]👤🧩 UserInventoryCog initialized")  # Cog init (🧩 = module piece)

# Load and patch DB URL
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLAlchemy setup
engine = db.create_engine(DATABASE_URL)
metadata = db.MetaData()

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

# Create the table if it doesn't exist
try:
    with engine.connect() as conn:
        metadata.create_all(engine)
        print("[DEBUG]👤📦 user_inventory table ensured in DB.")  # 📦 = inventory/storage
except Exception as e:
    print(f"[ERROR]👤🚨 Failed to create user_inventory table: {e}")  # 🚨 = error/alert

# Setup function for Discord extension loader
async def setup(bot):
    await bot.add_cog(UserInventoryCog(bot))
    print("[DEBUG]👤✅ user_inventory cog loaded")  # ✅ = successful load
