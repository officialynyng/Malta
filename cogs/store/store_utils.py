import json
import os
import time
from sqlalchemy.sql import insert, delete, select, and_
from cogs.exp_config import engine
from cogs.database.user_inventory_table import user_inventory
from cogs.exp_utils import get_user_data, update_user_data, update_user_gold

DEBUG = True  # Set to False in production
DATA_DIR = os.path.join(os.path.dirname(__file__), "Items")


CATEGORY_TO_FILES = {
    "armor": [
        "Armor/armor_hands.json",
        "Armor/armor_head.json",
        "Armor/armor_legs.json",
        "Armor/armor_shoulders.json",
        "Armor/armor_torso.json"
    ],
    "estates": ["Estates/estates.json"],
    "mounts": [
        "Mounts/mounts.json",
        "Mounts/mounts_armor.json"
    ],
    "pets": ["Pets/pets.json"],
    "shields": ["Shields/shields.json"],
    "titles": ["Titles/titles.json"],
    "trails": ["Trails/trails.json"],
    "utility": ["Utility/utility.json"],
    "weapons - 1H": [
        "Weapons_1H/weapons_1h_axe.json",
        "Weapons_1H/weapons_1h_mace.json",
        "Weapons_1H/weapons_1h_sword.json"
    ],
    "weapons - 2h": [
        "Weapons_2h/weapons_2h_axe.json",
        "Weapons_2h/weapons_2h_mace.json",
        "Weapons_2h/weapons_2h_sword.json"
    ],
    "weapons - arrows": [
        "Weapons_Arrows/arrows_cut.json",
        "Weapons_Arrows/arrows_pierce.json"
    ],
    "weapons - Bolts": [
        "Weapons_Bolts/bolts_cut.json",
        "Weapons_Bolts/bolts_pierce.json"
    ],
    "weapons - polearms": [
        "Weapons_Polearm/weapons_polearm_2d.json",
        "Weapons_Polearm/weapons_polearm_4d.json"
    ],
    "weapons - crossbows": ["Weapons_XBows/weapons_xbows.json"]
}

STORE_CATEGORIES = list(CATEGORY_TO_FILES.keys())

STORE_ROOT = "cogs/Items"

# Generic loader for a single item JSON file
def load_items_from_json(file_path):
    full_path = os.path.join(STORE_ROOT, file_path + ".json")
    if os.path.exists(full_path):
        if DEBUG:
            print(f"[DEBUG] Loading items from: {full_path}")
        with open(full_path, "r") as f:
            return json.load(f)
    if DEBUG:
        print(f"[DEBUG] File not found: {full_path}")
    return []

# Return all items across all files
def get_all_items():
    all_items = []
    for file_list in CATEGORY_TO_FILES.values():
        for filename in file_list:
            full_path = os.path.join(DATA_DIR, filename)
            if os.path.exists(full_path):
                print(f"[DEBUG] Trying to load: {full_path}")  # 🔍 Add this line
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        all_items.extend(json.load(f))
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Failed to load {full_path}: {e}")
    if DEBUG:
        print(f"[DEBUG] Loaded {len(all_items)} total items from all categories")
    return all_items

# Get item by ID (searching across all files)
def get_item_by_id(item_id):
    for file_list in CATEGORY_TO_FILES.values():
        for filename in file_list:
            path = os.path.join(DATA_DIR, filename)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        items = json.load(f)
                        for item in items:
                            if not isinstance(item, dict):
                                if DEBUG:
                                    print(f"[WARN] Skipping non-dict item in '{filename}': {item}")
                                continue
                            if item.get("id") == item_id:
                                if DEBUG:
                                    print(f"[DEBUG] Found item '{item_id}' in file '{filename}'")
                                return item
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Failed to parse '{filename}': {e}")
    if DEBUG:
        print(f"[DEBUG] Item '{item_id}' not found in any category")
    return None



