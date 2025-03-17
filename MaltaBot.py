import os
import discord
from discord.ext import commands

# Load environment variables
TOKEN = os.getenv('BOT_TOKEN')
APPROVED_IDS = [int(uid.strip()) for uid in os.getenv('APPROVED_IDS', '').split(',')]

# Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Store saved messages per user
saved_messages = {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def save(ctx):
    """Save a draft message (including attachments) to post later."""
    if ctx.author.id not in APPROVED_IDS:
        await ctx.send("❌ You are not authorized to use this bot.")
        return

    saved_messages[ctx.author.id] = {
        "content": ctx.message.content.replace("!save", "").strip(),
        "attachments": ctx.message.attachments
    }

    await ctx.send("✅ Message saved. Use `!postto <channel_id>` to send it.")

@bot.command()
async def postto(ctx, channel_id: int):
    """Post the saved message to a specific channel."""
    if ctx.author.id not in APPROVED_IDS:
        await ctx.send("❌ You are not authorized to use this bot.")
        return

    if ctx.author.id not in saved_messages:
        await ctx.send("⚠️ You haven't saved a message yet. Use `!save` first.")
        return

    post = saved_messages[ctx.author.id]
    channel = bot.get_channel(channel_id)

    if not channel:
        await ctx.send("❌ Could not find the specified channel.")
        return

    try:
        if post["attachments"]:
            files = [await attachment.to_file() for attachment in post["attachments"]]
            msg = await channel.send(content=post["content"], files=files)
        else:
            msg = await channel.send(content=post["content"])

        await ctx.send(f"✅ Message posted to <#{channel.id}>.\n🆔 Message ID: `{msg.id}`")
        del saved_messages[ctx.author.id]
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to send messages to that channel.")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to send message: {e}")

@bot.command()
async def editpost(ctx, message_id: int, *, new_content: str):
    """Edit a specific message sent by the bot (by message ID)."""
    if ctx.author.id not in APPROVED_IDS:
        await ctx.send("❌ You are not authorized to use this bot.")
        return

    for channel in ctx.guild.text_channels:
        try:
            msg = await channel.fetch_message(message_id)
            if msg.author.id == bot.user.id:
                await msg.edit(content=new_content)
                await ctx.send(f"✅ Edited message in <#{channel.id}>.")
                return
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            continue  # Try the next channel

    await ctx.send("❌ Could not find a bot message with that ID.")

# Run the bot
bot.run(TOKEN)
