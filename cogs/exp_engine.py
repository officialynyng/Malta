import discord
from discord.ext import commands
import time
from cogs.exp_config import (
    db, players, exp_channel, engine, EXP_COOLDOWN, EXP_PER_TICK, GOLD_PER_TICK, LEVEL_CAP, EXP_CHANNEL_ID, TIME_DELTA, MAX_MULTIPLIER,
)
from cogs.exp_utils import (
    get_multiplier, get_user_data, calculate_level, update_user_data, 
)

class ExpEngine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def handle_exp_gain(message: discord.Message, level_up_channel_id: int):
    print(f"Handling EXP gain for user: {message.author.id}")
    if message.author.bot:
        return

    user_id = str(message.author.id)
    current_ts = time.time()

    with engine.connect() as conn:
        result = conn.execute(db.select(players).where(players.c.user_id == user_id)).fetchone()

        if result:
            cooldown_remaining = current_ts - result.last_message_ts
            if cooldown_remaining < EXP_COOLDOWN:
                print(f"[DEBUG] EXP cooldown active for user {user_id}: {EXP_COOLDOWN - cooldown_remaining:.2f} seconds remaining.")
                return

            multiplier = get_multiplier(result.retirements)
            gained_exp = int(EXP_PER_TICK * multiplier)
            gained_gold = int(GOLD_PER_TICK * multiplier)
            total_exp = result.exp + gained_exp
            new_level = calculate_level(total_exp)

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
            if exp_channel:
                await exp_channel.send(
                    f"**{message.author.display_name}** gained ⚡ **{gained_exp} EXP** and 💰 **{gained_gold} gold** "
                    f"with a current daily multiplier of 🏔️ **{multiplier:.2f}x**."
                )

            if new_level > result.level:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)
        else:
            multiplier = get_multiplier(0)
            new_level = calculate_level(EXP_PER_TICK)
            gained_exp = int(EXP_PER_TICK * multiplier)
            gained_gold = int(GOLD_PER_TICK * multiplier)

            conn.execute(players.insert().values(
                user_id=user_id,
                exp=gained_exp,
                gold=gained_gold,
                level=new_level,
                last_message_ts=current_ts,
                retirements=0,
                heirloom_points=0
            ))
            conn.commit()

            exp_channel = message.guild.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"**{message.author.display_name}** gained ⚡ **{gained_exp} EXP** and 💰 **{gained_gold} gold** "
                    f"with a current daily multiplier of 🏔️ **{multiplier:.2f}x**."
                )

            if new_level > 0:
                await announce_level_up(message.guild, message.author, new_level, level_up_channel_id)


async def on_user_comment(user_id, bot):
    print("[DEBUG] on_user_comment triggered")
    current_time = int(time.time())
    user_data = get_user_data(user_id)

    if user_data:
        last_activity = user_data['last_activity']
        last_multiplier_update = user_data.get('last_multiplier_update', 0)
        current_daily_multiplier = user_data['daily_multiplier']

        print(f"[DEBUG] Last activity: {last_activity}, Last multiplier update: {last_multiplier_update}")
        print(f"[DEBUG] Daily Multiplier before update: {current_daily_multiplier}")

        # Always update last activity timestamp
        update_user_data(user_id, user_data['retirement_multiplier'], current_daily_multiplier, current_time, last_multiplier_update)

        # Don't update multiplier more than once per 24h
        if current_time - last_multiplier_update < TIME_DELTA:
            print(f"[DEBUG] Skipping multiplier update — already updated in the last 24h.")
            return

        # If inactive for 48+ hours, reset
        if current_time - last_activity >= TIME_DELTA * 2:
            new_daily_multiplier = 1
        else:
            new_daily_multiplier = min(current_daily_multiplier + 1, MAX_MULTIPLIER)

        # Save new multiplier + timestamp only if it changed
    if new_daily_multiplier != current_daily_multiplier:
        update_user_data(user_id, user_data['retirement_multiplier'], new_daily_multiplier, current_time, current_time)

        exp_channel = bot.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            await exp_channel.send(
                f"🏔️ <{user_id}>'s daily multiplier updated to **{new_daily_multiplier}x** due to daily posting."
            )
        else:
            print("[ERROR] EXP channel not found.")
    else:
        print(f"[DEBUG] Multiplier unchanged for {user_id}, no update message sent.")


async def check_and_reset_multiplier(user_id, bot):
    current_time = int(time.time())
    user_data = get_user_data(user_id)

    if user_data:
        time_since_last = current_time - user_data['last_activity']

        if time_since_last >= TIME_DELTA * 2:
            # Reset daily multiplier & last_multiplier_update
            update_user_data(user_id, user_data['retirement_multiplier'], 1, current_time, current_time)
            exp_channel = bot.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(
                    f"🌋 <{user_id}>'s daily multiplier has been reset to **1x** due to inactivity."
                )
            print(f"[DEBUG] Reset daily multiplier for {user_id} due to inactivity ({time_since_last} seconds).")
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