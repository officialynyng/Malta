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


players = db.Table(
    "players", metadata,
    db.Column("user_id", db.String, primary_key=True),
    db.Column("exp", db.Integer, nullable=False, default=0),
    db.Column("level", db.Integer, nullable=False, default=0),
    db.Column("gold", db.Integer, nullable=False, default=0),
    db.Column("last_message_ts", db.Float, nullable=False, default=0.0),
    db.Column("retirements", db.Integer, nullable=False, default=0),
    db.Column("heirloom_points", db.Integer, nullable=False, default=0),
    db.Column("multiplier", db.Integer, nullable=False, default=0)  # Add the multiplier column
)

with engine.connect() as conn:
    metadata.create_all(engine)

EXP_COOLDOWN = 600
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

def calculate_multiplier(last_activity_time, current_time, current_multiplier):
    """
    Calculate the new multiplier based on last activity and current time.
    If the user hasn't been active for more than 24 hours, reset their multiplier.
    """
    time_diff = current_time - last_activity_time
    
    # If more than 24 hours have passed, reset the multiplier
    if time_diff >= TIME_DELTA:
        current_multiplier = 0
    
    # Add multiplier tick if activity happened within the last 24 hours (up to MAX_MULTIPLIER)
    if current_multiplier < MAX_MULTIPLIER:
        current_multiplier += 1
    
    return current_multiplier

def get_user_data(user_id):
    # Fetch user data from the database (last activity and current multiplier)
    with engine.connect() as conn:
        result = conn.execute(
            select(players.c.last_message_ts, players.c.multiplier)
            .where(players.c.user_id == user_id)
        )
        
        # Fetch the first row (there should be only one row for the user)
        row = result.fetchone()

        if row:
            # Return the last activity timestamp and multiplier
            return {
                'last_activity': row[0],
                'multiplier': row[1]
            }
        else:
            # Handle the case where the user isn't found in the database
            return None
        

def update_user_data(user_id, new_multiplier, last_activity_time):
    # Update the player's data in the database with the new multiplier and last activity timestamp
    with engine.connect() as conn:
        conn.execute(players.update().where(players.c.user_id == user_id).values(
            multiplier=new_multiplier,
            last_message_ts=last_activity_time
        ))


async def handle_exp_gain(message: discord.Message, level_up_channel_id: int):
    print(f"Handling EXP gain for user: {message.author.id}")  # Debugging line
    if message.author.bot:
        return

    user_id = str(message.author.id)
    current_ts = time.time()

    with engine.connect() as conn:
        result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()
        print(f"Updated user data: {result}")

        if result:
            print(f"User found in DB: {user_id}")  # Debugging line
            print(f"Last message timestamp: {result.last_message_ts}")
            if current_ts - result.last_message_ts < EXP_COOLDOWN:
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
        

            if new_level > result.level:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)
        else:
            print(f"User not found, inserting into DB: {user_id}")  # Debugging line
            multiplier = get_multiplier(0)
            new_level = calculate_level(EXP_PER_TICK)
            conn.execute(players.insert().values(
                user_id=user_id,
                exp=int(EXP_PER_TICK * multiplier),
                gold=int(GOLD_PER_TICK * multiplier),
                level=new_level,
                last_message_ts=current_ts,
                retirements=0,
                heirloom_points=0
            ))
            print(f"Inserting new user {user_id} with EXP: {EXP_PER_TICK * multiplier}, Level: {new_level}")
            conn.commit()

            if new_level > 0:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)

async def on_user_comment(user_id, bot):
    print("[DEBUG] on_user_comment triggered")
    print(f"[DEBUG] EXP_CHANNEL_ID = {EXP_CHANNEL_ID}")
    current_time = int(time.time())  # Current UNIX timestamp
    user_data = get_user_data(user_id)

    if user_data:
        # Calculate the new multiplier
        new_multiplier = calculate_multiplier(user_data['last_activity'], current_time, user_data['multiplier'])

        # Update the player's last activity time and multiplier in the database
        update_user_data(user_id, new_multiplier, current_time)

        exp_channel = bot.get_channel(EXP_CHANNEL_ID)  # Ensure EXP_CHANNEL_ID is defined
        print(f"[DEBUG] exp_channel = {exp_channel}")
        if exp_channel:
            await exp_channel.send(
                f"🏔️ <@{user_id}>'s multiplier updated to **{new_multiplier:.2f}x** due to recent activity."
            )
        else:
            print("Failed to find the EXP channel.")

        print(f"User {user_id}'s new multiplier: {new_multiplier}")
    else:
        print(f"User {user_id} not found in database.")


