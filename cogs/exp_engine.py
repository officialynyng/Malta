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
    print(f"🚂 - ⚡⚡⚡(H_E_G) Handling EXP gain for user: {message.author.id} ⚡⚡⚡")
    if message.author.bot:
        return

    user_id = str(message.author.id)
    current_ts = time.time()
    username = str(message.author.display_name)

    with engine.connect() as conn:
        result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

        if result:
            cooldown_remaining = current_ts - result.last_message_ts
            print(f"[DEBUG]🚂 - 🥶🔥 Checking cooldown for {username} ({user_id}). Time since last message: {cooldown_remaining:.2f} seconds.")
            if cooldown_remaining < EXP_COOLDOWN:
                print(f"[DEBUG]🚂 - ❄️❄️❄️ EXP cooldown active for {username}, ({user_id}). {EXP_COOLDOWN - cooldown_remaining:.2f} seconds remaining before next update.❄️❄️❄️")
                return
            else:
                print(f"[DEBUG]🚂 - 🍾 No cooldown active, proceeding with EXP and gold calculation for {username} ({user_id}).")
            # Continue with EXP and gold calculation...
            daily = result.daily_multiplier
            retire = get_multiplier(result.retirements)
            combined_multiplier = daily * retire
            # Calculate rewards
            gained_exp = int(EXP_PER_TICK * combined_multiplier)
            gained_gold = int(GOLD_PER_TICK * combined_multiplier)
            total_exp = result.exp + gained_exp
            new_level = calculate_level(total_exp)
            print(f"[DEBUG]🚂 - ✖️☑️ Multiplier applied: {result.daily_multiplier} (daily) × {get_multiplier(result.retirements):.2f} (retirement) = {combined_multiplier:.2f}")

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



async def on_user_comment(user_id, bot, is_admin=False):
    print("[DEBUG]🚂 -  on_user_comment triggered, Admin Command: " + str(is_admin))
    current_time = int(time.time())
    user_data = get_user_data(user_id)

    if not user_data:
        print(f"[DEBUG]🚂 - 🏔️ No user data found for {user_id}.")
        return

    if is_admin:
        print("[DEBUG]🚂 - 🏔️ Admin check, not updating multiplier or timestamps.")
        return

    last_message_ts = user_data.get('last_message_ts', None)
    last_multiplier_update = user_data.get('last_multiplier_update', 0)
    current_daily_multiplier = user_data['daily_multiplier']

    if last_message_ts is None:
        print(f"[DEBUG]🚂 - User {user_id} does not have 'last_message_ts'. Skipping multiplier update.")
        return

    print(f"[DEBUG]🚂 - 🏔️ Last activity: {last_message_ts}, Last multiplier update: {last_multiplier_update}")
    print(f"[DEBUG]🚂 - 🏔️ Daily Multiplier before update: {current_daily_multiplier}")

    if current_time - last_multiplier_update >= TIME_DELTA:
        if current_time - last_message_ts >= TIME_DELTA:
            new_daily_multiplier = 1
            print(f"[DEBUG]🚂 - 🌋 Inactive for 24+ hours — resetting multiplier to baseline.")

            update_user_data(user_id, user_data['multiplier'], new_daily_multiplier, last_message_ts, current_time)
            exp_channel = bot.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"🌋 <@{user_id}>'s daily multiplier has been reset to **1x** due to inactivity."
                )
        else:
            new_daily_multiplier = min(current_daily_multiplier + 1, MAX_MULTIPLIER)
            print(f"[DEBUG]🚂 - 🏔️ Active within 24h — potentially increasing multiplier to {new_daily_multiplier}.")

            if new_daily_multiplier != current_daily_multiplier:
                update_user_data(user_id, user_data['multiplier'], new_daily_multiplier, last_message_ts, current_time)
                exp_channel = bot.get_channel(EXP_CHANNEL_ID)
                if exp_channel:
                    await exp_channel.send(
                        f"🏔️ <@{user_id}>'s daily multiplier updated to **{new_daily_multiplier}x** due to daily posting."
                    )
            else:
                print(f"[DEBUG] Multiplier unchanged for {user_id}, no update message sent.")
    else:
        print("[DEBUG]🚂 - Less than 24h since last update, not updating multiplier.")

async def check_and_reset_multiplier(user_id, bot):
    current_time = int(time.time())
    user_data = get_user_data(user_id)
    print(f"[DEBUG]🚂 - Retrieved user data for {user_id}: {user_data}")

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
            print(f"[DEBUG]🚂 - 🌋 Reset daily multiplier for {user_id} due to inactivity ({time_since_last} seconds).")

        else:
            if user_id in notified_users:
                notified_users.remove(user_id)  # user became active again, clear flag

    else:
        print(f"[ERROR]🚂 - User {user_id} not found in database.")



async def award_xp_and_gold(user_id, base_xp, base_gold, bot):
    user_data = get_user_data(user_id)
    if user_data:
        # Retrieve both multipliers
        retirement_multiplier = user_data['multiplier']  # Stored as a float like 0.45
        daily_multiplier = user_data['daily_multiplier']  # Usually 1-5

        # Correct calculation: Add 1 to retirement multiplier
        total_multiplier = (retirement_multiplier + 1) * daily_multiplier

        # Calculate awarded XP and gold
        xp_awarded = int(base_xp * total_multiplier)
        gold_awarded = int(base_gold * total_multiplier)

        # Print debug info
        print(f"[DEBUG]🚂 - ⚡⚡⚡(A_x_a_g) Awarded {xp_awarded} XP and {gold_awarded} gold to <{user_id}> — Total Multiplier: {total_multiplier:.2f}x ⚡⚡⚡")

        # Update XP and gold in DB
        with engine.connect() as conn:
            update_query = players.update().where(players.c.user_id == user_id).values(
                exp=user_data['exp'] + xp_awarded,
                gold=user_data['gold'] + gold_awarded
            )
            conn.execute(update_query)
            conn.commit()

        # Send result to EXP channel
        exp_channel = bot.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            await exp_channel.send(
                f"🏅 <@{user_id}> has been awarded ⚡ **{xp_awarded} XP** and 💰 **{gold_awarded} gold**\n"
                f"Total: ⚡ **{user_data['exp'] + xp_awarded} XP**, 💰 **{user_data['gold'] + gold_awarded} gold**\n"
                f"🏔️ Daily Multiplier: **{daily_multiplier}x**\n"
                f"🧬 Generational Multiplier: **{retirement_multiplier + 1:.2f}x**"
            )
        else:
            print("🚂 - [ERROR] EXP channel not found.")

async def announce_level_up(guild: discord.Guild, member: discord.Member, level: int, channel_id: int):
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(f"## 🎆 {member.mention} has reached **Level {level}**!")
    else:
        print(f"🚂 - [ERROR] Could not find channel ID {channel_id} to announce level up.")


async def setup(bot):
    await bot.add_cog(ExpEngine(bot))