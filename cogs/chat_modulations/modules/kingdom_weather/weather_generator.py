import random
from sqlalchemy.orm import Session

from cogs.chat_modulations.modules.kingdom_weather.temperature.temperature_generator import generate_temperature_structured
from cogs.chat_modulations.modules.kingdom_weather.clouds.cloud_generator import generate_cloud_condition
from cogs.chat_modulations.modules.kingdom_weather.kingdomweather_logger import log_weather_event

# 🔮 Main condition generator
def generate_weather_for_region(session: Session, region: str) -> dict:
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

    # Step 3: Decide main + sub weather conditions
    main_condition = "clear"
    sub_condition = None

    if "storm" in eligible_conditions and random.random() < 0.2:
        main_condition = "storm"
        sub_condition = random.choice(["lightning", "heavy rain"])
    elif "rain" in eligible_conditions and random.random() < 0.4:
        main_condition = "rain"
        sub_condition = random.choice(["light rain", "moderate rain", "drizzle"])
    elif "fog" in eligible_conditions and random.random() < 0.3:
        main_condition = "fog"
    elif "wind" in eligible_conditions and random.random() < 0.2:
        main_condition = "wind"
    elif "drizzle" in eligible_conditions and random.random() < 0.25:
        main_condition = "drizzle"
    else:
        main_condition = "clear"

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
    narrative = None

    if main_condition == "storm":
        narrative = f"A violent storm looms over {region} this {tod}, with {sub_condition} in the distance."
    elif main_condition == "fog":
        narrative = f"Thick fog clings to the valleys of {region} during the {tod}, obscuring the light."
    elif main_condition == "rain":
        narrative = f"Rain patters across the rooftops of {region} this {tod}."
    elif main_condition == "clear":
        narrative = f"The skies above {region} are remarkably clear this {tod}."


    # Step 5: Log to DB
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
        triggered_by="auto"
    )

    # Step 6: Return structured result
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
