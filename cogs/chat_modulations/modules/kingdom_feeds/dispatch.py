import random
import time
import json
from discord import Embed
from cogs.exp_config import EXP_CHANNEL_ID
from cogs.database.achievement_table import log_maltachievement

# Cooldown tracker per event type
event_cooldowns = {}

# Load templates from a given JSON file
def load_templates(event_key: str):
    try:
        path = f"cogs/chat_modulations/modules/maltachievement/templates/{event_key}.json"
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "templates": ["{user} experienced a catastrophic failure."],
            "decoration_emojis": ["📉"],
            "category_emoji": ":malta:",
            "cooldown": 600,
            "color": "#2f3136",
            "footer": "Justice served in the streets of Malta"
        }

# Generalized dispatcher for embed-based event posting
def post_dynamic_embed(bot, interaction, event_key: str, context: dict, cooldown: int = None, win: bool = None):
    global event_cooldowns
    now = time.time()

    config = load_templates(event_key)
    templates = config.get("templates", [])
    emojis = config.get("decoration_emojis", ["📉"])
    category = config.get("category_emoji", ":malta:")
    default_cd = config.get("cooldown", 600)
    color = int(config.get("color", "#2f3136").lstrip("#"), 16)
    footer = config.get("footer", "Justice served in the streets of Malta")

    # Use configured cooldown unless overridden
    effective_cd = cooldown if cooldown is not None else default_cd
    last_ts = event_cooldowns.get(event_key, 0)
    if now - last_ts < effective_cd:
        return

    # Specific logic for event validation (can be extended)
    if event_key == "maltachievement":
        if win or context.get("user_gold_before", 1) <= 0 or context.get("amount_bet") != context.get("user_gold_before"):
            return

    headline = random.choice(templates).format(**context)
    flair = random.choice(emojis)
    full_title = f"{category} {event_key.replace('_', ' ').title()}"

    embed = Embed(title=full_title, description=f"{flair} {headline}\n{interaction.user.mention}", color=color)
    embed.set_footer(text=footer)

    # Post to channel and log to achievements
    channel = bot.get_channel(EXP_CHANNEL_ID)
    if channel:
        bot.loop.create_task(channel.send(embed=embed))
        log_maltachievement(user_id=interaction.user.id, event_key=event_key, context=context)
        event_cooldowns[event_key] = now
