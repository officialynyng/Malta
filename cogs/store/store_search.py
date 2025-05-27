from cogs.store.store_utils import (load_all_melee_weapon_items, load_items_from_json, get_all_items)

############################
#############MELEE##########
############################

def filter_weapon_items(
    items,
    *,
    damage_types=None,
    weapon_types=None,
    min_handling=None,
    max_handling=None,
    min_swing_speed=None,
    min_thrust_speed=None,
    min_length=None,
    max_length=None,
    min_reach=None,
    max_reach=None
):
    results = []

    for item in items:
        # Filter by damage type
        if damage_types:
            if isinstance(damage_types, str):
                damage_types = [damage_types]
            if not any(d in item.get("damage_types", []) for d in damage_types):
                continue

        # Filter by weapon type (1h, 2h, polearm, bows, etc.)
        if weapon_types:
            if isinstance(weapon_types, str):
                weapon_types = [weapon_types]
            if not any(w == item.get("category", "").split("/")[-1] for w in weapon_types):
                continue

        # Handling (maneuverability)
        handling = item.get("handling", 100)
        if min_handling is not None and handling < min_handling:
            continue
        if max_handling is not None and handling > max_handling:
            continue

        # Swing speed
        if min_swing_speed is not None and item.get("swing_speed", 0) < min_swing_speed:
            continue

        # Thrust speed
        if min_thrust_speed is not None and item.get("thrust_speed", 0) < min_thrust_speed:
            continue

        # Length & Reach
        if min_length is not None and item.get("length", 0) < min_length:
            continue
        if max_length is not None and item.get("length", 0) > max_length:
            continue
        if min_reach is not None and item.get("reach", 0) < min_reach:
            continue
        if max_reach is not None and item.get("reach", 0) > max_reach:
            continue

        results.append(item)

    return results

def get_filtered_weapons(damage_types=None, weapon_types=None, **kwargs):
    weapons = load_all_melee_weapon_items()
    return filter_weapon_items(weapons, damage_types=damage_types, weapon_types=weapon_types, **kwargs)


def filter_shields(
    items,
    *,
    min_weight=None,
    max_weight=None,
    min_speed=None,
    min_reach=None,
    min_durability=None,
    armory_type=None,
    can_be_used_on_mounts=None
):
    results = []

    for item in items:
        if min_weight and item.get("weight", 0) < min_weight:
            continue
        if max_weight and item.get("weight", 0) > max_weight:
            continue
        if min_speed and item.get("speed", 0) < min_speed:
            continue
        if min_reach and item.get("reach", 0) < min_reach:
            continue
        if min_durability and item.get("durability", 0) < min_durability:
            continue
        if armory_type and item.get("armory", "") != armory_type:
            continue
        if can_be_used_on_mounts is not None and item.get("can_be_used_on_mounts", False) != can_be_used_on_mounts:
            continue

        results.append(item)

    return results

def get_filtered_shields(**kwargs):
    shields = load_items_from_json("shields")
    return filter_shields(shields, **kwargs)

############################
###########RANGED###########
############################

def filter_ranged_items(
    items,
    *,
    category=None,
    min_accuracy=None,
    min_missile_speed=None,
    min_aim_speed=None,
    min_reload_speed=None,
    max_weight=None
):
    results = []

    for item in items:
        # Category filter
        if category and item.get("category") != category:
            continue

        if min_accuracy is not None and item.get("accuracy", 0) < min_accuracy:
            continue
        if min_missile_speed is not None and item.get("missile_speed", 0) < min_missile_speed:
            continue
        if min_aim_speed is not None and item.get("aim_speed", 0) < min_aim_speed:
            continue
        if min_reload_speed is not None and item.get("reload_speed", 0) < min_reload_speed:
            continue
        if max_weight is not None and item.get("weight", 0) > max_weight:
            continue

        results.append(item)

    return results

def get_filtered_bows_xbows(**kwargs):
    bows = load_items_from_json("weapons_bows")
    return filter_ranged_items(bows, **kwargs)

