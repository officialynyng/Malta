import os
from discord.ext import commands  # Correct import statement

class AdminConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

# Environment variables
GUILD_ID = int(os.getenv("GUILD_ID"))
APPROVED_ROLE_NAME = os.getenv("APPROVED_ROLE_NAME")
OWNER_ID = int(os.getenv("OWNER_ID"))
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID"))  # Set this in your environment variables

# The setup function that registers the cog
async def setup(bot):
    await bot.add_cog(AdminConfig(bot))
