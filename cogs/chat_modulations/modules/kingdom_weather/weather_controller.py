import os
import random
import time
import json
import asyncio


from discord import Embed
from discord.ext import tasks


from cogs.exp_config import EXP_CHANNEL_ID


last_weather_ts = 0
WEATHER_COOLDOWN = 1800  # 30 minutes

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def pick_weighted_profile():
    weights = load_json("cogs/chat_modulations/modules/kingdom_weather/weather_weights.json")
    choices = list(weights.keys())
    values = list(weights.values())
    return random.choices(choices, weights=values, k=1)[0]

def load_weather_profile(profile_name: str):
    path = f"cogs/chat_modulations/modules/kingdom_weather/profiles/{profile_name}.json"
    return load_json(path)

def pick_region():
    region_list = load_json("cogs/chat_modulations/modules/kingdom_weather/regions.json")
    return random.choice(region_list)

async def post_weather(bot):
    global last_weather_ts
    now = time.time()

    if now - last_weather_ts < WEATHER_COOLDOWN:
        return

    profile_key = pick_weighted_profile()
    profile = load_weather_profile(profile_key)
    region = pick_region()
    narrative = random.choice(profile["narrative_templates"]).replace("{region}", region)

    embed = Embed(
        title=f"{profile['icon']} Weather Update – {region}",
        description=narrative,
        color=int(profile["color"].lstrip("#"), 16)
    )
    embed.add_field(name="Condition", value=profile["main_condition"], inline=True)
    embed.add_field(name="Temp", value=profile["temperature"], inline=True)
    embed.add_field(name="Wind", value=profile["wind"], inline=True)
    embed.set_footer(text=profile["footer"])

    channel = bot.get_channel(EXP_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)
        last_weather_ts = now
        
def setup_weather_task(bot):
    @tasks.loop(hours=6)
    async def weather_loop():
        await post_weather(bot)

    @weather_loop.before_loop
    async def before_loop():
        await bot.wait_until_ready()

    weather_loop.start()