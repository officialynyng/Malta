import discord
import io
from discord.ext import commands
from discord import app_commands
import os

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
APPROVED_ROLE_NAME = os.getenv("APPROVED_ROLE_NAME")
OWNER_ID = int(os.getenv("OWNER_ID"))
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID"))  # Set this in your environment variables
INTENTS = discord.Intents.default()
INTENTS.messages = True
INTENTS.guilds = True
INTENTS.message_content = True
INTENTS.members = True

class MaltaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)

    async def setup_hook(self):
        print("Loading ExpCommands cog...")
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)  # Sync the commands with the guild directly
        await self.load_extension("exp_system")  # exp_system.py must be in the same directory
        print("ExpCommands cog loaded!")


bot = MaltaBot()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    ###############################
    #Remove to prevent MANUAL sync.
    await bot.tree.sync()
    ###############################
    print("Command tree synced.")

@bot.tree.command(name="post", description="🔒 - Post a message and its images from a private channel to another channel.")
@app_commands.describe(message_id="ID of the original message", destination_channel_id="ID of the destination channel")
async def post(interaction: discord.Interaction, message_id: str, destination_channel_id: str):#
    member = interaction.user
    approved = any(role.name == APPROVED_ROLE_NAME for role in member.roles)
    if not approved:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    try:
        source_channel = interaction.channel  # command must be used in approval channel
        message = await source_channel.fetch_message(int(message_id))
    except discord.NotFound:
        await interaction.response.send_message("Message not found.", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to fetch message: {e}", ephemeral=True)
        return

    try:
        destination_channel = bot.get_channel(int(destination_channel_id))
        if destination_channel is None:
            destination_channel = await bot.fetch_channel(int(destination_channel_id))

        files = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                fp = await attachment.read()
                files.append(discord.File(fp=io.BytesIO(fp), filename=attachment.filename))


        sent_message = await destination_channel.send(content=message.content or None, files=files)
        await interaction.response.send_message(f"Message posted to <#{destination_channel_id}>. Message ID: {sent_message.id}", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Failed to post message: {e}", ephemeral=True)

@bot.tree.command(name="edit", description="🔒 - Edit a previously posted message in a specific channel.")
@app_commands.describe(destination_channel_id="ID of the channel where the message is posted", message_id="ID of the message to edit", new_content="The new message content")
async def edit(interaction: discord.Interaction, destination_channel_id: str, message_id: str, new_content: str):
    member = interaction.user
    approved = any(role.name == APPROVED_ROLE_NAME for role in member.roles)
    if not approved:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return

    try:
        channel = bot.get_channel(int(destination_channel_id))
        if channel is None:
            channel = await bot.fetch_channel(int(destination_channel_id))

        message = await channel.fetch_message(int(message_id))
        await message.edit(content=new_content)
        await interaction.response.send_message("Message updated successfully.", ephemeral=True)

    except discord.NotFound:
        await interaction.response.send_message("Message not found.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to edit that message.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to edit message: {e}", ephemeral=True)

@bot.tree.command(name="structure", description="🔒 - 📁 View the current bot file structure.")
async def structure(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
        return

    structure_text = (
        "📁 **Current Project Structure**\n\n"
        "├── `MaltaBot.py` *(main bot entry point)*\n"
        "├── `exp_system.py` *(experience system cog)*\n"
        "├── `requirements.txt` *(Python dependencies)*\n"
        "└── `Procfile` *(Heroku process declaration)*"
    )

    await interaction.response.send_message(structure_text, ephemeral=True)

@bot.tree.command(name="ping", description="🔒 - 🛜 Check if the bot is online and responsive.")
async def ping(interaction: discord.Interaction):
    member = interaction.user
    approved = any(role.name == APPROVED_ROLE_NAME for role in member.roles)
    
    if not approved:
        await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
        return

    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"🛜 Responsive... Latency: `{latency_ms}ms`", ephemeral=True)

@bot.tree.command(name="sync", description="🔒 - 🔄 Sync commands with Discord.")
async def sync(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
        return

    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await interaction.response.send_message("✅ Command tree synced.", ephemeral=True)

@bot.tree.command(name="reload", description="🔒 - 🔄 Reload a bot extension (cog).")
@app_commands.describe(extension="Name of the extension (e.g., exp_system)")
async def reload(interaction: discord.Interaction, extension: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
        return

    try:
        await bot.reload_extension(extension)
        await interaction.response.send_message(f"🔄 Extension `{extension}` reloaded successfully.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Failed to reload `{extension}`:\n```{e}```", ephemeral=True)


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


@bot.tree.command(name="help", description="🛡️ - Shows available commands for Malta Bot.")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "# **🏴☩ Malta Bot**\n\n"
        "## __[PRIVELEDGED]__ Commands\n\n"
        "🔒 /post <message_id> <channel_id> - Post a previously approved message and its images to a target channel. @Divine\n\n"
        "🔒 /edit <channel_id> <message_id> <new_content> - Edit a previously posted message. @Divine\n\n"
        "🔒 /reload <extension> - Reload a bot extension (cog). @ynyng\n\n"
        "🔒 /sync - Manually sync slash commands with Discord. @ynyng\n\n"
        "🔒 /ping - Check if the bot is online and responsive. @ynyng\n\n"
        "🔒 /structure - View the current filestructure of the bot. @ynyng\n\n"
        "## __[DISCORD CRPG]__ Commands\n\n"
        "⚗️ /stats - View your current level, EXP, gold, and retirement progress.\n\n"
        "⚗️ /profile <user> - View another player's profile.\n\n"
        "⚗️ /leaderboard - Show the top 10 players by level and EXP.\n\n"
        "⚗️ /retire - Retire your character between levels 31-38 for permanent heirloom bonuses.\n\n"
        "⚗️ /cooldown - Check how much time remains before you can earn your next experience & gold tick.\n\n"
        "## __[TECHNICAL]__ Commands\n\n"
        "🛡️ /help - Show this help message.\n\n"
        )
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)