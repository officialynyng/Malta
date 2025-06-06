import discord
from datetime import datetime
from zoneinfo import ZoneInfo
from cogs.chat_modulations.modules.kingdom_weather.weather_controller import (
    cloud_visuals,
    temperature_descriptor
)
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import condition_emojis

def calculate_time_jump_stability(real_now, malta_now):
    real_days = (real_now - datetime(2020, 1, 1, tzinfo=real_now.tzinfo)).days
    malta_days = (malta_now - datetime(1048, 1, 1, tzinfo=malta_now.tzinfo)).days
    delta = abs(malta_days - real_days)
    if delta < 30:
        return "🟢 Stable"
    elif delta < 365:
        return "🟡 Diverged"
    else:
        return "🔴 Time Rift!"

def build_forecast_embed(region, forecast_data, malta_dt, forecast_accuracy=None):
    main = forecast_data["main_condition"]
    sub = forecast_data["sub_condition"]
    temp = forecast_data["temperature"]
    precip = forecast_data["precipitation_chance"]
    cloud_density = forecast_data.get("cloud_density", "none")
    trend = forecast_data["trend"]
    change_chance = forecast_data["change_chance"]
    time_label = forecast_data["time_label"]
    region_time = forecast_data["region_time"]
    persistence_note = forecast_data.get("persistence_note")
    forecast_confidence = forecast_data.get("confidence", "Moderate")

    emoji = condition_emojis.get(main.lower(), "❓")
    cloud_field = cloud_visuals.get(cloud_density, f"[?????] {cloud_density}")

    # Time comparison
    real_now = datetime.now(tz=ZoneInfo("America/Chicago"))
    time_stability = calculate_time_jump_stability(real_now, malta_dt)

    embed = discord.Embed(
        title=f"⛈️🌄 Forecast for 🏦 {region}",
        description=f"{emoji} **Expected:** *{sub}* — *{trend}*\n\n{change_chance}",
        color=discord.Color.greyple()
    )

    embed.add_field(name="🌀 Condition", value=f"{emoji} {main}", inline=True)
    embed.add_field(name="🌡️ Temp", value=f"{temp}°F — {temperature_descriptor(temp)}", inline=True)
    embed.add_field(name="☁️ Clouds", value=cloud_field, inline=True)
    embed.add_field(name="🌧️ Precipitation", value=f"{precip}%", inline=True)
    embed.add_field(name="📅 Forecast Time", value=f"{time_label} — {region_time} MT", inline=False)
    embed.add_field(name="📊 Forecast Confidence", value=f"🔍 {forecast_confidence}", inline=True)
    embed.add_field(name="🕗 Time Stability", value=f"{time_stability}", inline=True)

    if forecast_accuracy is not None:
        embed.add_field(name="📉 Last Forecast Deviation", value=f"{forecast_accuracy}", inline=False)

    if persistence_note:
        embed.description += f"\n\n{persistence_note}"

    embed.set_footer(text="• Dynamic Weather System | Forecast Subject to Change ⚠️")
    return embed
