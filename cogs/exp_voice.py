import asyncio
import os
from discord.ext import commands

from exp_config import (
    EXP_CHANNEL_ID,
)

from exp_engine import (
    handle_exp_gain, on_user_comment, check_and_reset_multiplier, 
)

class VoiceExpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_activity_check_task = self.bot.loop.create_task(self.check_voice_activity())
        print("[DEBUG] VoiceExpCog initialized and background task started.")

    def cog_unload(self):
        self.voice_activity_check_task.cancel()  # Proper cleanup on cog unload
        print("[DEBUG] VoiceExpCog unloaded and background task canceled.")

    async def check_voice_activity(self):
        """Task to check for users in voice channels every 15 minutes and process their activity."""
        print("[DEBUG] Background task for checking voice channel activity started.")
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            for guild in self.bot.guilds:
                print(f"[DEBUG] Checking guild: {guild.name} (ID: {guild.id})")
                for vc in guild.voice_channels:
                    print(f"[DEBUG] Checking voice channel: {vc.name} (ID: {vc.id}) with {len(vc.members)} members.")
                    for member in vc.members:
                        if not member.bot:
                            print(f"[DEBUG] Processing member: {member.display_name} (ID: {member.id}) in voice channel.")
                            await self.process_user_activity(self.bot, member.id)
            await asyncio.sleep(900)  # Sleep for 15 minutes

    async def process_user_activity(self, bot, user_id):
        """Process activity for a user, assuming voice channel presence."""
        guild = bot.get_guild(int(os.getenv("GUILD_ID")))
        member = guild.get_member(int(user_id))

        if member is None or member.bot:
            print(f"[DEBUG] Member {user_id} invalid or bot. Skipping.")
            return

        if member.voice and member.voice.channel:
            print(f"[DEBUG] Member {member.display_name} (ID: {user_id}) is still in a voice channel: {member.voice.channel.name}.")
            # Simulate message handling for EXP gain
            fake_message = type('FakeMessage', (object,), {'author': member, 'guild': guild})
            await handle_exp_gain(fake_message, EXP_CHANNEL_ID)
            await on_user_comment(user_id, bot)
            await check_and_reset_multiplier(user_id, bot)
        else:
            print(f"[DEBUG] Member {member.display_name} (ID: {user_id}) is not in a voice channel or has left.")

async def setup(bot):
    await bot.add_cog(VoiceExpCog(bot))
    print("[DEBUG] VoiceExpCog has been added to the bot.")

