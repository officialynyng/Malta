import sqlalchemy as db
from sqlalchemy import select
from discord.ext import commands

from cogs.exp_config import (
    players, engine, LEVEL_CAP, TIME_DELTA, MAX_MULTIPLIER, BASE_EXP_SCALE,
)

from cogs.wallet.log_transactions import log_transaction 

DEBUG = True
# 🔒 Ensures all user_id comparisons match the VARCHAR type in Postgres
def safe_id(uid) -> str:
    return str(uid)

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
### DICTIONAIRY ### 
def get_user_data(user_id):
    with engine.connect() as conn:
        stmt = select(players).where(players.c.user_id == safe_id(user_id))
        result = conn.execute(stmt)
        row = result.fetchone()

        if row:
            return dict(row._mapping)  # Returns the full row as a dict
        else:
            return None


def update_user_data(user_id, new_retirement_multiplier, new_daily_multiplier, last_activity_time, last_multiplier_update=None, username=None):
    if username:
        print(f"[DEBUG]🗒️🖊️ update_user_data called for {username} ({user_id})")
    else:
        print(f"[DEBUG]🗒️🖊️ update_user_data called for user_id={user_id}")

    print(f"[DEBUG]🗒️🖊️ New values: gen_multiplier={new_retirement_multiplier}, daily_multiplier={new_daily_multiplier}, last_activity={last_activity_time}, last_multiplier_update={last_multiplier_update}")

    values = {
        "multiplier": new_retirement_multiplier,
        "daily_multiplier": new_daily_multiplier,
        "last_message_ts": last_activity_time,
    }

    if last_multiplier_update is not None:
        values["last_multiplier_update"] = last_multiplier_update

    with engine.connect() as conn:
        conn.execute(players.update().where(players.c.user_id == safe_id(user_id)).values(**values))
        conn.commit()

    print("[DEBUG]🗒️🖊️☑️ User data updated in database")

def update_user_gold(user_id, new_gold_amount, type_: str = "gold_update", description: str = ""):
    if not isinstance(new_gold_amount, int):
        raise ValueError(f"[ERROR] Gold must be an integer, got {type(new_gold_amount)}")

    user_data = get_user_data(user_id)
    if not user_data:
        raise ValueError(f"[ERROR] No user data found for ID {user_id}")

    old_gold = user_data.get("gold", 0)
    delta = new_gold_amount - old_gold

    if DEBUG:
        print(f"[DEBUG]💰 Updating gold for user {user_id} → {new_gold_amount} (Δ {delta})")

    with engine.connect() as conn:
        conn.execute(
            players.update()
            .where(players.c.user_id == safe_id(user_id))
            .values(gold=new_gold_amount)
        )
        conn.commit()

    # Log the transaction
    if delta != 0:
        log_transaction(user_id, delta, type_, description)

    if DEBUG:
        print(f"[DEBUG]💰 Gold updated and transaction logged for {user_id}")



def get_all_user_ids():
    with engine.connect() as conn:
        result = conn.execute(select(players.c.user_id)).fetchall()
        return [str(row[0]) for row in result]

async def setup(bot):
    await bot.add_cog(ExpUtils(bot))