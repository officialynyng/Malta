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

    @app_commands.command(name="create_invite", description="🔒 - 📨 Create a permanent invite link for the current channel.")
    async def create_invite(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        try:
            invite = await interaction.channel.create_invite(max_age=0, max_uses=0, unique=True)
            await interaction.response.send_message(f"📨 Permanent invite created: {invite.url}", ephemeral=True)
            print(f"[DEBUG]🧷 Permanent invite created by {interaction.user.display_name}: {invite.url}")
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Failed to create invite: {e}", ephemeral=True)
            print(f"[ERROR] Failed to create invite: {e}")

    @app_commands.command(
    name="edit",
    description="🔒 - 🖊️ Replace a message’s content with content from another message."
)
    @app_commands.describe(
        target_message_id="ID of the message to edit",
        target_channel_id="ID of the channel containing the message to edit",
        source_message_id="ID of the message to copy content from",
        source_channel_id="ID of the channel where the source message is posted",
        new_content="(Optional) Custom content to use instead of the source",
        keep_image="(Optional) Keep the image from the source message? Defaults to True."
    )
    async def edit(
        self,
        interaction: discord.Interaction,
        target_message_id: str,
        target_channel_id: str,
        source_message_id: str,
        source_channel_id: str,
        new_content: Optional[str] = None,
        keep_image: bool = True
    ):
        member = interaction.user
        if not any(role.name == APPROVED_ROLE_NAME for role in member.roles):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        print(f"[DEBUG] Edit command by {member.display_name}")

        # Fetch source channel with debug logging
        try:
            source_channel_id_int = int(source_channel_id)
            print(f"[DEBUG] Trying to resolve source_channel_id: {source_channel_id_int}")

            source_channel = self.bot.get_channel(source_channel_id_int)
            if source_channel is None:
                print("[DEBUG] Not in cache — attempting API fetch...")
                source_channel = await self.bot.fetch_channel(source_channel_id_int)

            print(f"[DEBUG] Source channel resolved: {source_channel.name} ({source_channel.id})")

        except discord.NotFound:
            print("[DEBUG] ❌ Channel not found.")
            await interaction.response.send_message("❌ Source channel not found.", ephemeral=True)
            return
        except discord.Forbidden:
            print("[DEBUG] 🚫 Missing permissions for source channel.")
            await interaction.response.send_message("🚫 Bot does not have permission to access the source channel.", ephemeral=True)
            return
        except Exception as e:
            print(f"[DEBUG] ⚠️ Unexpected error resolving channel: {e}")
            await interaction.response.send_message(f"⚠️ Unexpected error resolving source channel: {e}", ephemeral=True)
            return

        # Fetch source message
        try:
            source_message = await source_channel.fetch_message(int(source_message_id))
            print(f"[DEBUG] Source message fetched from channel ID {source_channel_id}")
        except discord.NotFound:
            await interaction.response.send_message("❌ Source message not found.", ephemeral=True)
            return

        # Fetch target channel
        try:
            target_channel = self.bot.get_channel(int(target_channel_id)) or await self.bot.fetch_channel(int(target_channel_id))
            print(f"[DEBUG] Target channel resolved: {target_channel.id}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to fetch target channel: {e}", ephemeral=True)
            return

        # Fetch target message
        try:
            target_message = await target_channel.fetch_message(int(target_message_id))
            print(f"[DEBUG] Target message fetched from channel {target_channel.id}")
        except discord.NotFound:
            await interaction.response.send_message("❌ Target message not found in the specified channel.", ephemeral=True)
            return

            print(f"[DEBUG] Target message fetched from current channel")
        except discord.NotFound:
            await interaction.response.send_message("❌ Target message not found in this channel.", ephemeral=True)
            return

        # Prepare content and optional attachments
        try:
            content_to_use = new_content if new_content else source_message.content
            files = []

            if keep_image and source_message.attachments:
                for attachment in source_message.attachments:
                    file = await attachment.to_file()
                    files.append(file)

            await target_message.edit(content=content_to_use, attachments=files)
            print(f"[DEBUG] Message edited with keep_image={keep_image}")
            await interaction.response.send_message("✅ Message updated successfully.", ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("🚫 I don't have permission to edit that message.", ephemeral=True)
        except discord.HTTPException as e:
            print(f"[DEBUG] HTTPException: {e}")
            await interaction.response.send_message(f"⚠️ Failed to edit message: {e}", ephemeral=True)


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
            "├── `Readme.md` *(Project overview)*\n"
            "└── `cogs/` *(modular bot components)*\n"
            "    ├── `admin_group.py` *(Admin commands)*\n"
            "    ├── `admin_config.py` *(Role, owner, and guild config)*\n"
            "    ├── `exp_background.py` *(Background CRPG handling)*\n"
            "    ├── `exp_commands.py` *(Slash commands and events)*\n"
            "    ├── `exp_config.py` *(Constants, DB engine, schema)*\n"
            "    ├── `exp_engine.py` *(EXP, gold, and multiplier logic)*\n"
            "    ├── `exp_multi_autoupdate.py` *(Daily multiplier scheduler)*\n"
            "    ├── `exp_reminder.py` *(Retirement reminder embed)*\n"
            "    ├── `exp_utils.py` *(Leveling, progression formulas)*\n"
            "    ├── `exp_voice.py` *(Voice activity EXP rewards)*\n"
            "    ├── `ActivityAnalyzer.py` *(Voice XP detection logic)*\n"
            "    ├── `store/` *(Shop system, items, trails, admin tools)*\n"
            "    │   ├── `store_group.py` *(User-facing shop interface)*\n"
            "    │   ├── `store_admin_group.py` *(Admin shop tools)*\n"
            "    │   ├── `store_reminder.py` *(Hourly shop reminder)*\n"
            "    │   ├── `store_search.py` *(Item lookups & previews)*\n"
            "    │   ├── `store_upkeep.py` *(Item state maintenance)*\n"
            "    │   ├── `store_utils.py` *(Inventory and SQL handling)*\n"
            "    │   └── `Items/` *(JSON-backed item directories)*\n"
            "    │       ├── `Titles/`, `Trails/`, `Armor/`, etc.\n"
            "    └── `character/` *(Inventory and equipment logic)*\n"
            "        ├── `user_inventory_group.py` *(User slash commands)*\n"
            "        ├── `user_inventory.py` *(Inventory SQL logic)*\n"
            "        ├── `inventory_utils.py` *(Helper utilities)*\n"
            "        └── `user_trigger.py` *(On-message equip logic)*\n"
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

    @app_commands.command(name="help", description="🔒 - 📕 Show a list of admin commands.")
    async def help(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You must be an admin to use this command.", ephemeral=True)
            return

        help_text = (
            "## __[ADMIN]__\n\n"
            "🔒📋 /admin post <message_id> <channel_id> - Post a previously approved message and its images to a target channel. @Divine\n\n"
            "🔒🖊️ /admin edit <channel_id> <message_id> <new_content> - Edit a previously posted message. @Divine\n\n"
            "🔒🛠️ /admin reload <extension> - Reload a bot extension (cog).\n\n"
            "🔒🔄 /admin sync - Manually sync slash commands with Discord.\n\n"
            "🔒🛜 /admin ping - Check if the bot is online and responsive.\n\n"
            "🔒📁 /admin structure - View the current filestructure of the bot.\n\n"
            "🔒⏪ /admin restart - Restart the bot.\n\n"
            "🔒🧪🌀 /admin crpg_multi_check — Force a multiplier check for all users.\n\n"
            "🔒🧪🏔️ /admin crpg_adjust_daily_multiplier <users> <action> [value] [all] - Manually increase, decrease, or set the daily multiplier for one or more users, or apply to all users in the system.\n\n"
            "🔒🧪💬 /admin crpg_trigger_activity_check — Manually process recent user activity from the database.\n\n"
            "🔒🧪📢 /admin crpg_trigger_voice_check — Manually process all active users in voice channels.\n\n"
        )
        await interaction.response.send_message(help_text, ephemeral=True)

async def setup(bot):
    admin_group = AdminGroup(bot)
    bot.tree.add_command(admin_group)