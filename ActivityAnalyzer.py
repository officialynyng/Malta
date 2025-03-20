import os
import time
import discord
from discord.ext import tasks, commands
import sqlalchemy as db
from sqlalchemy.sql import select

from exp_system import process_user_activity  # assumes function exists in exp_system.py

class ActivityToExpProcessor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = db.create_engine(self.fix_db_url(os.getenv("DATABASE_URL")))
        self.metadata = db.MetaData()
        self.recent_activity = db.Table("recent_activity", self.metadata, autoload_with=self.engine)

        self.cooldown_seconds = 900  # 15 min
        self.guild_id = int(os.getenv("MALTA_GUILD_ID"))
        self.process_recent_activity.start()

    def fix_db_url(self, url):
        return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url

    @tasks.loop(seconds=60)
    async def process_recent_activity(self):
        malta_guild = self.bot.get_guild(self.guild_id)
        if not malta_guild:
            return

        with self.engine.connect() as conn:
            results = conn.execute(select(self.recent_activity)).fetchall()

            for row in results:
                user_id = str(row.user_id)

                member = malta_guild.get_member(int(user_id))
                if not member:
                    # Cleanup: user not in Malta server
                    conn.execute(self.recent_activity.delete().where(self.recent_activity.c.user_id == user_id))
                    continue

                # ✅ Pass user to exp_system for normal processing
                await process_user_activity(user_id, self.bot, conn)

                # Cleanup: processed
                conn.execute(self.recent_activity.delete().where(self.recent_activity.c.user_id == user_id))

async def setup(bot):
    await bot.add_cog(ActivityToExpProcessor(bot))
