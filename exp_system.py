import discord
import os
import time
import math
from discord.ext import commands
from discord import app_commands
import sqlalchemy as db
from sqlalchemy.sql import select

EXP_CHANNEL_ID = int(os.getenv("EXP_CHANNEL_ID"))
print(f"[DEBUG] EXP_CHANNEL_ID loaded as: {EXP_CHANNEL_ID}")
DATABASE_URL = os.getenv("DATABASE_URL")
# Patch the URL so SQLAlchemy accepts it
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
MAX_MULTIPLIER = 5  # Max multiplier level
TIME_DELTA = 86400  # 24 hours in seconds (time threshold for activity)
engine = db.create_engine(DATABASE_URL)
metadata = db.MetaData()

exp_channel = None  # Global placeholder
last_leaderboard_timestamp = 0

#
players = db.Table(
    "players", metadata,
    db.Column("user_id", db.String, primary_key=True),
    db.Column("exp", db.Integer, nullable=False, default=0),
    db.Column("level", db.Integer, nullable=False, default=0),
    db.Column("gold", db.Integer, nullable=False, default=0),
    db.Column("last_message_ts", db.Float, nullable=False, default=0.0),
    db.Column("retirements", db.Integer, nullable=False, default=0),
    db.Column("heirloom_points", db.Integer, nullable=False, default=0),
    db.Column("multiplier", db.Integer, nullable=False, default=0),  # Add the multiplier column
    db.Column("daily_multiplier", db.Integer, nullable=False, default=1)
)

with engine.connect() as conn:
    metadata.create_all(engine)

EXP_COOLDOWN = 1800
EXP_PER_TICK = 10
GOLD_PER_TICK = 5
LEVEL_CAP = 38
BASE_EXP_SCALE = 100

def get_multiplier(retirements: int) -> float:
    return min(1 + 0.03 * retirements, 1.48)

def calculate_level(exp: int) -> int:
    return min(int((exp / BASE_EXP_SCALE) ** 0.75), LEVEL_CAP)

def get_heirloom_points(level: int) -> int:
    if 31 <= level <= 38:
        return 2 ** (level - 31)
    return 0

def calculate_multiplier(last_activity_time, current_time, current_daily_multiplier):
    """
    Calculate the new daily multiplier based on last activity and current time.
    If the user hasn't been active for more than 24 hours, reset their daily multiplier.
    """
    time_diff = current_time - last_activity_time

    if time_diff >= TIME_DELTA:
        current_daily_multiplier = 1  # Reset to 1 if more than 24 hours have passed
    else:
        if current_daily_multiplier < MAX_MULTIPLIER:
            current_daily_multiplier += 1  # Increment daily multiplier
    
    return current_daily_multiplier

def get_user_data(user_id):
    with engine.connect() as conn:
        # Correct usage for SQLAlchemy 1.4+
        stmt = select(
            players.c.last_message_ts,
            players.c.multiplier,
            players.c.daily_multiplier
        ).where(players.c.user_id == user_id)

        result = conn.execute(stmt)
        row = result.fetchone()

        if row:
            return {
                'last_activity': row[0],
                'retirement_multiplier': row[1],
                'daily_multiplier': row[2]
            }
        else:
            return Nonee
        

def update_user_data(user_id, new_retirement_multiplier, new_daily_multiplier, last_activity_time):
    # Update the player's data in the database with new multipliers and last activity timestamp
    with engine.connect() as conn:
        conn.execute(players.update().where(players.c.user_id == user_id).values(
            multiplier=new_retirement_multiplier,  # Update retirement multiplier
            daily_multiplier=new_daily_multiplier,  # Update daily multiplier
            last_message_ts=last_activity_time
        ))


