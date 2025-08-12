import discord
import os
from discord.ext import commands


from cogs.database.init_db import init_database
from cogs.admin_config import (
    GUILD_ID, WELCOME_CHANNEL_ID
)

TOKEN = os.getenv("TOKEN")
INTENTS = discord.Intents.default()
INTENTS.messages = True
INTENTS.guilds = True
INTENTS.message_content = True
INTENTS.members = True

init_database()

class MaltaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)

    async def setup_hook(self):
        print("Loading 🚂CRPG cogs...")
        guild = discord.Object(id=GUILD_ID)
        await self.load_extension("cogs.admin_config")
        await self.load_extension("cogs.admin_group")
        #await self.load_extension("cogs.exp_utils")
        #await self.load_extension("cogs.exp_engine")
        #await self.load_extension("cogs.exp_commands")
        #await self.load_extension("cogs.exp_background")
        #await self.load_extension("cogs.ActivityAnalyzer")
        #await self.load_extension("cogs.exp_multi_autoupdate")
        #await self.load_extension("cogs.exp_reminder")

        #print("Loading 🍯Store cogs...")
        #await self.load_extension("cogs.store.store_utils")
        #await self.load_extension("cogs.store.store_upkeep")
        #await self.load_extension("cogs.store.store_search")
        #await self.load_extension("cogs.store.store_group")
        #await self.load_extension("cogs.store.store_reminder")
        
        #print("Loading 👤Character cogs...")
        #await self.load_extension("cogs.character.user_inventory_group")
        #await self.load_extension("cogs.character.user_trigger")
        #await setup_voice_exp(self)

        #print("Loading 🎟️Lottery cogs...")
        #await self.load_extension("cogs.gambling.lottery.lottery_group")
        #await self.load_extension("cogs.gambling.lottery.lottery_reminder")

        #print("Loading ♠️ ♥️ ♦️ ♣️Gambling cogs...")
        #await self.load_extension("cogs.gambling.gambling_group")
        #await self.load_extension("cogs.gambling.gambling_reminder")

        #print("Loading 💼 Wallet cogs...")
        #await self.load_extension("cogs.wallet.wallet")

        #print("Loading ⚙️ Chat Modulation cogs...")
        #print("Loading 🌧️ Kingdom Weather cogs...")
        #await self.load_extension("cogs.chat_modulations.modules.kingdom_weather.weather_scheduler")
        #await self.load_extension("cogs.chat_modulations.modules.kingdom_weather.weather_admin_group")
        #await self.load_extension("cogs.chat_modulations.modules.kingdom_weather.forecast.forecast_admin_group")
        #print("Loading ⏲️ Malta Time cogs...")
        #await self.load_extension("cogs.chat_modulations.modules.malta_time.scheduler")
        #await self.load_extension("cogs.chat_modulations.modules.malta_time.admin_group")
        #await self.load_extension("cogs.chat_modulations.modules.malta_time.time_controls")

        for guild in self.guilds:
            print(f"[DEBUG] Connected to guild: {guild.name} (ID: {guild.id})")
        await self.tree.sync(guild=guild)  # Sync the commands with the guild directly
        for cmd in self.tree.walk_commands():
            print(f"[🔎[✅Registered] slash command: /{cmd.name}")

        print("🟩🟩🟩All cogs and commands loaded.🟩🟩🟩")



bot = MaltaBot()

@bot.event
async def on_message(message):
    if message.guild is None and not message.author.bot:  # Check if the message is a DM and not from a bot
        debug_info = (f"Received DM from {message.author} (ID: {message.author.id}): "
                      f"{message.content}")
        print(debug_info)  # Log the information to console for debugging

        # Optionally, send a response back to the user with the debug info
        await message.channel.send(f"Debug: {debug_info}")

    # Process commands if any
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    ###############################
    #Remove to prevent MANUAL sync.
    await bot.tree.sync()
    ###############################
    print("Command tree synced.")
    

@bot.event
async def on_member_join(member):
    # Compose your welcome message
    welcome_message = f"{member.mention} has joined the server."

    # Try to send the message to the welcome channel
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(welcome_message)

@bot.event
async def on_member_remove(member):
    farewell_message = f"{member.name} has left the server."
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(farewell_message)

bot.run(TOKEN)
