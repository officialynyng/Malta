

def calculate_melee_weapon_upkeep(item):
    # Base cost (price of the item scaled down)
    base_cost = item.get("price", 0) * 0.03

    # Weight factor (heavier weapons usually require more upkeep)
    weight_factor = item.get("weight", 0) * 0.6

    # Swing speed factor (faster weapons may need more upkeep due to maintenance of agility)
    swing_speed = item.get("swing_speed", 0)
    swing_speed_factor = max(0, 100 - swing_speed) * 0.4  # slower = higher upkeep

    # Thrust speed factor (similar logic to swing speed)
    thrust_speed = item.get("thrust_speed", 0)
    thrust_speed_factor = max(0, 100 - thrust_speed) * 0.3  # slower thrust = higher upkeep

    # Handling factor (the more maneuverable a weapon, the more upkeep)
    handling = item.get("handling", 100)
    handling_factor = max(0, 100 - handling) * 0.4  # low handling = more upkeep

    # Reach factor (longer weapons need more maintenance)
    reach = item.get("reach", 0)
    reach_factor = reach * 0.2  # longer reach = more upkeep

    # Length factor (longer weapons are harder to maintain)
    length = item.get("length", 0)
    length_factor = length * 0.3  # longer = more upkeep

    # Damage types (special damage types may increase upkeep, e.g., blunt vs cutting)
    damage_types = item.get("damage_types", [])
    damage_type_factor = 0
    if "pierce" in damage_types:
        damage_type_factor += 0.2
    if "cut" in damage_types:
        damage_type_factor += 0.15
    if "blunt" in damage_types:
        damage_type_factor += 0.25

    # Tier factor (higher tier = more expensive upkeep)
    tier_factor = item.get("tier", 1) ** 1.2

    # Total upkeep cost
    total_upkeep = base_cost + weight_factor + swing_speed_factor + thrust_speed_factor + handling_factor + reach_factor + length_factor + (damage_type_factor * base_cost) + tier_factor
    return round(total_upkeep)

def calculate_mount_upkeep(item):
    base = item.get("price", 0) * 0.025
    weight_factor = item.get("body_length", 0) * 0.1
    charge_factor = item.get("charge_damage", 0) * 0.2
    tankiness = item.get("hit_points", 0) * 0.05
    return round(base + weight_factor + charge_factor + tankiness)

def calculate_mount_armor_upkeep(item):
    # Base upkeep cost based on price (scaled down)
    base_upkeep = item.get("price", 0) * 0.02

    # Weight factor (heavier armor means more upkeep)
    weight_factor = item.get("weight", 0) * 0.05

    # Armor value factor (higher armor value = more upkeep)
    armor_value_factor = item.get("armor_value", 0) * 0.1

    # Tier factor (higher tier = higher upkeep)
    tier_factor = item.get("tier", 1) ** 1.3  # More complex = more upkeep

    # Total upkeep calculation
    total_upkeep = base_upkeep + weight_factor + armor_value_factor + tier_factor
    return round(total_upkeep)

def calculate_ranged_upkeep(item):
    # Base upkeep cost based on price (scaled down)
    base = item.get("price", 0) * 0.03

    # Penalty based on reload speed (longer reload = higher upkeep)
    reload_penalty = max(0, 100 - item.get("reload_speed", 0)) * 0.1

    # Penalty based on aim speed (slower aiming = higher upkeep)
    aim_penalty = max(0, 100 - item.get("aim_speed", 0)) * 0.1

    # Bonus based on accuracy (more accurate = lower upkeep)
    accuracy_bonus = item.get("accuracy", 0) * 0.05

    # Weight factor (heavier ranged weapons need more upkeep)
    weight_factor = item.get("weight", 0) * 0.05

    # Total upkeep cost
    total_upkeep = base + reload_penalty + aim_penalty + accuracy_bonus + weight_factor
    return round(total_upkeep)


def calculate_ammo_upkeep(item):
    base_upkeep = item.get("price", 0) * 0.04

    # Damage type factor
    type_multiplier = 1.0
    for dmg in item.get("damage_types", []):
        if dmg == "pierce":
            type_multiplier += 0.2
        elif dmg == "cut":
            type_multiplier += 0.1

    # Weight adds a bit
    weight_factor = item.get("stack_weight", 0) * 0.1

    # Ammo count adds small per-arrow upkeep (e.g., 0.02 per arrow)
    ammo_bonus = item.get("ammo_count", 0) * 0.02

    upkeep = base_upkeep * type_multiplier + weight_factor + ammo_bonus
    return round(upkeep)

