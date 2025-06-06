import asyncio
import random
from discord import Client
from datetime import datetime
from zoneinfo import ZoneInfo

from cogs.exp_config import EXP_CHANNEL_ID
from cogs.chat_modulations.modules.kingdom_weather.forecast.region_picker import get_all_regions, get_random_region
from cogs.chat_modulations.modules.kingdom_weather.weather_generator import generate_weather_for_region
from cogs.chat_modulations.modules.kingdom_weather.forecast.forecast_embed import build_forecast_embed
from cogs.chat_modulations.modules.malta_time.malta_time import get_malta_datetime
from cogs.chat_modulations.modules.kingdom_weather.forecast.forecast_ts import get_last_forecast_time, update_forecast_time

# DAILY FORECAST
async def post_daily_forecast(bot: Client):
    region = get_random_region()
    malta_dt = get_malta_datetime()
    forecast = generate_weather_for_region(region)
    embed = build_forecast_embed(region, forecast, malta_dt)

    channel = bot.get_channel(EXP_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)


# WEEKLY FORECAST
async def post_weekly_forecast(bot: Client):
    channel = bot.get_channel(EXP_CHANNEL_ID)
    if not channel:
        return

    regions = get_all_regions()
    malta_dt = get_malta_datetime()

    await channel.send("📅 **Weekly Forecast** — *Malta* 🌦️")

    for region in regions:
        forecast = generate_weather_for_region(region)
        embed = build_forecast_embed(region, forecast, malta_dt)
        await channel.send(embed=embed)
        await asyncio.sleep(1)  # Safety delay


async def forecast_scheduler_loop(bot: Client):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now(tz=ZoneInfo("America/Chicago"))

        # Check if it's between 7:00 and 7:04 AM CST
        if now.hour == 7 and now.minute < 5:
            last_daily = get_last_forecast_time("daily")
            last_weekly = get_last_forecast_time("weekly")

            # 🕗 Daily forecast (if not posted today)
            if not last_daily or last_daily.date() != now.date():
                await post_daily_forecast(bot)
                update_forecast_time("daily")

            # 🗓 Weekly forecast (only on Sunday and not already posted)
            if now.weekday() == 6:
                if not last_weekly or last_weekly.date() != now.date():
                    await post_weekly_forecast(bot)
                    update_forecast_time("weekly")

            await asyncio.sleep(300)  # Sleep 5 minutes to avoid dupe posts
        else:
            await asyncio.sleep(60)
