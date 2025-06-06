import discord
from datetime import datetime
from zoneinfo import ZoneInfo
from cogs.chat_modulations.modules.kingdom_weather.weather_controller import (
    cloud_visuals,
    temperature_descriptor
)
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_utils import condition_emojis



def calculate_time_jump_stability(last_weather_ts, forecast_dt: datetime):
    if isinstance(last_weather_ts, datetime):
        last_weather_ts = last_weather_ts.timestamp()

    forecast_epoch = forecast_dt.timestamp()
    delta_seconds = forecast_epoch - last_weather_ts
    delta_hours = delta_seconds / 3600

    if delta_hours < 1:
        return "🟢 Stable"
    elif delta_hours < 3:
        return "🟡 Slightly Ahead"
    else:
        return f"🔴 Time Rift! ({round(delta_hours, 1)} hours since last weather post)"

def build_forecast_embed(region, forecast_data, malta_dt, forecast_accuracy=None):
    main = forecast_data["main_condition"]
    sub = forecast_data["sub_condition"]
    temp = forecast_data["temperature"]
    precip = forecast_data["precipitation_chance"]
    trend = forecast_data.get("trend", "Unknown")
    change_chance = forecast_data.get("change_chance", "Unknown")
    time_label = forecast_data.get("time_label", "Unknown time")
    region_time = forecast_data.get("region_time", "Unknown")
    persistence_note = forecast_data.get("persistence_note")
    forecast_confidence = forecast_data.get("confidence", "Moderate")

    emoji = condition_emojis.get(main.lower(), "❓")

    # Time comparison
    real_now = datetime.now(tz=ZoneInfo("America/Chicago"))
    time_stability = calculate_time_jump_stability(
        forecast_data.get("last_weather_ts", malta_dt.timestamp()),
        malta_dt
    )

    embed = discord.Embed(
        title=f"⛈️🌄 Forecast for 🏦 {region}",
        description=f"{emoji} **Expected:** *{sub}* — *{trend}*\n\n{change_chance}",
        color=discord.Color.greyple()
    )


    embed.add_field(name="🌀 Condition", value=f"{emoji} {main}", inline=True)
    embed.add_field(name="🌡️ Temp", value=f"{temp}°F — {temperature_descriptor(temp)}", inline=True)
    embed.add_field(name="🌧️ Precipitation", value=f"{precip}%", inline=True)
    cloud_display = forecast_data.get("cloud_visual")
    if not cloud_display or "?" in cloud_display:
        cloud_display = f"[?????] {forecast_data.get('cloud_density', 'unknown')}"
    embed.add_field(name="☁️ Clouds", value=cloud_display, inline=True)
    embed.add_field(name="📅 Forecast Time", value=f"{time_label} — {region_time} MT", inline=False)
    embed.add_field(name="📊 Forecast Confidence", value=f"🔍 {forecast_confidence}", inline=True)
    embed.add_field(name="🕗 Time Stability", value=f"{time_stability}", inline=True)

    if forecast_accuracy is not None:
        embed.add_field(name="📉 Last Forecast Deviation", value=f"{forecast_accuracy}", inline=False)

    if persistence_note:
        embed.description += f"\n\n{persistence_note}"

    embed.set_footer(text="• Dynamic Weather System | Forecast Subject to Change ⚠️")
    return embed
