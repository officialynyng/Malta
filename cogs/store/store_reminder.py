import discord
from discord.ext import tasks, commands
import random
from cogs.exp_config import EXP_CHANNEL_ID
import datetime
import asyncio
import pytz

SHOP_REMINDER_VARIANTS = [
    {
        "line": "",
        "img": "http://theknightsofmalta.net/wp-content/uploads/2025/05/ynyng_medieval_Malta_marketplace_with_a_cloaked_merchant_reveal_ce19f260-2c5e-4668-9c7b-ab2ea7ce029b.png"
    },
    {
        "line": "",
        "img": "http://theknightsofmalta.net/wp-content/uploads/2025/05/ynyng_grim_medieval_war_camp_bazaar_weighing_scales_with_batter_500c364c-8f97-41d9-8001-86e45edb1a43.png"
    },
    {
        "line": "",
        "img": "http://theknightsofmalta.net/wp-content/uploads/2025/05/ynyng_the_knights_of_Malta_in_pitch_black_ROBES_axis_malta_cros_a9789c9d-fdbf-4a97-9e14-5303eb05d589.png"
    },
    {
        "line": "",
        "img": "http://theknightsofmalta.net/wp-content/uploads/2025/05/ynyng_haunted_medieval_marketplace_bell_tower_ringing_at_dusk_g_b271ca9d-12bd-4b6a-8550-4f152048219b.png"
    },
    {
        "line": "",
        "img": "http://theknightsofmalta.net/wp-content/uploads/2025/05/ynyng_large_PLUMP_jolly_brunette_merchant_man_store_front_trade_0637ddfa-61f0-46e7-aa44-e5120c6d3b4b.png"
    },
]

class ShopReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.shop_reminder_loop())

    async def shop_reminder_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            now = datetime.datetime.now(pytz.timezone("America/Chicago"))
            should_post = now.minute == 0 and now.hour % 6 == 0

            if should_post:
                print(f"[SHOP DEBUG] Posting shop reminder at {now.isoformat()}")
                channel = self.bot.get_channel(EXP_CHANNEL_ID)
                if channel:
                    variant = random.choice(SHOP_REMINDER_VARIANTS)

                    embed = discord.Embed(
                        title="🍯🛒 MALTAS DISCORD CRPG SHOP",
                        description="**Use** `/shop open` to browse the wares.\n**Use** `/help` for further details.",
                        color=discord.Color.gold()
                    )
                    embed.set_image(url=variant["img"])
                    embed.set_footer(text="The market is always open! Trails are out and functional! Take a look!")

                    await channel.send(content=variant["line"], embed=embed)

            # Sleep until the next top-of-hour
            next_hour = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            sleep_seconds = (next_hour - now).total_seconds()
            await asyncio.sleep(sleep_seconds)


async def setup(bot):
    print("[SHOP DEBUG] ShopReminder cog loaded")
    await bot.add_cog(ShopReminder(bot))