async def handle_exp_gain(message: discord.Message, level_up_channel_id: int):
    print(f"Handling EXP gain for user: {message.author.id}")
    if message.author.bot:
        return

    user_id = str(message.author.id)
    current_ts = time.time()

    with engine.connect() as conn:
        result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

        if result:
            cooldown_remaining = current_ts - result.last_message_ts
            if cooldown_remaining < EXP_COOLDOWN:
                print(f"[DEBUG] EXP cooldown active for user {user_id}: {EXP_COOLDOWN - cooldown_remaining:.2f} seconds remaining.")
                return

            multiplier = get_multiplier(result.retirements)
            gained_exp = int(EXP_PER_TICK * multiplier)
            gained_gold = int(GOLD_PER_TICK * multiplier)
            total_exp = result.exp + gained_exp
            new_level = calculate_level(total_exp)

            if result.level >= LEVEL_CAP:
                total_exp = result.exp
                new_level = LEVEL_CAP
                gained_exp = 0

            update = players.update().where(players.c.user_id == user_id).values(
                exp=total_exp,
                gold=result.gold + gained_gold,
                last_message_ts=current_ts,
                level=new_level
            )
            conn.execute(update)
            conn.commit()

            exp_channel = message.guild.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"**{message.author.display_name}** gained ⚡ **{gained_exp} EXP** and 💰 **{gained_gold} gold** "
                    f"with a current daily multiplier of 🏔️ **{multiplier:.2f}x**."
                )

            if new_level > result.level:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)
        else:
            multiplier = get_multiplier(0)
            new_level = calculate_level(EXP_PER_TICK)
            gained_exp = int(EXP_PER_TICK * multiplier)
            gained_gold = int(GOLD_PER_TICK * multiplier)

            conn.execute(players.insert().values(
                user_id=user_id,
                exp=gained_exp,
                gold=gained_gold,
                level=new_level,
                last_message_ts=current_ts,
                retirements=0,
                heirloom_points=0
            ))
            conn.commit()

            exp_channel = message.guild.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"**{message.author.display_name}** gained ⚡ **{gained_exp} EXP** and 💰 **{gained_gold} gold** "
                    f"with a current daily multiplier of 🏔️ **{multiplier:.2f}x**."
                )

            if new_level > 0:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)


async def on_user_comment(user_id, bot):
    print("[DEBUG] on_user_comment triggered")
    current_time = int(time.time())
    user_data = get_user_data(user_id)

    if user_data:
        last_activity = user_data['last_activity']
        current_daily_multiplier = user_data['daily_multiplier']
        print(f"[DEBUG] Last activity: {last_activity}, Daily Multiplier before update: {current_daily_multiplier}")

        # Calculate new daily multiplier based on activity
        time_diff = current_time - last_activity

        # Only proceed if at least 24 hours have passed
        if time_diff < TIME_DELTA:
            print(f"[DEBUG] Skipping daily multiplier update for {user_id} — only {time_diff} seconds since last activity.")
            return

        # Otherwise, it's a new day: reset or increment the multiplier
        if time_diff >= TIME_DELTA * 2:
            new_daily_multiplier = 1  # Reset due to missed day(s)
        else:
            new_daily_multiplier = min(current_daily_multiplier + 1, MAX_MULTIPLIER)


        # Update database with the new daily multiplier and the current timestamp
        update_user_data(user_id, user_data['retirement_multiplier'], new_daily_multiplier, current_time)

        # Fetch the channel once and use it for sending messages
        exp_channel = bot.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            await exp_channel.send(
                f"🏔️ <{user_id}>'s daily multiplier updated to **{new_daily_multiplier}x** due to daily posting."
            )
        else:
            print("[ERROR] EXP channel not found.")
    else:
        print(f"[ERROR] User {user_id} not found in database.")

async def check_and_reset_multiplier(user_id, bot):
    current_time = int(time.time())
    user_data = get_user_data(user_id)

    if user_data:
        time_since_last = current_time - user_data['last_activity']
        if time_since_last >= TIME_DELTA:
            # Only reset the daily_multiplier and update the last_message_ts
            update_user_data(user_id, user_data['retirement_multiplier'], 1, current_time)
            exp_channel = bot.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"🌋 <@{user_id}>'s daily multiplier has been reset to 1x due to inactivity."
                )
            else:
                print("Failed to find the EXP channel.")
            print(f"[DEBUG] Daily multiplier reset for {user_id} after {time_since_last} seconds.")
    else:
        print(f"[ERROR] User {user_id} not found in database.")