def get_item_by_category(category_name):
    file_list = CATEGORY_TO_FILES.get(category_name.lower(), [])
    items = []
    for filename in file_list:
        path = os.path.join(DATA_DIR, filename)
        if DEBUG:
            print(f"[DEBUG] Attempting to load: {path}")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    items.extend(json.load(f))
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to load {path}: {e}")
        else:
            if DEBUG:
                print(f"[DEBUG] File not found: {path}")
    return items


# Get all available category names
def get_category_names():
    return STORE_CATEGORIES

def load_all_melee_weapon_items():
    # List of melee weapon categories only (no ranged weapons)
    melee_categories = [
        "weapons_1h_axe",
        "weapons_1h_sword",
        "weapons_1h_mace",
        "weapons_2h_axe",
        "weapons_2h_mace",
        "weapons_2h_sword",
        "weapons_polearm_2d",
        "weapons_polearm_4d"
    ]
    
    weapons = []
    for category in melee_categories:
        weapons.extend(load_items_from_json(category))
    return weapons

# Check if item is in stock
def check_item_availability(item_id):
    item = get_item_by_id(item_id)
    if not item:
        if DEBUG:
            print(f"[DEBUG] Item '{item_id}' not found.")
        return False

    # ✅ Always allow trails to be bought
    if item.get("category", "").lower() == "trails":
        if DEBUG:
            print(f"[DEBUG] Item '{item_id}' is a trail and always available.")
        return True

    available = item.get("stock", 0) > 0
    if DEBUG:
        print(f"[DEBUG] Item '{item_id}' availability: {available}")
    return available

# Update item stock in its file
def update_item_stock(item_id, new_stock):
    for file_list in CATEGORY_TO_FILES.values():
        for filename in file_list:
            path = os.path.join(DATA_DIR, filename)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                items = json.load(f)
            for item in items:
                if item["id"] == item_id:
                    item["stock"] = new_stock
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(items, f, indent=4)
                    if DEBUG:
                        print(f"[DEBUG] Updated stock for '{item_id}' to {new_stock} in file '{filename}'")
                    return True
    if DEBUG:
        print(f"[DEBUG] Failed to update stock for '{item_id}' — not found")
    return False


# Get user inventory
def get_user_inventory(user_id):
    data = get_user_data(user_id)
    inventory = data.get("inventory", [])
    if DEBUG:
        print(f"[DEBUG] Inventory for user {user_id}: {inventory}")
    return inventory

def add_item_to_inventory(user_id, item_id, item_type, equipped=False):
    with engine.begin() as conn:
        if equipped:
            # Unequip any currently equipped item of this type
            unequip_stmt = user_inventory.update().where(
                (user_inventory.c.user_id == user_id) &
                (user_inventory.c.item_type == item_type) &
                (user_inventory.c.equipped == True)
            ).values(equipped=False)
            result = conn.execute(unequip_stmt)
            if DEBUG:
                print(f"[DEBUG]👤🔁 Unequipped {result.rowcount} previously equipped {item_type}(s)")
        # In add_item_to_inventory before insert, if item_type is "titles"
        if item_type == "titles":
            check_stmt = select(user_inventory).where(
                (user_inventory.c.user_id == user_id) &
                (user_inventory.c.item_type == "titles")
            )
            result = conn.execute(check_stmt).fetchone()
            if result:
                # User already owns a title
                if DEBUG:
                    print(f"[DEBUG]👤🛑 User {user_id} already owns a title — blocking insert.")
                return  # Or raise/return failure
        stmt = insert(user_inventory).values(
            user_id=user_id,
            item_id=item_id,
            item_type=item_type,
            equipped=True if item_type == "titles" else equipped
        )
        try:
            conn.execute(stmt)
            if DEBUG:
                print(f"[DEBUG]👤📦 Added item '{item_id}' ({item_type}) to user {user_id}'s inventory with equipped={equipped}")
        except Exception as e:
            if DEBUG:
                print(f"[ERROR]👤🚨 Failed to add item '{item_id}' for user {user_id}: {e}")

