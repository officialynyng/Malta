import os, json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "games_config.json")
with open(CONFIG_PATH) as f:
    GAMES = json.load(f)