async def award_xp_and_gold(user_id, base_xp, base_gold, bot):
    user_data = get_user_data(user_id)
    if user_data:
        # Retrieve both multipliers
        retirement_multiplier = user_data['multiplier']  # Retirement multiplier
        daily_multiplier = user_data['daily_multiplier']  # Daily activity multiplier

        # Calculate the total multiplier by multiplying the two multipliers
        total_multiplier = retirement_multiplier * daily_multiplier

        # Apply total_multiplier to base XP and gold
        xp_awarded = int(base_xp * total_multiplier)  # Apply total multiplier to base XP
        gold_awarded = int(base_gold * total_multiplier)  # Apply total multiplier to base gold

        # Print to console for debugging
        print(f"Awarded {xp_awarded} XP and {gold_awarded} gold to user <@{user_id}> - Multiplier: {daily_multiplier}x")

        # Update the XP and gold in the database
        with engine.connect() as conn:
            update_query = players.update().where(players.c.user_id == user_id).values(
                exp=user_data['exp'] + xp_awarded,
                gold=user_data['gold'] + gold_awarded
            )
            conn.execute(update_query)
            conn.commit()  # Ensure changes are committed to the database

                # Send a message to the designated Discord channel about the XP and gold update
        exp_channel = bot.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            await exp_channel.send(
                f"<@{user_id}> has been awarded ⚡ {xp_awarded} XP and 💰 {gold_awarded} gold. "
                f"Total XP is now ⚡ {user_data['exp'] + xp_awarded}, and total gold is 💰 {user_data['gold'] + gold_awarded}. "
                f"Daily Multiplier applied: 🏔️ {daily_multiplier}x, Generational Multiplier applied: 🌌 {retirement_multiplier + 1:.2f}x."
            )
        else:
            print("Failed to connect to Database for User.")


async def announce_level_up(guild: discord.Guild, member: discord.Member, level: int, channel_id: int):
    channel = guild.get_channel(channel_id)
    if channel:
        await exp_channel.send(f"## 🎆 {member.mention} has reached **Level {level}**.")


class ExpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
##############################
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            channel_name = getattr(message.channel, 'name', 'DM or unknown')
            print(f"[DEBUG] Message received in #{channel_name} by {message.author} (channel ID: {message.channel.id})")

            if message.author.bot:
                print("[DEBUG] Ignored bot message")
                return

            user_id = str(message.author.id)

            # Handle EXP + Leveling
            await handle_exp_gain(message, EXP_CHANNEL_ID)

            # 🔒 Multiplier logic - Only update once per 24h (handled internally)
            await on_user_comment(user_id, self.bot)

            # ❌ REMOVE: check_and_reset_multiplier() — that's already baked into on_user_comment now

            # 🔄 Optional passive gain
            # await award_xp_and_gold(user_id, base_xp=0, base_gold=0, bot=self.bot)

        except Exception as e:
            print(f"[ERROR] Exception in on_message: {e}")


    @commands.Cog.listener()
    async def on_ready(self):
        global exp_channel
        exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)
        print(f"[READY] Bot is online. EXP Channel set to: {exp_channel}")

