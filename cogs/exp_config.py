import os
import sqlalchemy as db
from sqlalchemy.sql import select
from discord.ext import commands

class ExpConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

EXP_CHANNEL_ID = int(os.getenv("EXP_CHANNEL_ID"))
print(f"[DEBUG]🗒️⚡ EXP_CHANNEL_ID loaded as: {EXP_CHANNEL_ID}")
DATABASE_URL = os.getenv("DATABASE_URL")

# Patch the URL so SQLAlchemy accepts it
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

MAX_MULTIPLIER = 5  # Max multiplier level
TIME_DELTA = 86400  # 24 hours in seconds (time threshold for activity)
EXP_COOLDOWN = 1800
EXP_PER_TICK = 10
GOLD_PER_TICK = 5
LEVEL_CAP = 38
BASE_EXP_SCALE = 100

engine = db.create_engine(DATABASE_URL)
metadata = db.MetaData()

exp_channel = None

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

with engine.connect() as conn:
    metadata.create_all(engine)

async def setup(bot):
    await bot.add_cog(ExpConfig(bot))