
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import random
from discord import Interaction, Embed
from sqlalchemy import select, insert, update
from cogs.exp_config import engine, EXP_CHANNEL_ID
from cogs.exp_utils import get_user_data, update_user_gold
from cogs.database.gambling_stats_table import gambling_stats
from cogs.gambling.games_loader import GAMES


async def handle_gamble_result(interaction: Interaction, user_id: int, game_key: str, amount: int):
    user_data = get_user_data(user_id)
    now = int(time.time())

    if user_data.get("last_gamble_ts") and now - user_data["last_gamble_ts"] < 5:
        await interaction.response.send_message("⏳ You must wait a few seconds before gambling again.", ephemeral=True)
        return

    # Game data
    if game_key.startswith("slot_machine:"):
        variant = game_key.split(":")[1]
        game = GAMES["slot_machine"]["variants"].get(variant)
        if not game or "odds" not in game or "payout" not in game:
            await interaction.followup.send("❌ Invalid slot machine configuration. Odds or payout missing.", ephemeral=True)
            return
    elif game_key.startswith("roulette:"):
        variant = game_key.split(":")[1]
        game = GAMES["roulette"]["variants"].get(variant)
    else:
        if game_key == "blackjack":
            from cogs.gambling.blackjack.blackjack import start_blackjack_game
            await start_blackjack_game(interaction, user_data, amount)
            return
        game = GAMES[game_key]

    if not game:
        await interaction.response.send_message("❌ Invalid game.", ephemeral=True)
        return

    if user_data["gold"] < amount:
        await interaction.response.send_message(f"❌ You need at least {amount} gold to play.", ephemeral=True)
        return

    # Handle games with custom logic elsewhere
    if game_key == "blackjack":
        from cogs.gambling.blackjack.blackjack import start_blackjack_game
        await start_blackjack_game(interaction, user_data, amount)
        return

    if game_key.startswith("roulette"):
        # All roulette logic is handled through UI and extra_callback – skip logic here
        return



    # Calculate win/loss
    win = random.random() < game["odds"]
    payout = int(amount * game["payout"]) if win else 0
    net_change = payout - amount
    user_data["gold"] += net_change
    user_data["last_gamble_ts"] = now
    update_user_gold(
        user_id,
        user_data["gold"],
        type_="gamble_win" if win else "gamble_loss",
        description=f"{'Won' if win else 'Lost'} {game['name']} for {abs(net_change)} gold"
    )


    # Record stats
    with engine.begin() as conn:
        existing = conn.execute(select(gambling_stats).where(gambling_stats.c.user_id == user_id)).fetchone()
        values = {
            "total_bets": (existing.total_bets + 1) if existing else 1,
            "total_won": (existing.total_won + payout) if win and existing else (payout if win else 0),
            "total_lost": (existing.total_lost + amount) if not win and existing else (0 if win else amount),
            "net_winnings": (existing.net_winnings + net_change) if existing else net_change,
            "last_gamble_ts": now
        }
        if existing:
            conn.execute(update(gambling_stats).where(gambling_stats.c.user_id == user_id).values(**values))
        else:
            conn.execute(insert(gambling_stats).values(user_id=user_id, **values))

    # Final message suppressed (no ephemeral)
    try:
        if not interaction.response.is_done():
            await interaction.response.defer()
    except Exception:
        pass

    # Public broadcast of all results
    exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
    # 1. Defer the interaction first
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

    # 2. Send initial ephemeral placeholder (ONCE)
    ephemeral_msg = await interaction.followup.send("⏳ Calculating result...", ephemeral=True)

    # 3. Do your game result logic...

    # 4. Get CST timestamp
    ts = datetime.now(ZoneInfo("America/Chicago")).strftime("%I:%M:%S %p CST")

    # 5. Edit that original ephemeral message
    if win:
        await ephemeral_msg.edit(
            content=f"🎉 You won **{payout}** gold on {game['name']} {game['emoji']}!\n*Updated at {ts}*"
        )
    else:
        await ephemeral_msg.edit(
            content=f"💀 You lost your bet of **{amount}** gold on {game['name']} {game['emoji']}.\n*Updated at {ts}*"
        )

    if exp_channel:
        if win:
            await exp_channel.send(
                f"♠️ ♥️ ♦️ ♣️ **{interaction.user.display_name}** wagered **{amount}** gold on {game['name']} {game['emoji']} and won 🎉 **+{net_change}** gold!"
            )
        else:
            await exp_channel.send(
                f"♠️ ♥️ ♦️ ♣️ **{interaction.user.display_name}** wagered **{amount}** gold on {game['name']} {game['emoji']} and lost 💀."
            )