def filter_ammo_items(
    items,
    *,
    damage_types=None,
    min_ammo_count=None,
    max_stack_weight=None
):
    results = []

    for item in items:
        if damage_types:
            if isinstance(damage_types, str):
                damage_types = [damage_types]
            if not any(d in item.get("damage_types", []) for d in damage_types):
                continue

        if min_ammo_count and item.get("ammo_count", 0) < min_ammo_count:
            continue

        if max_stack_weight and item.get("stack_weight", 0) > max_stack_weight:
            continue

        results.append(item)

    return results

def get_filtered_arrows(**kwargs):
    arrows = load_items_from_json("arrows_cut", "arrows_pierce")
    return filter_ammo_items(arrows, **kwargs)

def get_filtered_bolts(**kwargs):
    bolts = load_items_from_json("bolts_cut", "bolts_pierce")
    return filter_ammo_items(bolts, **kwargs)


############################
###########MOUNTS###########
############################

def filter_mount_items(
    items,
    *,
    mount_type=None,
    min_speed=None,
    min_maneuver=None,
    min_charge_damage=None,
    min_hit_points=None
):
    results = []

    for item in items:
        if mount_type and item.get("mount_type") != mount_type:
            continue
        if min_speed and item.get("speed", 0) < min_speed:
            continue
        if min_maneuver and item.get("maneuver", 0) < min_maneuver:
            continue
        if min_charge_damage and item.get("charge_damage", 0) < min_charge_damage:
            continue
        if min_hit_points and item.get("hit_points", 0) < min_hit_points:
            continue

        results.append(item)

    return results

def get_filtered_mounts(**kwargs):
    mounts = load_items_from_json("mounts")
    return filter_mount_items(mounts, **kwargs)

def filter_mount_armor(
    items,
    *,
    material=None,
    compatible_with=None,
    min_armor_value=None,
    max_weight=None,
    min_tier=None
):
    results = []

    for item in items:
        if material and item.get("material", "").lower() != material.lower():
            continue
        if compatible_with:
            if compatible_with not in item.get("compatible_mounts", []):
                continue
        if min_armor_value and item.get("armor_value", 0) < min_armor_value:
            continue
        if max_weight and item.get("weight", 0) > max_weight:
            continue
        if min_tier and item.get("tier", 1) < min_tier:
            continue

        results.append(item)

    return results

def get_filtered_mount_armor(**kwargs):
    armor_items = load_items_from_json("mounts_armor")
    return filter_mount_armor(armor_items, **kwargs)


############################
###########ARMOR###########
############################

def filter_armor_items(
    items,
    *,
    material=None,
    min_head_armor=None,
    min_body_armor=None,
    min_arm_armor=None,
    min_leg_armor=None,
    max_weight=None
):
    results = []

    for item in items:
        if material and item.get("material", "").lower() != material.lower():
            continue
        if min_head_armor and item.get("head_armor", 0) < min_head_armor:
            continue
        if min_body_armor and item.get("body_armor", 0) < min_body_armor:
            continue
        if min_arm_armor and item.get("arm_armor", 0) < min_arm_armor:
            continue
        if min_leg_armor and item.get("leg_armor", 0) < min_leg_armor:
            continue
        if max_weight and item.get("weight", 0) > max_weight:
            continue

        results.append(item)

    return results

def get_filtered_head_armor(**kwargs):
    items = load_items_from_json("armor_head")
    return filter_armor_items(items, **kwargs)

def get_filtered_shoulders_armor(**kwargs):
    items = load_items_from_json("armor_shoulders")
    return filter_armor_items(items, **kwargs)

def get_filtered_torso_armor(**kwargs):
    items = load_items_from_json("armor_torso")
    return filter_armor_items(items, **kwargs)

def get_filtered_hand_armor(**kwargs):
    items = load_items_from_json("armor_hands")
    return filter_armor_items(items, **kwargs)

def get_filtered_leg_armor(**kwargs):
    items = load_items_from_json("armor_legs")
    return filter_armor_items(items, **kwargs)



##################################################

def get_item_from_any_store(query: str):
    """Searches all store items by ID or name (case-insensitive)."""
    query = query.lower()
    for item in get_all_items():
        if item["id"].lower() == query or item["name"].lower() == query:
            return item
    return None

async def setup(bot):
    pass  # This file only contains utility functions, no commands yet