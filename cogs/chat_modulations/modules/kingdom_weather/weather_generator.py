import random
from sqlalchemy.orm import Session
import time
from cogs.chat_modulations.modules.kingdom_weather.region_timezone import get_region_hour
from cogs.database.kingdomweather.weather_state_region import get_region_weather_state, upsert_region_weather_state
from cogs.chat_modulations.modules.kingdom_weather.temperature.temperature_generator import generate_temperature_structured
from cogs.chat_modulations.modules.kingdom_weather.clouds.cloud_generator import generate_cloud_condition
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_logger import log_weather_event
from cogs.chat_modulations.modules.kingdom_weather.region_timezone import get_region_timestamp




# 🔮 Main condition generator
def generate_weather_for_region(session: Session, region: str) -> dict:
    hour = get_region_hour(region)
    now = get_region_timestamp(region)
    # Step 1: Generate temperature data
    temperature_struct = generate_temperature_structured(region)
    temp_c = temperature_struct["temperature_c"]
    descriptor = temperature_struct["descriptor"]
    hour = temperature_struct["hour"]
    season = temperature_struct["season"]

    # Step 2: Generate cloud data
    cloud_data = generate_cloud_condition(session, region, temperature_struct)
    cloud_condition = cloud_data["cloud_condition"]
    cloud_density = cloud_data["cloud_density"]
    eligible_conditions = cloud_data["eligible_conditions"]

    # Step 3: Retrieve past state
    past_state = get_region_weather_state(session, region)
    last_main = past_state.get("main_condition")
    last_sub = past_state.get("sub_condition")
    last_time = past_state.get("last_updated", 0)

    elapsed = now - int(last_time)
    continuing = elapsed < 14400 and last_main in eligible_conditions  # 4 hours

    # Step 4: Decide main + sub condition
    if continuing:
        main_condition = last_main
        sub_condition = last_sub
    else:
        if "storm" in eligible_conditions and random.random() < 0.2:
            main_condition = "storm"
            sub_condition = random.choice(["lightning", "heavy rain"])
        elif "rain" in eligible_conditions and random.random() < 0.4:
            main_condition = "rain"
            sub_condition = random.choice(["light rain", "moderate rain", "drizzle"])
        elif "fog" in eligible_conditions and random.random() < 0.3:
            main_condition = "fog"
            sub_condition = None
        elif "wind" in eligible_conditions and random.random() < 0.2:
            main_condition = "wind"
            sub_condition = None
        elif "drizzle" in eligible_conditions and random.random() < 0.25:
            main_condition = "drizzle"
            sub_condition = None
        else:
            if cloud_data["cloud_density"] in ["moderate", "dense"]:
                main_condition = "partly cloudy"
            else:
                main_condition = "clear"
            sub_condition = None

    # Step 5: Determine time-of-day label
    def time_of_day(hour):
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 21:
            return "evening"
        else:
            return "night"

    tod = time_of_day(hour)

    # Step 6: Smart narrative based on state change
    narrative = ""

    if continuing:
        if main_condition == "storm":
            narrative = f"The storm continues to rage over {region}, flashes of {sub_condition} seen through the gloom."
        elif main_condition == "rain":
            hours_persisted = round(elapsed / 3600)
            narrative = f"Rain has persisted over {region} for {hours_persisted} hours."
        elif main_condition == "fog":
            narrative = f"The fog still hangs thick over {region}, unbroken since earlier."
        else:
            narrative = f"The weather over {region} remains {main_condition} this {tod}."
    elif last_main and last_main != main_condition:
        if last_main == "fog" and main_condition == "drizzle":
            narrative = f"The fog over {region} lifts, giving way to a soft drizzle."
        elif last_main == "rain" and main_condition == "storm":
            hours_persisted = round(elapsed / 3600)
            narrative = f"Rain has persisted over {region} for {hours_persisted} hours and now intensifies into a storm."
        elif last_main == "clear" and main_condition in ["scattered", "overcast", "partly cloudy"]:
            narrative = f"The skies over {region} grow heavier with clouds this {tod}."
        elif main_condition == "clear" and last_main in ["fog", "rain", "drizzle"]:
            narrative = f"The skies above {region} finally clear after earlier {last_main}."
        else:
            narrative = f"The weather in {region} shifts from {last_main} to {main_condition} this {tod}."
    else:
        if main_condition == "storm":
            narrative = f"A violent storm looms over {region} this {tod}, with {sub_condition} in the distance."
        elif main_condition == "fog":
            narrative = f"Thick fog clings to the valleys of {region} during the {tod}, obscuring the light."
        elif main_condition == "rain":
            narrative = f"Rain patters across the rooftops of {region} this {tod}."
        elif main_condition == "clear":
            narrative = f"The skies above {region} are remarkably clear this {tod}."
        else:
            narrative = f"The weather over {region} is {main_condition} this {tod}."

    # Step 7: Save updated state
    upsert_region_weather_state(
        session=session,
        region=region,
        main_condition=main_condition,
        sub_condition=sub_condition,
        timestamp=now
    )

    # Step 8: Log to DB
    log_weather_event(
        session=session,
        region=region,
        temperature=temp_c,
        descriptor=descriptor,
        hour=hour,
        season=season,
        cloud_condition=cloud_condition,
        main_condition=main_condition,
        sub_condition=sub_condition,
        narrative=narrative,
        persistence_hours=elapsed // 3600 if continuing else 0,
        triggered_by="auto"
    )


    # Step 9: Return structured result
    return {
        "region": region,
        "temperature": temp_c,
        "descriptor": descriptor,
        "season": season,
        "hour": hour,
        "cloud_condition": cloud_condition,
        "cloud_density": cloud_density,
        "main_condition": main_condition,
        "sub_condition": sub_condition,
        "narrative": narrative,
        "precipitation_chance": cloud_data["precipitation_chance"]
    }