import discord
import os
import time
import math
from MaltaBot import bot
from discord.ext import commands
from discord import app_commands
import sqlalchemy as db
from sqlalchemy.sql import select

EXP_CHANNEL_ID = int(os.getenv("EXP_CHANNEL_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")
MAX_MULTIPLIER = 5  # Max multiplier level
TIME_DELTA = 86400  # 24 hours in seconds (time threshold for activity)
engine = db.create_engine(DATABASE_URL)
metadata = db.MetaData()

exp_channel = None  # Global placeholder

@bot.event
async def on_ready():
    global exp_channel
    exp_channel = bot.get_channel(EXP_CHANNEL_ID)
    print(f"[READY] Bot is online. EXP Channel set to: {exp_channel}")

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
    with db.engine.connect() as conn:
        result = conn.execute(select([players.c.last_message_ts, players.c.multiplier])
                              .where(players.c.user_id == user_id))
        
        # Fetch the first row (there should be only one row for the user)
        row = result.fetchone()

        if row:
            # Return the last activity timestamp and multiplier
            return {
                'last_activity': row['last_message_ts'],
                'multiplier': row['multiplier']
            }
        else:
            # Handle the case where the user isn't found in the database
            return None

def update_user_data(user_id, new_multiplier, last_activity_time):
    # Update the player's data in the database with the new multiplier and last activity timestamp
    with db.engine.connect() as conn:
        conn.execute(players.update().where(players.c.user_id == user_id).values(
            multiplier=new_multiplier,
            last_message_ts=last_activity_time
        ))

async def handle_exp_gain(message: discord.Message, level_up_channel_id: int):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    current_ts = time.time()

    with engine.connect() as conn:
        result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

        if result:
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

            if new_level > result.level:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)
        else:
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
            if new_level > 0:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)

def on_user_comment(user_id):
    current_time = int(time.time())  # Current UNIX timestamp
    user_data = get_user_data(user_id)

    if user_data:
        # Calculate the new multiplier
        new_multiplier = calculate_multiplier(user_data['last_activity'], current_time, user_data['multiplier'])

        # Update the player's last activity time and multiplier in the database
        update_user_data(user_id, new_multiplier, current_time)

        print(f"User {user_id}'s new multiplier: {new_multiplier}")
    else:
        print(f"User {user_id} not found in database.")

def check_and_reset_multiplier(user_id):
    current_time = int(time.time())  # Current UNIX timestamp
    user_data = get_user_data(user_id)

    if user_data:
        # Check if 24 hours have passed since the last activity
        if current_time - user_data['last_activity'] >= TIME_DELTA:
            # Reset the multiplier
            update_user_data(user_id, 0, user_data['last_activity'])
            print(f"User {user_id}'s multiplier has been reset due to inactivity.")


def award_xp(user_id, base_xp):
    user_data = get_user_data(user_id)
    if user_data:
        multiplier = user_data['multiplier']

        # Multiply the XP by the multiplier
        xp_awarded = base_xp * multiplier
        print(f"Awarded {xp_awarded} XP to user {user_id} with a multiplier of {multiplier}.")
        
        # Logic to update the XP in the database
        with db.engine.connect() as conn:
            conn.execute(players.update().where(players.c.user_id == user_id).values(
                exp=user_data['exp'] + xp_awarded
            ))


async def announce_level_up(guild: discord.Guild, member: discord.Member, level: int, channel_id: int):
    channel = guild.get_channel(channel_id)
    if channel:
        await exp_channel.send(f"🎆 {member.mention} has reached **Level {level}**.")

class ExpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="retire", description="Retire your character between levels 31-38 for heirloom bonuses.")
    async def retire(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        with engine.connect() as conn:
            result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()
            if not result:
                await exp_channel.send("You have no EXP record yet.")
                return
            if result.level < 31 or result.level > 38:
                await exp_channel.send("You can only retire between levels 31 - 38.")
                return

        await exp_channel.send(
            f"🛡️ Are you sure you want to retire? You will reset your level, EXP, and gold.\\n"
            f"Type your username (`{interaction.user.name}`) to confirm."
        )

        def check(m):
            return m.author == interaction.user and m.content == interaction.user.name

        try:
            msg = await self.bot.wait_for("message", timeout=60.0, check=check)
        except:
            await exp_channel.send("🏰 Retirement cancelled (timeout).")
            return

        heirloom_gain = get_heirloom_points(result.level)
        new_retire_count = result.retirements + 1
        new_total_heirlooms = result.heirloom_points + heirloom_gain
        multiplier = get_multiplier(new_retire_count)

        bonus_note = ""
        if new_retire_count > 16:
            bonus_note = "⚖️ Multiplier is capped at 1.48x, but you still can earn heirloom point(s)."

        with engine.connect() as conn:
            conn.execute(players.update().where(players.c.user_id == user_id).values(
                exp=0,
                level=0,
                retirements=new_retire_count,
                heirloom_points=new_total_heirlooms
            ))

        await exp_channel.send(
            f"🎖️ {interaction.user.mention} has retired and earned **{heirloom_gain} heirloom points**!\\n"
            f"Total retirements: `{new_retire_count}` → Multiplier: `{multiplier:.2f}x`\\n"
            f"All progress reset. Start your journey anew!\\n"
            f"{bonus_note}"
        )

@bot.tree.command(name="stats", description="View your own stats (level, gold, EXP, retirements, etc.)")
async def stats(interaction: discord.Interaction):
    """Fetch and display user's stats"""
    user_id = str(interaction.user.id)
    with engine.connect() as conn:
        query = players.select().where(players.c.user_id == user_id)
        result = conn.execute(query).fetchone()
        if not result:
            await exp_channel.send("No stats found. Start participating to gain EXP!", ephemeral=True)
            return
        level, exp, gold, retirements, heirloom_points = result[2], result[1], result[3], result[5], result[6]
        await exp_channel.send(
            f"**{interaction.user.display_name}'s Stats**\n"
            f"Level: {level}\nEXP: {exp}\nGold: {gold}\n"
            f"Retirements: {retirements}\nHeirloom Points: {heirloom_points}",
            ephemeral=False
        )

@bot.tree.command(name="profile", description="View another player's profile")
@app_commands.describe(user="The user whose profile you want to see")
async def profile(interaction: discord.Interaction, user: discord.User):
    """Fetch and display another user's stats"""
    user_id = str(user.id)
    with engine.connect() as conn:
        query = players.select().where(players.c.user_id == user_id)
        result = conn.execute(query).fetchone()
        if not result:
            await exp_channel.send(f"{user.display_name} has no stats yet.", ephemeral=True)
            return
        level, exp, gold, retirements, heirloom_points = result[2], result[1], result[3], result[5], result[6]
        await exp_channel.send(
            f"**{user.display_name}'s Stats**\n"
            f"Level: {level}\nEXP: {exp}\nGold: {gold}\n"
            f"Retirements: {retirements}\nHeirloom Points: {heirloom_points}",
            ephemeral=False
        )

@bot.tree.command(name="leaderboard", description="Show top 10 players by level, then EXP as a tiebreaker")
async def leaderboard(interaction: discord.Interaction):
    """Fetch and display the leaderboard"""
    with engine.connect() as conn:
        query = players.select().order_by(players.c.level.desc(), players.c.exp.desc()).limit(10)
        results = conn.execute(query).fetchall()
        
        if not results:
            await exp_channel.send("No players on the leaderboard yet.", ephemeral=False)
            return

        leaderboard_text = "**Leaderboard**\n"
        for i, result in enumerate(results, start=1):
            user_id, exp, level, gold = result[0], result[1], result[2], result[3]
            leaderboard_text += f"{i}. <@{user_id}> - Level {level}, EXP: {exp}, Gold: {gold}\n"
        
        await exp_channel.send(leaderboard_text, ephemeral=False)

async def setup(bot):
    await bot.add_cog(ExpCommands(bot))