def calculate_shield_upkeep(item):
    # Base upkeep cost based on price (scaled down)
    base_upkeep = item.get("price", 0) * 0.03

    # Weight factor (heavier shields generally cost more to maintain)
    weight_factor = item.get("weight", 0) * 0.1

    # Speed factor (slower shields may require more upkeep due to maneuvering issues)
    speed_factor = max(0, 100 - item.get("speed", 100)) * 0.05  # slower = higher upkeep

    # Reach factor (larger shields may need more maintenance)
    reach_factor = item.get("reach", 0) * 0.05

    # Armory factor (cavalry shields might need more upkeep)
    armory_factor = 0
    if item.get("armory") == "cavalry":
        armory_factor = 0.15  # cavalry shields are more specialized

    # Total upkeep calculation (without durability)
    total_upkeep = base_upkeep + weight_factor + speed_factor + reach_factor + armory_factor
    return round(total_upkeep)

def calculate_armor_upkeep(item):
    # Base upkeep cost based on price (scaled down)
    base_upkeep = item.get("price", 0) * 0.03

    # Weight factor (heavier armor generally costs more to maintain)
    weight_factor = item.get("weight", 0) * 0.1

    # Armory factor (specialized armor for cavalry might need more upkeep)
    armory_factor = 0
    if item.get("armory") == "cavalry":
        armory_factor = 0.15  # Cavalry armor is specialized, thus more upkeep

    # Total upkeep calculation
    total_upkeep = base_upkeep + weight_factor + armory_factor
    return round(total_upkeep)

def calculate_head_armor_upkeep(item):
    # Base upkeep
    base_upkeep = item.get("price", 0) * 0.03

    # Weight factor (heavier helmets cost more to maintain)
    weight_factor = item.get("weight", 0) * 0.1

    # Head armor value (higher protection = more maintenance)
    head_armor_value = item.get("head_armor", 0)
    head_armor_factor = head_armor_value * 0.15

    # Total upkeep
    total_upkeep = base_upkeep + weight_factor + head_armor_factor
    return round(total_upkeep)

def calculate_shoulder_armor_upkeep(item):
    # Base upkeep
    base_upkeep = item.get("price", 0) * 0.03

    # Weight factor
    weight_factor = item.get("weight", 0) * 0.1

    # Body armor and arm armor values
    body_armor_factor = item.get("body_armor", 0) * 0.1
    arm_armor_factor = item.get("arm_armor", 0) * 0.1

    # Total upkeep
    total_upkeep = base_upkeep + weight_factor + body_armor_factor + arm_armor_factor
    return round(total_upkeep)

def calculate_torso_armor_upkeep(item):
    # Base upkeep
    base_upkeep = item.get("price", 0) * 0.03

    # Weight factor
    weight_factor = item.get("weight", 0) * 0.1

    # Body armor, arm armor, and leg armor values
    body_armor_factor = item.get("body_armor", 0) * 0.15
    arm_armor_factor = item.get("arm_armor", 0) * 0.1
    leg_armor_factor = item.get("leg_armor", 0) * 0.1

    # Total upkeep
    total_upkeep = base_upkeep + weight_factor + body_armor_factor + arm_armor_factor + leg_armor_factor
    return round(total_upkeep)

def calculate_hand_armor_upkeep(item):
    # Base upkeep
    base_upkeep = item.get("price", 0) * 0.03

    # Weight factor
    weight_factor = item.get("weight", 0) * 0.1

    # Arm armor factor
    arm_armor_factor = item.get("arm_armor", 0) * 0.1

    # Total upkeep
    total_upkeep = base_upkeep + weight_factor + arm_armor_factor
    return round(total_upkeep)

def calculate_leg_armor_upkeep(item):
    # Base upkeep
    base_upkeep = item.get("price", 0) * 0.03

    # Weight factor
    weight_factor = item.get("weight", 0) * 0.1

    # Leg armor factor
    leg_armor_factor = item.get("leg_armor", 0) * 0.15

    # Total upkeep
    total_upkeep = base_upkeep + weight_factor + leg_armor_factor
    return round(total_upkeep)

async def setup(bot):
    pass
