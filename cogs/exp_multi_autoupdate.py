import asyncio
from cogs.exp_engine import check_and_reset_multiplier
from cogs.exp_utils import get_all_user_ids

async def start_multiplier_cleanup(bot):
    await bot.wait_until_ready()
    print("[🌀] Routine Multiplier reset loop started.")

    while not bot.is_closed():
        user_ids = await get_all_user_ids()
        print(f"[🌀⏳] Checking {len(user_ids)} users for multiplier resets...")

        for user_id in user_ids:
            before = asyncio.get_event_loop().time()
            try:
                await check_and_reset_multiplier(user_id, bot)
                user = await bot.fetch_user(int(user_id))
                after = asyncio.get_event_loop().time()
                print(f"[🌀✅] Processed {user.display_name} ({user_id}) in {after - before:.2f}s")
            except Exception as e:
                print(f"[🌀❌] Error processing user {user_id}: {e}")
            await asyncio.sleep(0.25)

        print(f"[🌀🏁🌀] Routine Multiplier check cycle complete. {len(user_ids)} users checked.")
        await asyncio.sleep(3600)

async def setup(bot):
    print("[🌀] Setting up hourly multiplier cleanup...")
    bot.loop.create_task(start_multiplier_cleanup(bot))

