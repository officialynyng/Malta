import random
import json
from pathlib import Path

# Path to regions.json (relative to this file's directory)
REGIONS_PATH = Path(__file__).parent.parent / "regions" / "regions.json"

def load_regions() -> list[str]:
    """Load region names from the JSON file."""
    try:
        with REGIONS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("regions", [])
    except Exception as e:
        print(f"[region_picker] Failed to load regions: {e}")
        return []

def get_all_regions() -> list[str]:
    """Return the full list of region names."""
    return load_regions()

def get_random_region() -> str:
    """Return a random region name."""
    regions = load_regions()
    return random.choice(regions) if regions else "Unknown Region"

def is_valid_region(name: str) -> bool:
    """Check if a region matches any in the list (case-insensitive)."""
    return name.lower() in [r.lower() for r in load_regions()]

def get_region_match(name: str) -> str | None:
    """Return the properly-cased region name if matched."""
    for region in load_regions():
        if region.lower() == name.lower():
            return region
    return None
