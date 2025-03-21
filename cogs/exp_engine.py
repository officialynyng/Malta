import discord
from discord.ext import commands
import time
from cogs.exp_config import (
    db, players, exp_channel, engine, EXP_COOLDOWN, EXP_PER_TICK, GOLD_PER_TICK, LEVEL_CAP, EXP_CHANNEL_ID, TIME_DELTA, MAX_MULTIPLIER,
)
from cogs.exp_utils import (
    get_multiplier, get_user_data, calculate_level, update_user_data, 
)

notified_users = set()

class ExpEngine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def handle_exp_gain(message: discord.Message, level_up_channel_id: int):
    print(f"Handling EXP gain for user: {message.author.id}")
    if message.author.bot:
        return

    user_id = str(message.author.id)
    current_ts = time.time()
    username = str(message.author.display_name)

    with engine.connect() as conn:
        result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

        if result:
            cooldown_remaining = current_ts - result.last_message_ts
            print(f"[DEBUG] Checking cooldown for {username} ({user_id}). Time since last message: {cooldown_remaining:.2f} seconds.")
            if cooldown_remaining < EXP_COOLDOWN:
                print(f"[DEBUG] EXP cooldown active for {username}, ({user_id}). {EXP_COOLDOWN - cooldown_remaining:.2f} seconds remaining before next update.")
                return
            else:
                print(f"[DEBUG] No cooldown active, proceeding with EXP and gold calculation for {username} ({user_id}).")
            # Continue with EXP and gold calculation...
            daily = result.daily_multiplier
            retire = get_multiplier(result.retirements)
            combined_multiplier = daily * retire
            # Calculate rewards
            gained_exp = int(EXP_PER_TICK * combined_multiplier)
            gained_gold = int(GOLD_PER_TICK * combined_multiplier)
            total_exp = result.exp + gained_exp
            new_level = calculate_level(total_exp)
            print(f"[DEBUG] Multiplier applied: {result.daily_multiplier} (daily) × {get_multiplier(result.retirements):.2f} (retirement) = {combined_multiplier:.2f}")

            if result.level >= LEVEL_CAP:
                total_exp = result.exp
                new_level = LEVEL_CAP
                gained_exp = 0

            update = players.update().where(players.c.user_id == user_id).values(
                exp=total_exp,
                gold=result.gold + gained_gold,
                last_message_ts=current_ts,
                level=new_level
            )
            conn.execute(update)
            conn.commit()

            exp_channel = message.guild.get_channel(EXP_CHANNEL_ID)
            await exp_channel.send(
                f"**{message.author.display_name}** gained ⚡ **{gained_exp} EXP** and 💰 **{gained_gold} gold**\n"
                f"🏔️ Daily Multiplier: **{daily:.2f}x**\n"
                f"🧬 Generational Multiplier: **{retire:.2f}x**\n"
                )

            if new_level > result.level:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)
        else:
            daily = 1.0  # Default daily multiplier for new users
            retire = get_multiplier(0)
            combined_multiplier = daily * retire

            gained_exp = int(EXP_PER_TICK * combined_multiplier)
            gained_gold = int(GOLD_PER_TICK * combined_multiplier)
            total_exp = gained_exp
            new_level = calculate_level(total_exp)

            conn.execute(players.insert().values(
                user_id=user_id,
                exp=total_exp,
                gold=gained_gold,
                level=new_level,
                last_message_ts=current_ts,
                retirements=0,
                heirloom_points=0,
                multiplier=0.0,
                daily_multiplier=daily,
                last_multiplier_update=current_ts
            ))
            conn.commit()

            exp_channel = message.guild.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"**{message.author.display_name}** gained ⚡ **{gained_exp} EXP** and 💰 **{gained_gold} gold**\n"
                    f"🏔️ Daily Multiplier: **{daily:.2f}x**\n"
                    f"🧬 Generational Multiplier: **{retire:.2f}x**"
                )

            if new_level > 0:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)