class CRPGGroup(app_commands.Group):
    def __init__(self, bot):
        super().__init__(name="crpg", description="CRPG system commands.")
        self.bot = bot

    @app_commands.command(name="retire", description="⚗️ -  Retire your character between levels 31-38 for heirloom bonuses.")
    async def retire(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)
        exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)  # Ensure EXP_CHANNEL_ID is defined

        with engine.connect() as conn:
            result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

            if not result:
                await interaction.response.send_message(
                    "⚠️ You have no EXP record yet. Start participating to gain experience.",
                    ephemeral=True
                )
                return

            if result.level < 31 or result.level > 38:
                await interaction.response.send_message(
                    "⚠️ You can only retire between levels 31 - 38.", ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"🛡️ Are you sure you want to retire? You will reset your level, EXP, and gold.\n"
                f"Type your username (`{interaction.user.name}`) to confirm.",
                ephemeral=True
            )

            def check(m):
                return m.author == interaction.user and m.content == interaction.user.name

            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await interaction.followup.send("🏰 Retirement cancelled (timeout).", ephemeral=True)
                return


            heirloom_gain = get_heirloom_points(result.level)
            new_retire_count = result.retirements + 1
            new_total_heirlooms = result.heirloom_points + heirloom_gain
            multiplier = get_multiplier(new_retire_count)

            bonus_note = ""
            if new_retire_count > 16:
                bonus_note = "⚖️ Multiplier is capped at 1.48x, but you still can earn heirloom point(s)."

            conn.execute(players.update().where(players.c.user_id == user_id).values(
                exp=0,
                level=0,
                retirements=new_retire_count,
                heirloom_points=new_total_heirlooms
            ))
            conn.commit()

            if exp_channel:
                await exp_channel.send(
                    f"🎖️ {interaction.user.mention} has retired and earned 🪙 **{heirloom_gain} heirloom point(s)**!\n"
                    f"Total retirements: `{new_retire_count}` → Multiplier: `{multiplier:.2f}x`\n"
                    f"All progress reset. Start your journey anew!\n"
                    f"{bonus_note}"
                )


    @app_commands.command(name="stats", description="⚗️ -  View your own stats (level, gold, EXP, etc.)")
    async def stats(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        with engine.connect() as conn:
            query = players.select().where(players.c.user_id == user_id)
            result = conn.execute(query).fetchone()

            if not result:
                await interaction.response.send_message("You have no stats yet.", ephemeral=True)
                return

            level = result.level
            exp = result.exp
            gold = result.gold
            retirements = result.retirements
            heirloom_points = result.heirloom_points

            await interaction.response.send_message(
                f"📜 Stats for **{interaction.user.display_name}'s Profile**\n"
                f"🧬 Level: {level}\n⚡ EXP: {exp}\n💰 Gold: {gold}\n"
                f"🌱 Generation: {retirements}\n🪙 Heirloom Points: {heirloom_points}",
                ephemeral=True
            )



    @app_commands.command(name="profile", description="⚗️ -  View another player's profile")
    @app_commands.describe(user="The user whose profile you want to see")
    async def profile(self, interaction: discord.Interaction, user: discord.User):
        user_id = str(user.id)

        with engine.connect() as conn:
            result = conn.execute(players.select().where(players.c.user_id == user_id)).fetchone()

            if not result:
                await interaction.response.send_message(f"{user.display_name} has no stats yet.", ephemeral=True)
                return

            level = result.level
            exp = result.exp
            gold = result.gold
            retirements = result.retirements
            heirloom_points = result.heirloom_points

            await interaction.response.send_message(
                f"📜 **{user.display_name}'s Profile**\n"
                f"🧬 Level: {level}\n⚡ EXP: {exp}\n💰 Gold: {gold}\n"
                f"🌱 Generation: {retirements}\n🪙 Heirloom Points: {heirloom_points}",
                ephemeral=True
            )


    @app_commands.command(name="leaderboard", description="⚗️ - 📜 Show top 10 players by generation, level, gold, and EXP.")
    async def leaderboard(self, interaction: discord.Interaction):
        global last_leaderboard_timestamp

        now = time.time()
        cooldown_seconds = 600  # 10 minutes

        if now - last_leaderboard_timestamp < cooldown_seconds:
            remaining = int(cooldown_seconds - (now - last_leaderboard_timestamp))
            await interaction.response.send_message(
                f"⏳ Leaderboard is on cooldown. Try again in {remaining} seconds.",
                ephemeral=True
            )
            return

        last_leaderboard_timestamp = now

        exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)

        if not exp_channel:
            await interaction.response.send_message("Please perform this action in #discord-crpg.", ephemeral=True)
            return

        with engine.connect() as conn:
            query = players.select().order_by(
                players.c.retirements.desc(),
                players.c.level.desc(),
                players.c.gold.desc(),
                players.c.exp.desc()
            ).limit(10)
            results = conn.execute(query).fetchall()

            if not results:
                await exp_channel.send("No players on the leaderboard yet.")
                await interaction.response.send_message("Leaderboard posted.", ephemeral=True)
                return

            leaderboard_text = "# 📜 Leaderboard\n"
            for i, result in enumerate(results, start=1):
                user_id = result.user_id
                exp = result.exp
                level = result.level
                gold = result.gold
                retirements = result.retirements
                leaderboard_text += (
                    f"{i}. <@{user_id}> - 🌱 Generation {retirements}, 🧬 Level {level}, 💰 {gold} gold, ⚡ {exp} EXP\n"
                )

            await exp_channel.send(leaderboard_text)
            await interaction.response.send_message("Leaderboard posted in #discord-crpg.", ephemeral=True)

    @app_commands.command(name="cooldown", description="⚗️ - Check how long until your next ⚡ experience & 💰 gold tick.")
    async def cooldown(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_ts = time.time()

        with engine.connect() as conn:
            result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

            if result:
                elapsed_time = current_ts - result.last_message_ts
                remaining_cooldown = EXP_COOLDOWN - elapsed_time

                if remaining_cooldown > 0:
                    minutes, seconds = divmod(int(remaining_cooldown), 60)
                    await interaction.response.send_message(
                        f"⏳ You have **{minutes} minutes & {seconds} seconds** left until your next available ⚡ experience & 💰 gold tick.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "You're ready for your next ⚡ experience & 💰 gold tick.",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "You have no EXP record yet. Start participating to earn ⚡ experience & 💰 gold.",
                    ephemeral=True
                )

    @app_commands.command(name="multipliers", description="⚗️ - Your multiplier information.")
    async def next_multiplier(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_time = int(time.time())
        user_data = get_user_data(user_id)

        if not user_data:
            await interaction.response.send_message("You have no EXP record yet. Start participating to gain experience.", ephemeral=True)
            return

        last_activity = user_data['last_activity']
        daily_multiplier = user_data['daily_multiplier']  # Using the daily multiplier
        retirement_multiplier = user_data['retirement_multiplier']  # Using the retirement multiplier
        time_since_last_activity = current_time - last_activity

        if time_since_last_activity < TIME_DELTA:
            time_until_update = TIME_DELTA - time_since_last_activity
            hours, remainder = divmod(time_until_update, 3600)
            minutes, seconds = divmod(remainder, 60)
            await interaction.response.send_message(
                f"""## Daily: 🏔️ **{daily_multiplier}x**
            ## Generational: 🌌 **{retirement_multiplier + 1:.2f}x**

         Your next daily multiplier update is in __{int(hours)}__ hours, __{int(minutes)}__ minutes, and __{int(seconds)}__ seconds.""",
                ephemeral=True
            )
        else:
            # If more than a day has passed since the last activity, the multiplier can be updated immediately
            await interaction.response.send_message(
                f"""## Current Daily: 🏔️ **{daily_multiplier}x**
            ## Current Generational: 🌌 **{retirement_multiplier + 1:.2f}x**

        Your daily multiplier update is available now. ephemeral=True)"""
            )


async def process_user_activity(bot, user_id):
    guild = bot.get_guild(int(os.getenv("GUILD_ID")))
    member = guild.get_member(int(user_id))

    if member is None or member.bot:
        print(f"[DEBUG] Member {user_id} invalid or bot. Skipping.")
        return

    # Creating a minimal fake message object for existing compatibility
    class FakeMessage:
        def __init__(self, author, guild):
            self.author = author
            self.guild = guild

    fake_message = FakeMessage(author=member, guild=guild)

    # Directly invoke existing complete logic
    await handle_exp_gain(fake_message, EXP_CHANNEL_ID)
    await on_user_comment(user_id, bot)
    await check_and_reset_multiplier(user_id, bot)


async def setup(bot):
    print("Loading ExpCommands cog...")
    await bot.add_cog(ExpCommands(bot))
    crpg_group = CRPGGroup(bot)
    bot.tree.add_command(crpg_group)
    print("ExpCommands cog and CRPGGroup commands loaded!")