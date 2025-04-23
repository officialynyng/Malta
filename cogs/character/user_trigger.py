import time
import discord
from discord.ext import commands
from sqlalchemy.sql import select, update
from cogs.exp_config import EXP_CHANNEL_ID
from cogs.character.user_inventory import players, user_inventory, engine
from cogs.store.store_utils import get_item_by_id

TRAIL_COOLDOWN_DEFAULT = 1800  # 30 minutes
TITLE_COOLDOWN = 86400         # 24 hours
DEBUG = True

class UserTriggers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = str(message.author.id)

        with engine.begin() as conn:
            stmt = select(players).where(players.c.user_id == user_id)
            row = conn.execute(stmt).fetchone()

        if not row:
            if DEBUG:
                print(f"[DEBUG]👤 No player record found for {user_id}")
            return

        now = time.time()

        # 🎗️ Title announcement
        if now - row.last_title_announce_ts >= TITLE_COOLDOWN:
            if DEBUG:
                print(f"[DEBUG]👑 Cooldown met — triggering title announcement for {user_id}")
            await self.trigger_title_announcement(message, conn, user_id, now)
        else:
            if DEBUG:
                remaining = TITLE_COOLDOWN - (now - row.last_title_announce_ts)
                print(f"[DEBUG]⏳ Title cooldown active for {user_id}: {remaining:.0f}s remaining")

        # ✨ Trail reaction
        await self.trigger_trail_reaction(message, conn, user_id, now, row.last_trail_trigger_ts)

    async def trigger_title_announcement(self, message, conn, user_id, now):
    # Update cooldown timestamp
        conn.execute(
            update(players).where(players.c.user_id == user_id).values(last_title_announce_ts=now)
        )

        # Fetch equipped title
        stmt = select(user_inventory).where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_type == "titles") &
            (user_inventory.c.equipped == True)
        )
        row = conn.execute(stmt).fetchone()

        if not row:
            if DEBUG:
                print(f"[DEBUG]👑 No equipped title for {user_id}")
            return

        title = get_item_by_id(row.item_id)
        if not title:
            if DEBUG:
                print(f"[DEBUG]👑 Could not find title JSON for '{row.item_id}'")
            return

        embed = discord.Embed(
            title=f"☩ {message.author.display_name} now bears the title:",
            description=f"**『 {title['name']} 』**\n{title.get('description', '')}",
            color=discord.Color.dark_gold()
        )
        if title.get("avatar_url"):
            embed.set_image(url=title["avatar_url"])

        channel = message.client.get_channel(EXP_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)
            if DEBUG:
                print(f"[DEBUG]👑 Title embed sent for {user_id}")

    async def trigger_trail_reaction(self, message, conn, user_id, now, last_ts):
        stmt = select(user_inventory).where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_type == "trails") &
            (user_inventory.c.equipped == True)
        )
        row = conn.execute(stmt).fetchone()
        if not row:
            if DEBUG:
                print(f"[DEBUG]✨ No equipped trail found for {user_id}")
            return

        trail = get_item_by_id(row.item_id)
        if not trail:
            if DEBUG:
                print(f"[DEBUG]✨ Trail JSON not found for {row.item_id}")
            return

        cooldown = trail.get("cooldown", TRAIL_COOLDOWN_DEFAULT)
        if now - last_ts < cooldown:
            if DEBUG:
                remaining = cooldown - (now - last_ts)
                print(f"[DEBUG]⏳ Trail '{row.item_id}' still on cooldown ({remaining:.0f}s) for {user_id}")
            return

        conn.execute(
            update(players).where(players.c.user_id == user_id).values(last_trail_trigger_ts=now)
        )

        emoji = trail.get("display", "✨")
        try:
            await message.add_reaction(emoji)
            if DEBUG:
                print(f"[DEBUG]✨ Trail '{row.item_id}' reaction '{emoji}' added for {user_id}")
        except discord.HTTPException as e:
            if DEBUG:
                print(f"[DEBUG]⚠️ Failed to add emoji '{emoji}' for {user_id}: {e}")

async def setup(bot):
    await bot.add_cog(UserTriggers(bot))
