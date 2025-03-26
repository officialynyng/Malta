import json
import os
from cogs.exp_utils import get_user_data, update_user_data

DEBUG = True  # Set to False in production

STORE_CATEGORIES = [
    "weapons/1h",
    "weapons/2h",
    "weapons/polearm",
    "bows",
    "crossbows",
    "arrows",
    "bolts",
    "armor",
    "mounts",
    "pets",
    "titles",
    "trails",
    "utility",
    "estates"
]

STORE_ROOT = "cogs/items"

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
    for category in STORE_CATEGORIES:
        items = load_items_from_json(category)
        all_items.extend(items)
    if DEBUG:
        print(f"[DEBUG] Loaded {len(all_items)} total items from all categories")
    return all_items

# Get item by ID (searching across all files)
def get_item_by_id(item_id):
    for category in STORE_CATEGORIES:
        items = load_items_from_json(category)
        for item in items:
            if item["id"] == item_id:
                if DEBUG:
                    print(f"[DEBUG] Found item '{item_id}' in category '{category}'")
                return item
    if DEBUG:
        print(f"[DEBUG] Item '{item_id}' not found in any category")
    return None

# Get items by a specific category
def get_item_by_category(category):
    if DEBUG:
        print(f"[DEBUG] Getting items from category: {category}")
    return load_items_from_json(category)

# Get items by subcategory (e.g., arrows, bolts, bows)
def get_item_by_subcategory(subcategory):
    if DEBUG:
        print(f"[DEBUG] Getting items by subcategory: {subcategory}")
    if subcategory not in STORE_CATEGORIES:
        if DEBUG:
            print(f"[DEBUG] Subcategory '{subcategory}' not found")
        return []
    return load_items_from_json(subcategory)

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
    available = item and item.get("stock", 0) > 0
    if DEBUG:
        print(f"[DEBUG] Item '{item_id}' availability: {available}")
    return available

# Update item stock in its file
def update_item_stock(item_id, new_stock):
    for category in STORE_CATEGORIES:
        path = os.path.join(STORE_ROOT, category + ".json")
        if not os.path.exists(path):
            continue
        with open(path, "r") as f:
            items = json.load(f)
        for item in items:
            if item["id"] == item_id:
                item["stock"] = new_stock
                with open(path, "w") as f:
                    json.dump(items, f, indent=4)
                if DEBUG:
                    print(f"[DEBUG] Updated stock for '{item_id}' to {new_stock}")
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

# Add item to user's inventory
def add_item_to_inventory(user_id, item_id):
    data = get_user_data(user_id)
    inventory = data.get("inventory", [])
    inventory.append(item_id)
    data["inventory"] = inventory
    update_user_data(user_id, data["multiplier"], data["daily_multiplier"], data["last_message_ts"], data["last_multiplier_update"])
    if DEBUG:
        print(f"[DEBUG] Added '{item_id}' to user {user_id}'s inventory")

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
    for category in STORE_CATEGORIES:
        path = os.path.join(STORE_ROOT, category + ".json")
        if not os.path.exists(path):
            continue
        with open(path, "r") as f:
            items = json.load(f)
        for item in items:
            if item["id"] == item_id:
                item["price"] = new_price
                with open(path, "w") as f:
                    json.dump(items, f, indent=4)
                if DEBUG:
                    print(f"[DEBUG] Updated price for '{item_id}' to {new_price}")
                return True
    if DEBUG:
        print(f"[DEBUG] Failed to update price — item '{item_id}' not found")
    return False

# Process item purchase
def process_purchase(user_id, item_id):
    item = get_item_by_id(item_id)
    if not item or not check_item_availability(item_id):
        return False, "Item not available"

    user_data = get_user_data(user_id)
    gold = user_data.get("gold", 0)
    price = item.get("price", 0)

    if gold < price:
        return False, "Not enough gold"

    # Deduct gold and add item
    user_data["gold"] -= price
    inventory = user_data.get("inventory", [])
    inventory.append(item_id)
    user_data["inventory"] = inventory
    update_user_data(user_id, user_data["multiplier"], user_data["daily_multiplier"], user_data["last_message_ts"], user_data["last_multiplier_update"])

    # Decrease stock
    update_item_stock(item_id, item["stock"] - 1)

    if DEBUG:
        print(f"[DEBUG] User {user_id} purchased '{item_id}' for {price} gold")

    return True, f"Purchased {item['name']} for {price} gold"

def check_item_ownership(user_id, item_id):
    inventory = get_user_inventory(user_id)
    owned = item_id in inventory
    if DEBUG:
        print(f"[DEBUG] User {user_id} owns '{item_id}': {owned}")
    return owned

def remove_item_from_inventory(user_id, item_id):
    data = get_user_data(user_id)
    inventory = data.get("inventory", [])
    if item_id in inventory:
        inventory.remove(item_id)
        data["inventory"] = inventory
        update_user_data(user_id, data["multiplier"], data["daily_multiplier"], data["last_message_ts"], data["last_multiplier_update"])
        if DEBUG:
            print(f"[DEBUG] Removed '{item_id}' from user {user_id}'s inventory")

async def setup(bot):
    pass
