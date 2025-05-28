import os
import discord
import sqlalchemy as db
from sqlalchemy.sql import select
from discord.ext import commands

# === Shared Engine and Metadata ===
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = db.create_engine(DATABASE_URL)

# === Load tables AFTER defining shared metadata ===
from cogs.database.meta import metadata
from cogs.database.players_table import players
from cogs.database.user_inventory_table import user_inventory
from cogs.database.recent_activity_table import recent_activity
from cogs.database.gambling_stats_table import gambling_stats
from cogs.database.lottery_entries_table import lottery_entries
from cogs.database.lottery_history_table import lottery_history

# === Constants ===
EXP_CHANNEL_ID = int(os.getenv("EXP_CHANNEL_ID"))
exp_channel = discord.Object(id=EXP_CHANNEL_ID)
print(f"[DEBUG]🗒️⚡ EXP_CHANNEL_ID loaded as: {EXP_CHANNEL_ID}")
MAX_MULTIPLIER = 5
TIME_DELTA = 86400  # 24 hours
EXP_COOLDOWN = 1800  # 30 minutes
EXP_PER_TICK = 10
GOLD_PER_TICK = 5
LEVEL_CAP = 38
BASE_EXP_SCALE = 100

# === Create All Tables ===
with engine.connect() as conn:
    metadata.create_all(engine)

# === Optional Cog Setup ===
class ExpConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(ExpConfig(bot))
