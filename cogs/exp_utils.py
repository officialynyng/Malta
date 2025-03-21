import sqlalchemy as db
from sqlalchemy import select
from discord.ext import commands

from cogs.exp_config import (
    players, engine, LEVEL_CAP, TIME_DELTA, MAX_MULTIPLIER, BASE_EXP_SCALE,
)

class ExpUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            return None
        
def update_user_data(user_id, new_retirement_multiplier, new_daily_multiplier, last_activity_time, last_multiplier_update):
    print(f"[DEBUG] update_user_data called with user_id={user_id}, new_retirement_multiplier={new_retirement_multiplier}, new_daily_multiplier={new_daily_multiplier}, last_activity_time={last_activity_time}, last_multiplier_update={last_multiplier_update}")
    with engine.connect() as conn:
        conn.execute(players.update().where(players.c.user_id == user_id).values(
            multiplier=new_retirement_multiplier,
            daily_multiplier=new_daily_multiplier,
            last_message_ts=last_activity_time,
            last_multiplier_update=last_multiplier_update
        ))
    print("[DEBUG] User data updated in database")

async def setup(bot):
    await bot.add_cog(ExpUtils(bot))