def equip_item(user_id, item_id, item_type):
    with engine.begin() as conn:
        # Unequip any currently equipped item of this type
        unequip_stmt = user_inventory.update().where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_type == item_type) &
            (user_inventory.c.equipped == True)
        ).values(equipped=False)
        conn.execute(unequip_stmt)

        # Equip the new item
        equip_stmt = user_inventory.update().where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_id == item_id) &
            (user_inventory.c.item_type == item_type)
        ).values(equipped=True)
        conn.execute(equip_stmt)

        if DEBUG:
            print(f"[DEBUG] 👤🧢 Equipped '{item_id}' ({item_type}) for user {user_id}")


# Get user gold
def get_user_gold(user_id):
    data = get_user_data(user_id)
    gold = data.get("gold", 0)
    if DEBUG:
        print(f"[DEBUG] User {user_id} has {gold} gold")
    return gold

def add_gold_to_user(user_id, amount):
    data = get_user_data(user_id)
    data["gold"] += amount
    update_user_data(user_id, data["multiplier"], data["daily_multiplier"], data["last_message_ts"], data["last_multiplier_update"])
    if DEBUG:
        print(f"[DEBUG] Added {amount} gold to user {user_id}")

def get_item_price(item_id):
    item = get_item_by_id(item_id)
    price = item.get("price", 0) if item else 0
    if DEBUG:
        print(f"[DEBUG] Price for item '{item_id}': {price}")
    return price

def update_item_price(item_id, new_price):
    for file_list in CATEGORY_TO_FILES.values():
        for filename in file_list:
            path = os.path.join(DATA_DIR, filename)
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                items = json.load(f)
            for item in items:
                if item["id"] == item_id:
                    item["price"] = new_price
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(items, f, indent=4)
                    if DEBUG:
                        print(f"[DEBUG] Updated price for '{item_id}' to {new_price} in file '{filename}'")
                    return True
    if DEBUG:
        print(f"[DEBUG] Failed to update price — item '{item_id}' not found")
    return False

# Process item purchase
def process_purchase(user_id, item_id, item_type):
    item = get_item_by_id(item_id)
    if not item:
        return False, "Item not found"

    if not check_item_availability(item_id):
        return False, "Item out of stock"

    user_data = get_user_data(user_id)
    gold = user_data.get("gold", 0)
    price = item.get("price", 0)

    if gold < price:
        return False, "Not enough gold"

    # Check ownership
    if check_item_ownership(user_id, item_id, item_type):
        return False, "You already own this item"
    
    # Debug before deducting
    if DEBUG:
        if user_data["gold"] < price:
            print(f"[WARN]❌ User {user_id} does NOT have enough gold ({user_data['gold']} < {price}) — this should not happen past pre-check.")
        else:
            print(f"[DEBUG]💸 Deducting {price} gold from user {user_id}")

    # Deduct gold
    user_data["gold"] = max(0, user_data["gold"] - price)

    # Update player data (keep existing multiplier-related info)
    update_user_gold(user_id, user_data["gold"])
    update_user_data(
        user_id,
        user_data["multiplier"],
        user_data["daily_multiplier"],
        user_data["last_message_ts"],
        user_data["last_multiplier_update"]
    )

    # Add item to SQL inventory
    add_item_to_inventory(user_id, item_id, item_type)

    # Decrease stock
    if "stock" in item:
        update_item_stock(item_id, item["stock"] - 1)

    if DEBUG:
        print(f"[DEBUG]👤💰 User {user_id} purchased '{item_id}' ({item_type}) for {price} gold")

    return True, f"Purchased **{item['name']}** for {price} gold"