async def check_and_reset_multiplier(user_id, bot):
    current_time = int(time.time())  # Current UNIX timestamp
    user_data = get_user_data(user_id)

    if user_data:
        # Check if 24 hours have passed since the last activity
        if current_time - user_data['last_activity'] >= TIME_DELTA:
            # Reset the multiplier
            update_user_data(user_id, 0, user_data['last_activity'])
            exp_channel = bot.get_channel(EXP_CHANNEL_ID)  # Ensure you have defined EXP_CHANNEL_ID globally or passed it
            if exp_channel:
                await exp_channel.send(
                    f"🌋 <@{user_id}>'s multiplier has been reset due to inactivity."
                )
            else:
                print("Failed to find the EXP channel.")
            print(f"User {user_id}'s multiplier has been reset due to inactivity.")



async def award_xp_and_gold(user_id, base_xp, base_gold, bot):
    user_data = get_user_data(user_id)
    if user_data:
        multiplier = user_data['multiplier']
        xp_awarded = int(base_xp * multiplier)  # Apply multiplier to base XP
        gold_awarded = int(base_gold * multiplier)  # Apply multiplier to base gold

        # Print to console for debugging
        print(f"Awarded {xp_awarded} XP and {gold_awarded} gold to user <@{user_id}> - Multiplier: {multiplier}")

        # Update the XP and gold in the database
        with engine.connect() as conn:
            update_query = players.update().where(players.c.user_id == user_id).values(
                exp=user_data['exp'] + xp_awarded,
                gold=user_data['gold'] + gold_awarded
            )
            conn.execute(update_query)
            conn.commit()  # Ensure changes are committed to the database

        # Send a message to the designated Discord channel about the XP and gold update
        exp_channel = bot.get_channel(EXP_CHANNEL_ID)  # Ensure you have defined EXP_CHANNEL_ID globally or passed it
        if exp_channel:
            await exp_channel.send(
                f"<@{user_id}> has been awarded ⚡ {xp_awarded} XP and 💰 {gold_awarded} gold. "
                f"Total XP is now ⚡ {user_data['exp'] + xp_awarded}, and total gold is 💰 {user_data['gold'] + gold_awarded}. "
                f"Multiplier applied: ❎ {multiplier}x."
            )
        else:
            print("Failed to connect to Database for User.")




async def announce_level_up(guild: discord.Guild, member: discord.Member, level: int, channel_id: int):
    channel = guild.get_channel(channel_id)
    if channel:
        await exp_channel.send(f"🎆 {member.mention} has reached **Level {level}**.")


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

            print("[DEBUG] Passed checks, handling EXP gain")
            await handle_exp_gain(message, EXP_CHANNEL_ID)

            print("[DEBUG] Updating multiplier")
            await on_user_comment(user_id, self.bot)

            print("[DEBUG] Checking for multiplier reset")
            await check_and_reset_multiplier(user_id, self.bot)

            # Optional: give bonus XP/gold for participation
            print("[DEBUG] Awarding base XP/gold")
            await award_xp_and_gold(user_id, base_xp=0, base_gold=0, bot=self.bot)

        except Exception as e:
            print(f"[ERROR] Exception in on_message: {e}")

###############################
    @commands.Cog.listener()
    async def on_ready(self):
        global exp_channel
        exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)
        print(f"[READY] Bot is online. EXP Channel set to: {exp_channel}")

    @app_commands.command(name="ping", description="Ping the bot to check if it's online.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Ping back from Malta system.")
    

    @app_commands.command(name="retire", description="Retire your character between levels 31-38 for heirloom bonuses.")
    async def retire(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)  # Acknowledge the interaction early

        user_id = str(interaction.user.id)
        exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)  # Ensure EXP_CHANNEL_ID is defined

        with engine.connect() as conn:
            result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()
            if not result:
                if exp_channel:
                    await exp_channel.send("You have no EXP record yet.")
                else:
                    print("EXP channel not found.")
                return

            if result.level < 31 or result.level > 38:
                if exp_channel:
                    await exp_channel.send("You can only retire between levels 31 - 38.")
                return

            if exp_channel:
                await exp_channel.send(
                    f"🛡️ Are you sure you want to retire? You will reset your level, EXP, and gold.\n"
                    f"Type your username (`{interaction.user.name}`) to confirm."
                )
            else:
                print("EXP channel not found.")
                return

            def check(m):
                return m.author == interaction.user and m.content == interaction.user.name

            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
            except:
                if exp_channel:
                    await exp_channel.send("🏰 Retirement cancelled (timeout).")
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


    @app_commands.command(name="stats", description="View your own stats (level, gold, EXP, etc.)")
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



    @app_commands.command(name="profile", description="View another player's profile")
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


    @app_commands.command(name="leaderboard", description="Show top 10 players by generation, level, gold, and EXP.")
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

            leaderboard_text = "**📜 Leaderboard** *(Generation → Level → Gold → EXP)*\n"
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






async def setup(bot):
    print("Loading ExpCommands cog...")
    await bot.add_cog(ExpCommands(bot))
    print("ExpCommands cog loaded!")