async def on_user_comment(user_id, bot, is_admin_command=False):
    print("[DEBUG] on_user_comment triggered")
    current_time = int(time.time())
    user_data = get_user_data(user_id)

    if user_data:
        last_message_ts = user_data.get('last_message_ts', None)
        last_multiplier_update = user_data.get('last_multiplier_update', 0)
        current_daily_multiplier = user_data['daily_multiplier']

        if last_message_ts is None:
            print(f"[DEBUG] User {user_id} does not have 'last_message_ts'. Skipping multiplier update.")
            return

        print(f"[DEBUG] Last activity: {last_message_ts}, Last multiplier update: {last_multiplier_update}")
        print(f"[DEBUG] Daily Multiplier before update: {current_daily_multiplier}")

        # Only update last activity timestamp without touching the last_multiplier_update when it's an admin command
        if is_admin_command:
            update_user_data(user_id, user_data['multiplier'], current_daily_multiplier, current_time, last_multiplier_update)
        else:
            update_user_data(user_id, user_data['multiplier'], current_daily_multiplier, current_time, current_time)

        # Only process multiplier updates if it's not an admin command
        if not is_admin_command and current_time - last_multiplier_update >= TIME_DELTA:
            if current_time - last_message_ts >= TIME_DELTA:
                new_daily_multiplier = 1
                print(f"[DEBUG] Inactive for 24+ hours — resetting multiplier.")
            elif last_message_ts > last_multiplier_update:
                new_daily_multiplier = min(current_daily_multiplier + 1, MAX_MULTIPLIER)
                print(f"[DEBUG] Active since last multiplier update — increasing multiplier.")
            else:
                new_daily_multiplier = current_daily_multiplier
                print(f"[DEBUG] No new activity since last update — multiplier unchanged.")

            if new_daily_multiplier != current_daily_multiplier:
                update_user_data(user_id, user_data['multiplier'], new_daily_multiplier, current_time, current_time)
                exp_channel = bot.get_channel(EXP_CHANNEL_ID)
                if exp_channel:
                    await exp_channel.send(
                        f"🏔️ <@{user_id}>'s daily multiplier updated to **{new_daily_multiplier}x** due to daily posting."
                    )
                else:
                    print("[ERROR] EXP channel not found.")
            else:
                print(f"[DEBUG] Multiplier unchanged for {user_id}, no update message sent.")
    else:
        print(f"[DEBUG] User data not found for {user_id}. Skipping.")




async def check_and_reset_multiplier(user_id, bot):
    current_time = int(time.time())
    user_data = get_user_data(user_id)
    print(f"[DEBUG] Retrieved user data for {user_id}: {user_data}")

    if user_data:
        time_since_last = current_time - user_data['last_multiplier_update']

        if time_since_last >= TIME_DELTA * 2:
            if user_id in notified_users:
                print(f"[DEBUG] Reset notice already sent for {user_id}, skipping message.")
                return

            # Reset daily multiplier & last_multiplier_update
            update_user_data(user_id, user_data['retirement_multiplier'], 1, current_time, current_time)
            notified_users.add(user_id)

            exp_channel = bot.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"🌋 <@{user_id}>'s daily multiplier has been reset to **1x** due to inactivity."
                )
            print(f"[DEBUG] Reset daily multiplier for {user_id} due to inactivity ({time_since_last} seconds).")

        else:
            if user_id in notified_users:
                notified_users.remove(user_id)  # user became active again, clear flag

    else:
        print(f"[ERROR] User {user_id} not found in database.")



async def award_xp_and_gold(user_id, base_xp, base_gold, bot):
    user_data = get_user_data(user_id)
    if user_data:
        # Retrieve both multipliers
        retirement_multiplier = user_data['multiplier']  # Retirement multiplier
        daily_multiplier = user_data['daily_multiplier']  # Daily activity multiplier

        # Calculate the total multiplier by multiplying the two multipliers
        total_multiplier = retirement_multiplier * daily_multiplier

        # Apply total_multiplier to base XP and gold
        xp_awarded = int(base_xp * total_multiplier)  # Apply total multiplier to base XP
        gold_awarded = int(base_gold * total_multiplier)  # Apply total multiplier to base gold

        # Print to console for debugging
        print(f"Awarded {xp_awarded} XP and {gold_awarded} gold to user <{user_id}> - Multiplier: {daily_multiplier}x")

        # Update the XP and gold in the database
        with engine.connect() as conn:
            update_query = players.update().where(players.c.user_id == user_id).values(
                exp=user_data['exp'] + xp_awarded,
                gold=user_data['gold'] + gold_awarded
            )
            conn.execute(update_query)
            conn.commit()  # Ensure changes are committed to the database

                # Send a message to the designated Discord channel about the XP and gold update
        exp_channel = bot.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            await exp_channel.send(
                f"<{user_id}> has been awarded ⚡ {xp_awarded} XP and 💰 {gold_awarded} gold. "
                f"Total XP is now ⚡ {user_data['exp'] + xp_awarded}, and total gold is 💰 {user_data['gold'] + gold_awarded}. "
                f"Daily Multiplier applied: 🏔️ {daily_multiplier}x, Generational Multiplier applied: 🧬 {retirement_multiplier + 1:.2f}x."
            )
        else:
            print("Failed to connect to Database for User.")


async def announce_level_up(guild: discord.Guild, member: discord.Member, level: int, channel_id: int):
    channel = guild.get_channel(channel_id)
    if channel:
        await exp_channel.send(f"## 🎆 {member.mention} has reached **Level {level}**.")

async def setup(bot):
    await bot.add_cog(ExpEngine(bot))