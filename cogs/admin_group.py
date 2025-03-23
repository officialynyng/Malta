import discord
import io
import os
import asyncio
import sys
import time
from typing import (Optional,)
from discord import (app_commands,)
from cogs.exp_engine import (on_user_comment,)
from cogs.exp_utils import (get_all_user_ids, get_user_data, update_user_data,)
from cogs.admin_config import (APPROVED_ROLE_NAME, OWNER_ID, GUILD_ID)
from cogs.exp_config import (
    db
)
from cogs.exp_engine import is_happy_hour
class AdminGroup(app_commands.Group):
    def __init__(self, bot):
        super().__init__(name='admin', description='Administration commands')
        self.bot = bot

    @app_commands.command(name="post", description="🔒 - 📋 Post a message and its images from a private channel to another channel.")
    @app_commands.describe(message_id="ID of the original message", destination_channel_id="ID of the destination channel")
    async def post(self, interaction: discord.Interaction, message_id: str, destination_channel_id: str):
        member = interaction.user
        approved = any(role.name == APPROVED_ROLE_NAME for role in member.roles)
        if not approved:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        # Debug: Starting command process
        print(f"[DEBUG] {member.display_name} initiated the post command for message ID {message_id} to channel ID {destination_channel_id}")

        try:
            source_channel = interaction.channel  # Command must be used in the approval channel
            message = await source_channel.fetch_message(int(message_id))
            # Debug: Message fetched successfully
            print(f"[DEBUG] Successfully fetched message from source channel {source_channel.id}")
        except discord.NotFound:
            await interaction.response.send_message("❌ Message not found.", ephemeral=True)
            return
        except discord.HTTPException as e:
            await interaction.response.send_message(f"⚠️ Failed to fetch message: {e}", ephemeral=True)
            return

        try:
            destination_channel = self.bot.get_channel(int(destination_channel_id))
            if destination_channel is None:
                destination_channel = await self.bot.fetch_channel(int(destination_channel_id))

            # Debug: Checking if destination channel is resolved
            if destination_channel:
                print(f"[DEBUG] Destination channel resolved: {destination_channel.id}")
            else:
                print(f"[DEBUG] Failed to resolve destination channel ID: {destination_channel_id}")

            files = []
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image"):
                    fp = await attachment.read()
                    files.append(discord.File(fp=io.BytesIO(fp), filename=attachment.filename))
                    # Debug: Attachment prepared for sending
                    print(f"[DEBUG] Prepared attachment: {attachment.filename}")

            sent_message = await destination_channel.send(content=message.content or None, files=files)
            # Debug: Message posted successfully
            print(f"[DEBUG] Message posted successfully to {destination_channel_id} with Message ID: {sent_message.id}")
            await interaction.response.send_message(f"✅ Message posted to <#{destination_channel_id}>. Message ID: {sent_message.id}", ephemeral=True)

        except Exception as e:
            # Debug: Posting failed
            print(f"[DEBUG] Failed to post message: {e}")
            await interaction.response.send_message(f"⚠️ Failed to post message: {e}", ephemeral=True)


    @app_commands.command(name="edit", description="🔒 - 🖊️ Replace a message’s content with content from another message.")
    @app_commands.describe(
        target_message_id="ID of the message to edit",
        source_message_id="ID of the message to copy content from",
        source_channel_id="ID of the channel where the source message is posted",
        new_content="(Optional) Custom content to use instead of the source"
    )
    async def edit(
        self,
        interaction: discord.Interaction,
        target_message_id: str,
        source_message_id: str,
        source_channel_id: str,
        new_content: Optional[str] = None
    ):
        member = interaction.user
        approved = any(role.name == APPROVED_ROLE_NAME for role in member.roles)
        if not approved:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        # Debug: Command initialization
        print(f"[DEBUG] Edit command initiated by {member.display_name}")

        try:
            # Fetch the source message from the specified source channel
            source_channel = self.bot.get_channel(int(source_channel_id)) or await self.bot.fetch_channel(int(source_channel_id))
            source_message = await source_channel.fetch_message(int(source_message_id))
            # Debug: Source message fetched
            print(f"[DEBUG] Source message fetched from channel ID {source_channel_id}")
        except discord.NotFound:
            await interaction.response.send_message("❌ Source message or channel not found.", ephemeral=True)
            return

        try:
            # Fetch the target message from the current channel (assuming the target is in the same channel as command used)
            target_message = await interaction.channel.fetch_message(int(target_message_id))
            # Debug: Target message fetched
            print(f"[DEBUG] Target message fetched from current channel")
        except discord.NotFound:
            await interaction.response.send_message("❌ Target message not found in this channel.", ephemeral=True)
            return

        try:
            # Use override content if provided, otherwise use content from source message
            updated_content = new_content if new_content else source_message.content
            await target_message.edit(content=updated_content)
            # Debug: Message updated successfully
            print(f"[DEBUG] Message updated successfully with new content")
            await interaction.response.send_message("✅ Message updated successfully.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("🚫 I don't have permission to edit that message.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"⚠️ Failed to edit message: {e}", ephemeral=True)
            # Debug: Failed to edit message
            print(f"[DEBUG] Failed to edit message due to HTTPException: {e}")



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
        
        print(f"[DEBUG]🛜 Ping command used by {member.display_name} | Latency: {latency_ms}ms")

        await interaction.response.send_message(f"🛜 Responsive... Latency: `{latency_ms}ms`", ephemeral=True)


    @app_commands.command(name="sync", description="🔒 - 🔄 Sync commands with Discord.")
    async def sync(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        # Perform the synchronization
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        
        # Debug statement with emoji
        print(f"[DEBUG]🔄 Commands synced by {interaction.user.display_name}")

        await interaction.response.send_message("✅ Command tree synced.", ephemeral=True)


    @app_commands.command(name="reload", description="🔒 - 🔄 Reload a bot extension (cog).")
    @app_commands.describe(extension="Name of the extension (e.g., exp_system)")
    async def reload(self, interaction: discord.Interaction, extension: str):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        try:
            await self.bot.reload_extension(extension)
            # Debug statement with emoji
            print(f"[DEBUG]🔄  Extension `{extension}` reloaded by {interaction.user.display_name}")
            await interaction.response.send_message(f"🔄 Extension `{extension}` reloaded successfully.", ephemeral=True)
        except Exception as e:
            print(f"[DEBUG]⚠️  Failed to reload `{extension}` by {interaction.user.display_name}: {e}")
            await interaction.response.send_message(f"⚠️ Failed to reload `{extension}`:\n```{e}```", ephemeral=True)


    @app_commands.command(name="restart", description="🔒 - ⏪ Restart the bot.")
    async def restart(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        # Debug statement with emoji
        print(f"[DEBUG]⏪ Restart command issued by {interaction.user.display_name}")

        await interaction.response.send_message("🔄 Restarting the bot...", ephemeral=True)

        # A small delay to allow the message to be sent
        await asyncio.sleep(2)

        # Exit the current process (which will trigger a restart in environments like Heroku)
        os.execv(sys.executable, ['python'] + sys.argv)


    @app_commands.command(name="crpg_multi_check", description="🔒 - 🧪🌀 Force a multiplier check for all users.")
    async def check_all_multipliers(self, interaction: discord.Interaction):
        # Debug: Log the interaction user and command initiation
        print(f"[DEBUG]🌀 Forcing multiplier check: {interaction.user.id}")

        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You do not have permission to use this command.", ephemeral=True)
            return

        # Proceed with command execution
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Fetch all user IDs
        user_ids = get_all_user_ids()
        print(f"[DEBUG] Total users fetched: {len(user_ids)}")  # Debug: Log total number of users

        results = []

        for user_id in user_ids:
            # Debug: Log user ID being processed
            print(f"[DEBUG] Processing user ID: {user_id}")
            await on_user_comment(user_id, self.bot)

            # Fetch updated multiplier from database
            user_data = get_user_data(user_id)
            if not user_data:
                print(f"[ERROR] No user data found for user ID: {user_id}")  # Debug: Error if no data found
                continue

            display = f"<@{user_id}> — 🏔️ Daily: {user_data['daily_multiplier']}x"
            results.append(display)

            # Debug: Log successful processing of user data
            print(f"[DEBUG] Updated multiplier for user ID {user_id}: {user_data['daily_multiplier']}x")

            await asyncio.sleep(0.1)  # prevent rate limits

        result_text = "\n".join(results)
        # Debug: Log final result text
        print(f"[DEBUG]🌀 Final result text for multiplier check: {result_text}")

        await interaction.followup.send(
            content=f"✖️ Multiplier check run for **{len(user_ids)} users**:\n\n{result_text}",
            ephemeral=True
        )


    @app_commands.command(name="crpg_adjust_daily_multiplier", description="🔒 - 🧪🏔️ Manually adjust daily multipliers.")
    @app_commands.describe(
        users="Mention one user to update (optional)",
        value="The value to set the daily multiplier to",
        all="Apply to all users (optional)"
    )
    async def adjust_daily_multiplier(
        self,
        interaction: discord.Interaction,
        users: Optional[discord.User] = None,
        value: int = None,
        all: bool = False
    ):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You do not have permission to use this command.", ephemeral=True)
            return

        if value is None:
            await interaction.response.send_message("❌ You must provide a value when using 'set'.", ephemeral=True)
            return

        if users and all:
            await interaction.response.send_message("❌ You cannot specify both a user and `all: true`. Please choose one.", ephemeral=True)
            return
        elif not users and not all:
            await interaction.response.send_message("❌ You must specify either a user or use `all: true`.", ephemeral=True)
            return

        # Debug: Starting the adjustment process
        print(f"[DEBUG]🔧 Starting multiplier adjustment by {interaction.user.display_name}, Value: {value}, All: {all}")

        await interaction.response.defer(ephemeral=True)

        user_ids = []
        if all:
            user_ids = get_all_user_ids()
            print(f"[DEBUG]🔧 Applying to all users, total: {len(user_ids)}")  # Debug: Total users affected
        elif users:
            user_ids = [str(users.id)]
            print(f"[DEBUG]🔧 Applying to specific user ID: {users.id}")  # Debug: Specific user affected

        updates = []
        for user_id in user_ids:
            user_data = get_user_data(user_id)
            if not user_data:
                updates.append(f"⚠️ <@{user_id}> — not found in DB.")
                continue

            current = user_data['daily_multiplier']
            new = max(1, min(value, 5))

            # Debug: Before updating user data
            print(f"🔧 [DEBUG] Updating {user_id} from {current}x to {new}x")

            # Do NOT update last_multiplier_update
            update_user_data(
                user_id,
                user_data['multiplier'],
                new,
                user_data['last_message_ts'],  # preserve existing last activity
                last_multiplier_update=None    # indicate no update
            )

            updates.append(f"✖️ <@{user_id}> — 🏔️ {current}x ➜ {new}x")

        summary = "\n".join(updates)
        await interaction.followup.send(f"Daily multiplier adjustment:\n{summary}", ephemeral=True)

        # Debug: Summary of changes
        print(f"[DEBUG]🔧 Multiplier adjustments completed:\n{summary}")

    @app_commands.command(name="crpg_trigger_activity_check", description="🔒 - 🧪💬 Manually run the recent ActivityAnalyzer check.")
    async def trigger_activity_check(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        try:
            from cogs.ActivityAnalyzer import ActivityToExpProcessor
            cog = self.bot.get_cog("ActivityToExpProcessor")
            if cog:
                # Get guild and pending activity before triggering
                guild = self.bot.get_guild(GUILD_ID)
                engine = cog.engine
                table = cog.recent_activity
                with engine.begin() as conn:
                    results = conn.execute(db.select(table)).fetchall()
                    if not results:
                        await interaction.response.send_message("🧼 No users in recent activity queue. Nothing to process.", ephemeral=True)
                        return

                    users = []
                    for row in results:
                        users.append(f"👤 <@{row.user_id}>")

                await cog.process_recent_activity()
                user_list = "\n".join(users)
                await interaction.response.send_message(
                    f"⚙️ Activity check complete — processed `{len(users)}` users:\n{user_list}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("💀 ActivityAnalyzer cog not found.", ephemeral=True)
        except Exception as e:
            print(f"[ERROR] Failed to run manual activity check: {e}")
            await interaction.response.send_message(f"💢 Failed to run manual activity check:\n```{e}```", ephemeral=True)

    @app_commands.command(name="crpg_trigger_voice_check", description="🔒 - 🧪📢 Manually trigger VoiceExpCog check.")
    async def trigger_voice_check(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        try:
            from cogs.exp_voice import VoiceExpCog
            cog = self.bot.get_cog("VoiceExpCog")
            if not cog:
                await interaction.response.send_message("💀 VoiceExpCog not found.", ephemeral=True)
                return

            processed = []
            for guild in self.bot.guilds:
                for vc in guild.voice_channels:
                    for member in vc.members:
                        if not member.bot:
                            await cog.process_user_activity(self.bot, member.id)
                            processed.append(f"🔊 <@{member.id}> in `#{vc.name}`")

            if not processed:
                await interaction.response.send_message("🔕 No eligible users found in voice channels.", ephemeral=True)
                return

            result = "\n".join(processed)
            await interaction.response.send_message(
                f"📢 Voice check complete — processed `{len(processed)}` users:\n{result}",
                ephemeral=True
            )

        except Exception as e:
            print(f"[ERROR] Failed to run manual voice check: {e}")
            await interaction.response.send_message(f"💢 Failed to run voice check:\n```{e}```", ephemeral=True)

    @app_commands.command(name="check_happy_hour", description="🔒 - 🕒 Check if it's currently Happy Hour.")
    async def check_happy_hour(self, interaction: discord.Interaction):
        # Ensure only the admin can use this command
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        # Check if it's Happy Hour
        if is_happy_hour():
            await interaction.response.send_message("🍾🍸 **Happy Hour is LIVE!** EXP and 💰 gold are doubled until 11:30 PM CST!", ephemeral=True)
        else:
            await interaction.response.send_message("💤 **Happy Hour is NOT active.**", ephemeral=True)
        



async def setup(bot):
    admin_group = AdminGroup(bot)
    bot.tree.add_command(admin_group)