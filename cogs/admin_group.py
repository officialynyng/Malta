import discord
import io
import os
import asyncio
import sys
from discord import app_commands
from cogs.exp_engine import (on_user_comment,)
from cogs.exp_utils import (get_all_user_ids,)
from cogs.admin_config import (APPROVED_ROLE_NAME, OWNER_ID, GUILD_ID)

class AdminGroup(app_commands.Group):
    def __init__(self, bot):
        super().__init__(name='admin', description='Administration commands')
        self.bot = bot

    @app_commands.command(name="post", description="🔒 - 📋 Post a message and its images from a private channel to another channel.")
    @app_commands.describe(message_id="ID of the original message", destination_channel_id="ID of the destination channel")
    async def post(self, interaction: discord.Interaction, message_id: str, destination_channel_id: str):#
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
            destination_channel = self.bot.get_channel(int(destination_channel_id))
            if destination_channel is None:
                destination_channel = await self.bot.fetch_channel(int(destination_channel_id))

            files = []
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image"):
                    fp = await attachment.read()
                    files.append(discord.File(fp=io.BytesIO(fp), filename=attachment.filename))


            sent_message = await destination_channel.send(content=message.content or None, files=files)
            await interaction.response.send_message(f"Message posted to <#{destination_channel_id}>. Message ID: {sent_message.id}", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Failed to post message: {e}", ephemeral=True)

    @app_commands.command(name="edit", description="🔒 - 🖊️ Edit a previously posted message in a specific channel.")
    @app_commands.describe(destination_channel_id="ID of the channel where the message is posted", message_id="ID of the message to edit", new_content="The new message content")
    async def edit(self, interaction: discord.Interaction, destination_channel_id: str, message_id: str, new_content: str):
        member = interaction.user
        approved = any(role.name == APPROVED_ROLE_NAME for role in member.roles)
        if not approved:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        try:
            channel = self.bot.get_channel(int(destination_channel_id))
            if channel is None:
                channel = await self.bot.fetch_channel(int(destination_channel_id))

            message = await channel.fetch_message(int(message_id))
            await message.edit(content=new_content)
            await interaction.response.send_message("Message updated successfully.", ephemeral=True)

        except discord.NotFound:
            await interaction.response.send_message("Message not found.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to edit that message.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Failed to edit message: {e}", ephemeral=True)

    @app_commands.command(name="structure", description="🔒 - 📁 View the current bot file structure.")
    async def structure(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        structure_text = (
            "📁 **Current Project Structure**\n\n"
            "├── `MaltaBot.py` *(main bot entry point)*\n"
            "├── `requirements.txt` *(Python dependencies)*\n"
            "├── `Procfile` *(Heroku process declaration)*\n"
            "└── `cogs/` *(modular bot components)*\n"
            "    ├── `ActivityAnalyzer.py` *(voice EXP tracking and analysis)*"
            "    ├── `admin_config.py` *(variables for Heroku)*\n"
            "    ├── `admin_group.py` *(Admin Group)*\n"
            "    ├── `exp_background.py` *(CRPG group + background setup)*\n"
            "    ├── `exp_commands.py` *(Discord commands and event listeners)*\n"
            "    ├── `exp_config.py` *(constants, DB engine, and schema)*\n"
            "    ├── `exp_engine.py` *(EXP handling, multiplier logic)*\n"
            "    ├── `exp_utils.py` *(leveling formulas, calculations)*\n"
            "    └── `exp_voice.py` *(CRPG Voice Recognition + Reward)*\n"
        )

        await interaction.response.send_message(structure_text, ephemeral=True)

    @app_commands.command(name="ping", description="🔒 - 🛜 Check if the bot is online and responsive.")
    async def ping(self, interaction: discord.Interaction):
        member = interaction.user
        approved = any(role.name == APPROVED_ROLE_NAME for role in member.roles)
        
        if not approved:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🛜 Responsive... Latency: `{latency_ms}ms`", ephemeral=True)

    @app_commands.command(name="sync", description="🔒 - 🔄 Sync commands with Discord.")
    async def sync(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await interaction.response.send_message("✅ Command tree synced.", ephemeral=True)

    @app_commands.command(name="reload", description="🔒 - 🔄 Reload a bot extension (cog).")
    @app_commands.describe(extension="Name of the extension (e.g., exp_system)")
    async def reload(self, interaction: discord.Interaction, extension: str):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        try:
            await self.bot.reload_extension(extension)
            await interaction.response.send_message(f"🔄 Extension `{extension}` reloaded successfully.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Failed to reload `{extension}`:\n```{e}```", ephemeral=True)

    @app_commands.command(name="restart", description="🔒 - ⏪ Restart the bot.")
    async def restart(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        await interaction.response.send_message("🔄 Restarting the bot...", ephemeral=True)

        # A small delay to allow the message to be sent
        await asyncio.sleep(2)

        # Exit the current process (which will trigger a restart in environments like Heroku)
        os.execv(sys.executable, ['python'] + sys.argv)

    @app_commands.command(name="crpg_multi_check", description="🔒 - 🏔️ Force a multiplier check for all users.")
    async def check_all_multipliers(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        user_ids = get_all_user_ids()
        results = []

        for user_id in user_ids:
            await on_user_comment(user_id, self.bot)

            # Get their updated multiplier from DB
            user_data = get_user_data(user_id)
            display = f"<@{user_id}> — 🏔️ {user_data['daily_multiplier']}x"
            results.append(display)

            await asyncio.sleep(0.1)  # prevent rate limits

        result_text = "\n".join(results)
        await interaction.followup.send(
            content=f"✖️ Multiplier check run for **{len(user_ids)} users**:\n\n{result_text}",
            ephemeral=True
        )


async def setup(bot):
    admin_group = AdminGroup(bot)
    bot.tree.add_command(admin_group)