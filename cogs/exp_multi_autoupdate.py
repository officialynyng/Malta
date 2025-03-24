import asyncio
from discord.ext import tasks
from cogs.exp_engine import check_and_reset_multiplier
from cogs.exp_utils import get_all_user_ids

# Hourly background task to auto-check and update multipliers
async def start_hourly_multiplier_check(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        print("[🏔️⏲ AutoMultiplier] Checking all user multipliers...")
        try:
            user_ids = await get_all_user_ids()
            print(f"[🏔️⏲ AutoMultiplier] Found {len(user_ids)} users to check.")
            for user_id in user_ids:
                print(f"[🏔️⏲ AutoMultiplier] Checking multiplier for user: {user_id}")
                await check_and_reset_multiplier(user_id, bot)
        except Exception as e:
            print(f"[🏔️⏲ AutoMultiplier] Error during hourly check: {e}")
        print("[🏔️⏲ AutoMultiplier] Sleeping for 1 hour...")
        await asyncio.sleep(3600)  # wait 1 hour

# Helper to hook this in on bot startup
def setup(bot):
    print("[🏔️⏲ AutoMultiplier] Setting up hourly multiplier check...")
    bot.loop.create_task(start_hourly_multiplier_check(bot))