def check_item_ownership(user_id, item_id, item_type):
    with engine.connect() as conn:
        stmt = select(user_inventory).where(and_(
            user_inventory.c.user_id == user_id,
            user_inventory.c.item_id == item_id,
            user_inventory.c.item_type == item_type
        ))
        result = conn.execute(stmt).fetchone()
        owned = result is not None
        if DEBUG:
            print(f"[DEBUG]👤🔍 User {user_id} owns '{item_id}' ({item_type}): {owned}")
        return owned


def remove_item_from_inventory(user_id, item_id, item_type):
    with engine.begin() as conn:
        stmt = delete(user_inventory).where(and_(
            user_inventory.c.user_id == user_id,
            user_inventory.c.item_id == item_id,
            user_inventory.c.item_type == item_type
        ))
        conn.execute(stmt)
        if DEBUG:
            print(f"[DEBUG]👤❌ Removed item '{item_id}' ({item_type}) from user {user_id}'s inventory")

def get_unowned_titles():
    from random import shuffle

    all_titles = get_item_by_category("Titles")
    unclaimed = []

    with engine.connect() as conn:
        for title in all_titles:
            stmt = select(user_inventory).where(and_(
                user_inventory.c.item_id == title["id"],
                user_inventory.c.item_type == "title"
            ))
            result = conn.execute(stmt).fetchone()
            if result is None:
                unclaimed.append(title)

    shuffle(unclaimed)
    return unclaimed

def roll_random_title_for_user(user_id, price):
    from random import shuffle

    # Get all title items
    titles = get_item_by_category("Titles")
    shuffle(titles)

    # Check if user already owns a title
    with engine.connect() as conn:
        owned = conn.execute(
            select(user_inventory).where(
                and_(
                    user_inventory.c.user_id == user_id,
                    user_inventory.c.item_type == "titles",
                    user_inventory.c.equipped == True
                )
            )
        ).fetchone()

    if owned:
        return "confirm_overwrite", owned["item_id"]  # Prompt user

    # Find a random unowned title
    for title in titles:
        title_id = title["id"]
        if not check_item_ownership(user_id, title_id, "titles"):
            user_data = get_user_data(user_id)

            # Safety check to prevent KeyError
            if not user_data or "gold" not in user_data:
                return False, "❌ You don't have any gold yet. Earn some first!"

            if user_data["gold"] < price:
                return False, "❌ Not enough gold for a roll."
            
            # Debug before deducting
            if DEBUG:
                if user_data["gold"] < price:
                    print(f"[WARN]❌ User {user_id} does NOT have enough gold ({user_data['gold']} < {price}) — this should not happen past pre-check.")
                else:
                    print(f"[DEBUG]💸 Deducting {price} gold from user {user_id}")

            # Deduct gold
            user_data["gold"] = max(0, user_data["gold"] - price)

            update_user_gold(user_id, user_data["gold"])
            update_user_data(
                user_id,
                user_data["multiplier"],
                user_data["daily_multiplier"],
                user_data["last_message_ts"],
                user_data["last_multiplier_update"]
            )
            # Equip title directly
            add_item_to_inventory(user_id, title_id, "titles", equipped=True)
            return True, title  # Send full title dict

    return False, "❌ No unclaimed titles left."



def get_equipped_title(user_id):
    with engine.connect() as conn:
        stmt = select(user_inventory).where(and_(
            user_inventory.c.user_id == user_id,
            user_inventory.c.item_type == "titles",
            user_inventory.c.equipped == True
        ))
        result = conn.execute(stmt).fetchone()
        return dict(result._mapping) if result else None
def get_user_by_title_id(title_id):
    with engine.connect() as conn:
        stmt = select(user_inventory).where(
            (user_inventory.c.item_id == title_id) &
            (user_inventory.c.item_type == "titles")
        )
        result = conn.execute(stmt).fetchone()
        if DEBUG:
            print(f"[DEBUG] Owner of title '{title_id}': {result['user_id'] if result else 'None'}")
        return result["user_id"] if result else None



async def setup(bot):
    pass
