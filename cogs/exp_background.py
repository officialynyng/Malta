import asyncio
import discord
import os
import time
from discord import app_commands
from discord.ext import commands
from cogs.exp_utils import get_all_user_ids
from cogs.exp_engine import check_and_reset_multiplier

from cogs.exp_config import (
    EXP_CHANNEL_ID, TIME_DELTA,
    EXP_COOLDOWN,
    engine, players, db,
)

from cogs.exp_utils import (
    get_multiplier, get_heirloom_points, get_user_data,
)

from cogs.exp_engine import (
    handle_exp_gain, on_user_comment, check_and_reset_multiplier,
)

class ExpBackground(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def start_multiplier_cleanup(bot):
    await bot.wait_until_ready()
    print("[🌀] Multiplier reset loop started.")

    while not bot.is_closed():
        user_ids = get_all_user_ids()
        print(f"[⏳] Checking {len(user_ids)} users for multiplier resets...")

        updated_count = 0
        for user_id in user_ids:
            before = asyncio.get_event_loop().time()
            await check_and_reset_multiplier(user_id, bot)
            after = asyncio.get_event_loop().time()
            if after - before > 0.1:
                print(f"[✅] Processed {user_id} in {after - before:.2f}s")
            await asyncio.sleep(0.25)  # space out checks

        print(f"[🌀🏁🌀] Multiplier check cycle complete. {len(user_ids)} users checked.")
        await asyncio.sleep(3600)  # wait 1 hour before next run


exp_channel = None
last_leaderboard_timestamp = 0

class CRPGGroup(app_commands.Group):
    def __init__(self, bot):
        super().__init__(name="crpg", description="CRPG system commands.")
        self.bot = bot

    @app_commands.command(name="retire", description="⚗️ -  Retire your character between levels 31-38 for heirloom bonuses.")
    async def retire(self, interaction: discord.Interaction):

        user_id = str(interaction.user.id)
        exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)  # Ensure EXP_CHANNEL_ID is defined

        with engine.connect() as conn:
            result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

            if not result:
                await interaction.response.send_message(
                    "⚠️ You have no EXP record yet. Start participating to gain experience.",
                    ephemeral=True
                )
                return

            if result.level < 31 or result.level > 38:
                await interaction.response.send_message(
                    "⚠️ You can only retire between levels 31 - 38.", ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"🛡️ Are you sure you want to retire? You will reset your level, EXP, and gold.\n"
                f"Type your username (`{interaction.user.name}`) to confirm.",
                ephemeral=True
            )

            def check(m):
                return m.author == interaction.user and m.content == interaction.user.name

            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                await interaction.followup.send("🏰 Retirement cancelled (timeout).", ephemeral=True)
                return


            heirloom_gain = get_heirloom_points(result.level)
            new_retire_count = result.retirements + 1
            new_total_heirlooms = result.heirloom_points + heirloom_gain
            multiplier = get_multiplier(new_retire_count)

            bonus_note = ""
            if new_retire_count > 16:
                bonus_note = "⚖️ Multiplier is capped at 1.48x, but you still can earn heirloom point(s)."

            conn.execute(players.update().where(players.c.user_id == user_id).values(
                exp=0,
                level=0,
                retirements=new_retire_count,
                heirloom_points=new_total_heirlooms
            ))
            conn.commit()

            if exp_channel:
                await exp_channel.send(
                    f"🎖️ {interaction.user.mention} has retired and earned 🪙 **{heirloom_gain} heirloom point(s)**!\n"
                    f"Total retirements: `{new_retire_count}` → Multiplier: `{multiplier:.2f}x`\n"
                    f"All progress reset. Start your journey anew!\n"
                    f"{bonus_note}"
                )


    @app_commands.command(name="stats", description="⚗️ -  View your own stats (level, gold, EXP, etc.)")
    async def stats(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        with engine.connect() as conn:
            query = players.select().where(players.c.user_id == user_id)
            result = conn.execute(query).fetchone()

            if not result:
                await interaction.response.send_message("You have no stats yet.", ephemeral=True)
                return

            level = result.level
            exp = result.exp
            gold = result.gold
            retirements = result.retirements
            heirloom_points = result.heirloom_points

            await interaction.response.send_message(
                f"📜 Stats for **{interaction.user.display_name}'s Profile**\n"
                f"🌌 Level: {level}\n⚡ EXP: {exp}\n💰 Gold: {gold}\n"
                f"🌱 Generation: {retirements}\n🪙 Heirloom Points: {heirloom_points}",
                ephemeral=True
            )



    @app_commands.command(name="profile", description="⚗️ -  View another player's profile")
    @app_commands.describe(user="The user whose profile you want to see")
    async def profile(self, interaction: discord.Interaction, user: discord.User):
        user_id = str(user.id)

        with engine.connect() as conn:
            result = conn.execute(players.select().where(players.c.user_id == user_id)).fetchone()

            if not result:
                await interaction.response.send_message(f"{user.display_name} has no stats yet.", ephemeral=True)
                return

            level = result.level
            exp = result.exp
            gold = result.gold
            retirements = result.retirements
            heirloom_points = result.heirloom_points

            await interaction.response.send_message(
                f"📜 **{user.display_name}'s Profile**\n"
                f"🌌 Level: {level}\n⚡ EXP: {exp}\n💰 Gold: {gold}\n"
                f"🌱 Generation: {retirements}\n🪙 Heirloom Points: {heirloom_points}",
                ephemeral=True
            )


    @app_commands.command(name="leaderboard", description="⚗️ - 📜 Show top 10 players by generation, level, gold, and EXP.")
    async def leaderboard(self, interaction: discord.Interaction):
        global last_leaderboard_timestamp

        now = time.time()
        cooldown_seconds = 600  # 10 minutes

        if now - last_leaderboard_timestamp < cooldown_seconds:
            remaining = int(cooldown_seconds - (now - last_leaderboard_timestamp))
            await interaction.response.send_message(
                f"⏳ Leaderboard is on cooldown. Try again in {remaining} seconds.",
                ephemeral=True
            )
            return

        last_leaderboard_timestamp = now

        exp_channel = self.bot.get_channel(EXP_CHANNEL_ID)

        # Ensure exp_channel is correctly assigned
        if not exp_channel:
            await interaction.response.send_message("Error: Leaderboard channel not found.", ephemeral=True)
            return

        with engine.connect() as conn:
            query = players.select().order_by(
                players.c.retirements.desc(),
                players.c.level.desc(),
                players.c.gold.desc(),
                players.c.exp.desc()
            ).limit(10)
            results = conn.execute(query).fetchall()

            if not results:
                await exp_channel.send("No players on the leaderboard yet.")
            else:
                leaderboard_text = "**📜 Leaderboard**\n\n"
                for i, result in enumerate(results, start=1):
                    user_id = result.user_id
                    user = await self.bot.fetch_user(user_id)
                    name = user.display_name
                    exp = result.exp
                    level = result.level
                    gold = result.gold
                    retirements = result.retirements

                    leaderboard_text += (
                        f"**{i}. {name}**\n"
                        f"🌱 Generation: {retirements}\n"
                        f"🌌 Level: {level}\n"
                        f"💰 Gold: {gold}\n"
                        f"⚡ EXP: {exp}\n"
                    )

                await exp_channel.send(leaderboard_text)

        # Respond to the user to confirm the leaderboard has been posted
        await interaction.response.send_message("Leaderboard has been updated in the designated channel.", ephemeral=True)



    @app_commands.command(name="cooldown", description="⚗️ - Check how long until your next ⚡ experience & 💰 gold tick.")
    async def cooldown(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_ts = time.time()

        with engine.connect() as conn:
            result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

            if result:
                elapsed_time = current_ts - result.last_message_ts
                remaining_cooldown = EXP_COOLDOWN - elapsed_time

                if remaining_cooldown > 0:
                    minutes, seconds = divmod(int(remaining_cooldown), 60)
                    await interaction.response.send_message(
                        f"⏳ You have **{minutes} minutes & {seconds} seconds** left until your next available ⚡ experience & 💰 gold tick.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "You're ready for your next ⚡ experience & 💰 gold tick.",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "You have no EXP record yet. Start participating to earn ⚡ experience & 💰 gold.",
                    ephemeral=True
                )

    @app_commands.command(name="multipliers", description="⚗️ - Your multiplier information.")
    async def next_multiplier(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        current_time = int(time.time())
        user_data = get_user_data(user_id)

        if not user_data:
            await interaction.response.send_message("You have no EXP record yet. Start participating to gain experience.", ephemeral=True)
            return

        last_activity = user_data['last_message_ts']
        daily_multiplier = user_data['daily_multiplier']  # Using the daily multiplier
        retirement_multiplier = user_data['multiplier']  # Using the retirement multiplier
        time_since_last_activity = current_time - last_activity

        if time_since_last_activity < TIME_DELTA:
            time_until_update = TIME_DELTA - time_since_last_activity
            hours, remainder = divmod(time_until_update, 3600)
            minutes, seconds = divmod(remainder, 60)
            await interaction.response.send_message(
                f"""## Daily: 🏔️ **{daily_multiplier}x**
            ## Generational: 🧬 **{retirement_multiplier + 1:.2f}x**

            Your next daily multiplier update is in __{int(hours)}__ hours, __{int(minutes)}__ minutes, and __{int(seconds)}__ seconds.""",
                ephemeral=True
            )
        else:
            # If more than a day has passed since the last activity, the multiplier can be updated immediately
            await interaction.response.send_message(
                f"""## Current Daily: 🏔️ **{daily_multiplier}x**
            ## Current Generational: 🧬 **{retirement_multiplier + 1:.2f}x**

            Your daily multiplier update is available now. ephemeral=True)"""
            )


async def process_user_activity(bot, user_id):
    guild = bot.get_guild(int(os.getenv("GUILD_ID")))
    member = guild.get_member(int(user_id))

    if member is None or member.bot:
        print(f"[DEBUG] Member {user_id} invalid or bot. Skipping.")
        return

    # Creating a minimal fake message object for existing compatibility
    class FakeMessage:
        def __init__(self, author, guild):
            self.author = author
            self.guild = guild

    fake_message = FakeMessage(author=member, guild=guild)

    # Directly invoke existing complete logic
    await handle_exp_gain(fake_message, EXP_CHANNEL_ID)
    await on_user_comment(user_id, bot)
    await check_and_reset_multiplier(user_id, bot)


async def setup_crpg(bot):
    print("Loading ExpCommands cog...")
    crpg_group = CRPGGroup(bot)
    bot.tree.add_command(crpg_group)
    print("ExpCommands cog and CRPGGroup commands loaded!")

async def setup(bot):
    await bot.add_cog(ExpBackground(bot))