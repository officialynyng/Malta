import os
import time
import discord
from discord.ext import tasks, commands
import sqlalchemy as db
from sqlalchemy import select
from cogs.exp_background import process_user_activity  # assumes function exists in exp_system.py

class ActivityToExpProcessor(commands.Cog):
    def __init__(self, bot):
        print("[DEBUG] ActivityToExpProcessor cog initialized.")
        self.bot = bot
        self.engine = db.create_engine(self.fix_db_url(os.getenv("DATABASE_URL")))
        self.metadata = db.MetaData()
        self.recent_activity = db.Table("recent_activity", self.metadata, autoload_with=self.engine)
        self.cooldown_seconds = 300  ##<-- Set to 900 For Production
        self.guild_id = int(os.getenv("GUILD_ID"))
    async def cog_load(self):  # ✅ NEW: safer than starting loop in __init__
        print("[DEBUG] ActivityToExpProcessor cog fully loaded. Starting task loop...")
        self.process_recent_activity.start()

    def fix_db_url(self, url):
        return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url

    @tasks.loop(seconds=300) ##<-- Set to 900 For Production
    async def process_recent_activity(self):
        print("[DEBUG] ActivityAnalyzer task loop triggered.")
        print(f"[DEBUG] GUILD_ID being used: {self.guild_id}")
        malta_guild = self.bot.get_guild(self.guild_id)
        if not malta_guild:
            print("[DEBUG] Malta guild not found. Skipping.")
            return

        with self.engine.connect() as conn:
            results = conn.execute(select(self.recent_activity)).fetchall()
            print(f"[DEBUG] Retrieved {len(results)} activity entries from database.")

            for row in results:
                user_id = str(row.user_id)
                print(f"[DEBUG] Processing user ID: {user_id}")

                member = malta_guild.get_member(int(user_id))
                if not member:
                    print(f"[DEBUG] User {user_id} not found in guild. Removing from activity table.")
                    # Cleanup: user not in Malta server
                    conn.execute(self.recent_activity.delete().where(self.recent_activity.c.user_id == user_id))
                    continue

                # ✅ Corrected call to match your wrapper function exactly
                print(f"[DEBUG] User {user_id} is valid. Passing to EXP system.")
                await process_user_activity(self.bot, user_id)

                # Cleanup: processed
                print(f"[DEBUG] Cleaning up user {user_id} from recent_activity.")
                conn.execute(self.recent_activity.delete().where(self.recent_activity.c.user_id == user_id))


async def setup(bot):
    await bot.add_cog(ActivityToExpProcessor(bot))
