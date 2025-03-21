from discord.ext import commands

from cogs.exp_engine import (
    handle_exp_gain, on_user_comment,
)

from cogs.exp_config import EXP_CHANNEL_ID

class ExpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            channel_name = getattr(message.channel, 'name', 'DM or unknown')
            print(f"[DEBUG] Message received in #{channel_name} by {message.author} (channel ID: {message.channel.id})")

            if message.author.bot:
                print("[DEBUG] Ignored bot message")
                return

            user_id = str(message.author.id)

            # Handle EXP + Leveling
            await handle_exp_gain(message, EXP_CHANNEL_ID)

            # 🔒 Multiplier logic - Only update once per 24h (handled internally)
            await on_user_comment(user_id, self.bot)

        except Exception as e:
            print(f"[ERROR] Exception in on_message: {e}")


    @commands.Cog.listener()
    async def on_ready(self):
        global exp_channel
        exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)
        print(f"[READY] Bot is online. EXP Channel set to: {exp_channel}")


async def setup(bot):
    await bot.add_cog(ExpCommands(bot))