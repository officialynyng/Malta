import time
import discord
from discord.ext import tasks, commands
from sqlalchemy import select

from cogs.exp_background import process_user_activity
from cogs.exp_config import engine
from cogs.database.recent_activity_table import recent_activity

class ActivityToExpProcessor(commands.Cog):
    def __init__(self, bot):
        print("[DEBUG]💬 ActivityToExpProcessor cog initialized.")
        self.bot = bot
        self.cooldown_seconds = 300
        self.guild_id = int(os.getenv("GUILD_ID"))

    async def cog_load(self):
        print("[DEBUG]💬 ActivityToExpProcessor cog fully loaded. Starting task loop...")
        self.process_recent_activity.start()

    @tasks.loop(seconds=300)
    async def process_recent_activity(self):
        print("[DEBUG]💬 ActivityAnalyzer task loop triggered.")
        malta_guild = self.bot.get_guild(self.guild_id)
        if not malta_guild:
            print("[DEBUG]💬❌ Malta guild not found. Skipping.")
            return

        with engine.begin() as conn:
            results = conn.execute(select(recent_activity)).fetchall()
            print(f"[DEBUG]💬☑️ Retrieved {len(results)} activity entries from database.")

            for row in results:
                user_id = str(row.user_id)
                member = malta_guild.get_member(int(user_id))
                if member:
                    try:
                        await process_user_activity(self.bot, user_id)
                        print(f"[DEBUG]💬🗒️🖊️☑️ Entry for user ID {user_id} successfully processed.")
                    except Exception as e:
                        print(f"[ERROR]💬 Failed to process activity for user {user_id}: {e}")
                else:
                    print(f"[DEBUG]💬❌ User ID {user_id} not found in guild. Deleting entry.")

                delete_stmt = recent_activity.delete().where(recent_activity.c.user_id == row.user_id)
                conn.execute(delete_stmt)

async def setup(bot):
    await bot.add_cog(ActivityToExpProcessor(bot))
