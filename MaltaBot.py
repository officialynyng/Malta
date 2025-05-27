import discord
import os
from discord.ext import commands
from cogs.exp_voice import setup as setup_voice_exp
from cogs.admin_config import (
    GUILD_ID, WELCOME_CHANNEL_ID
)

TOKEN = os.getenv("TOKEN")
INTENTS = discord.Intents.default()
INTENTS.messages = True
INTENTS.guilds = True
INTENTS.message_content = True
INTENTS.members = True

class MaltaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)

    async def setup_hook(self):
        print("Loading 🚂CRPG cogs...")
        guild = discord.Object(id=GUILD_ID)
        await self.load_extension("cogs.admin_config")
        await self.load_extension("cogs.admin_group")
        await self.load_extension("cogs.exp_utils")
        await self.load_extension("cogs.exp_engine")
        await self.load_extension("cogs.exp_commands")
        await self.load_extension("cogs.exp_background")
        await self.load_extension("cogs.ActivityAnalyzer")
        await self.load_extension("cogs.exp_multi_autoupdate")
        print("Loading 🍯Store cogs...")
        await self.load_extension("cogs.store.store_utils")
        await self.load_extension("cogs.store.store_upkeep")
        await self.load_extension("cogs.store.store_search")
        await self.load_extension("cogs.store.store_group")
        print("Loading 👤Character cogs...")
        await self.load_extension("cogs.character.user_inventory")
        await self.load_extension("cogs.character.user_inventory_group")
        await self.load_extension("cogs.character.user_trigger")
        await self.load_extension("cogs.character.inventory_utils")
        await setup_voice_exp(self)
        
        from cogs.exp_background import setup_crpg
        await setup_crpg(self)

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


@bot.tree.command(name="help", description="🏴📕 - Shows available commands for Malta Bot.")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "# **🏴☩ Malta Bot**\n\n"
        "## __[CRPG]__\n\n"
        "⚗️📊 /crpg stats - View your current level, EXP, gold, and retirement progress.\n\n"
        "⚗️🧾 /crpg profile <user> - View another player's profile.\n\n"
        "⚗️🏆 /crpg leaderboard - Show the top 10 players by level and EXP.\n\n"
        "⚗️🪦 /crpg retire - Retire your character between levels 31–38 for permanent heirloom bonuses.\n\n"
        "⚗️⚡ /crpg cooldown - Check how much time remains before you can earn your next experience & gold tick.\n\n"
        "⚗️🏔️ /crpg multipliers — View your current daily and generational multipliers.\n\n"
        "## __[SHOP]__\n\n"
        "🍯🛒 /shop open - Open Malta's CRPG item shop UI.\n\n"
        "🍯🔍 /shop filter <damage_type> <weapon_type> - Filter shop weapons by damage and type.\n\n"
        "🍯📘 /shop info <item_id> - View detailed information about a specific item.\n\n"
        "🍯💰 /shop sell <item_id> - Sell an unequipped item for 60% of its value.\n\n"
        "🍯🎲 /shop roll - Roll for a random, unclaimed Title.\n\n"
        "## __[INVENTORY]__\n\n"
        "👤🎒 /user inventory - View all your equipped and unequipped items.\n\n"
        "👤✅📦 /user equip <item_id> - Equip an item from your inventory.\n\n"
        "👤❌📦 /user unequip <item_id> - Unequip an equipped item (titles cannot be unequipped).\n\n"
        "👤🎁 /user gift <item_id> <@user> - Gift an unequipped item to another player.\n\n"
        "## __[UTILITY]__\n\n"
        "📕 /help - Show this help message.\n\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)