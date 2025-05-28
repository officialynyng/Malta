import random
import time
import json
import discord
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ext import commands
from discord.ui import View, Button
from sqlalchemy import select, insert, update
from cogs.exp_config import engine, EXP_CHANNEL_ID
from cogs.database.gambling_stats_table import gambling_stats
from cogs.exp_utils import get_user_data, update_user_gold
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "games_config.json")
with open(CONFIG_PATH) as f:
    GAMES = json.load(f)

DEBUG = True

class GamblingButtonView(View):
    def __init__(self, user_id, game_key, amount):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.game_key = game_key
        self.amount = amount

    @discord.ui.button(label="Play", style=ButtonStyle.red, emoji="🎰")
    async def play(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your game!", ephemeral=True)

        if self.game_key.startswith("slot_machine:"):
            variant = self.game_key.split(":")[1]
            game = GAMES["slot_machine"]["variants"].get(variant)
            if not game:
                return await interaction.response.send_message("❌ Invalid slot machine variant.", ephemeral=True)
        elif self.game_key.startswith("roulette:"):
            variant = self.game_key.split(":")[1]
            game = GAMES["roulette"]["variants"].get(variant)
            if not game:
                return await interaction.response.send_message("❌ Invalid roulette variant.", ephemeral=True)
        else:
            game = GAMES[self.game_key]
        user_data = get_user_data(self.user_id)

        now = int(time.time())
        if user_data.get("last_gamble_ts") and now - user_data["last_gamble_ts"] < 5:
            return await interaction.response.send_message("⏳ You must wait a few seconds before gambling again.", ephemeral=True)

        if DEBUG:
            print(f"[DEBUG🎰] User {self.user_id} has {user_data['gold']} gold before betting {self.amount}")


        if not user_data:
            return await interaction.response.send_message("❌ No user data found.", ephemeral=True)

        max_loss = self.amount * (1 - game["odds"])
        if user_data["gold"] < self.amount:
            return await interaction.response.send_message(
                f"❌ You need at least {self.amount} gold to place this bet.", ephemeral=True
            )

        win = random.random() < game["odds"]
        payout = int(self.amount * game["payout"]) if win else 0
        net_change = payout - self.amount
        user_data["gold"] += net_change
        user_data["last_gamble_ts"] = now
        update_user_gold(self.user_id, user_data["gold"])
        if DEBUG:
            print(f"[DEBUG🎰] Payout: {payout}, Net Change: {net_change}, Final Gold: {user_data['gold']}")

        
        with engine.begin() as conn:
            existing = conn.execute(select(gambling_stats).where(gambling_stats.c.user_id == self.user_id)).fetchone()
            if existing:
                values = {
                    "total_bets": existing.total_bets + 1,
                    "total_won": existing.total_won + (payout if win else 0),
                    "total_lost": existing.total_lost + (0 if win else self.amount),
                    "net_winnings": existing.net_winnings + net_change,
                    "last_gamble_ts": int(time.time())
                }
                conn.execute(update(gambling_stats).where(gambling_stats.c.user_id == self.user_id).values(**values))
            else:
                conn.execute(insert(gambling_stats).values(
                    user_id=self.user_id,
                    total_bets=1,
                    total_won=payout if win else 0,
                    total_lost=0 if win else self.amount,
                    net_winnings=net_change,
                    last_gamble_ts=int(time.time())
                ))

        outcome = f"✅ You won {payout} gold!" if win else f"💀 You lost {self.amount} gold."
        embed = Embed(title=game["name"], description=outcome, color=discord.Color.red())
        embed.set_footer(text="Gambling Results", icon_url=interaction.user.display_avatar.url)

        exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
        if exp_channel:
            await exp_channel.send(f"{game['emoji']} **{interaction.user.display_name}** played {game['name']} and {'won' if win else 'lost'} {abs(net_change)} gold!")

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=ButtonStyle.grey, emoji="❌")
    async def cancel(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your game!", ephemeral=True)
        await interaction.response.edit_message(content="❌ Game cancelled.", view=None)

class GameSelectionView(View):
    def __init__(self, user_id, user_gold):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_gold = user_gold

        options = []

        for key, game in GAMES.items():
            if key == "slot_machine" and "variants" in game:
                for variant_key, variant in game["variants"].items():
                    options.append(discord.SelectOption(
                        label=variant['name'],
                        value=f"slot_machine:{variant_key}",
                        description=variant["description"][:100],
                        emoji=variant.get("emoji", "🎰")
                    ))
            else:
                options.append(discord.SelectOption(
                    label=game["name"],
                    value=key,
                    description=game["description"][:100],
                    emoji=game.get("emoji", "🎰")
                ))

        self.select = discord.ui.Select(
            placeholder="🎲 Choose a gambling game...",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        game_key = self.select.values[0]

        if game_key == "roulette":
            await interaction.response.send_message(
                "🎡 Choose your roulette bet type:",
                view=RouletteVariantSelectionView(self.user_id, self.user_gold),
                ephemeral=True
            )
            return

        if game_key.startswith("slot_machine:"):
            variant_key = game_key.split(":")[1]
            game = GAMES["slot_machine"]["variants"][variant_key]
        else:
            game = GAMES[game_key]

        min_bet = game.get("min_bet", 1)
        max_bet = 100000
        await interaction.response.send_message(
            f"💰 You've selected **{game['name']}**. Now choose your bet amount:",
            view=BetAmountSelectionView(self.user_id, game_key, min_bet, max_bet),
            ephemeral=True
        )

class RouletteVariantSelectionView(View):
    def __init__(self, user_id, user_gold):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_gold = user_gold

        options = [
            discord.SelectOption(label=variant, value=variant,
                description=f"{data['odds']*100:.1f}% chance, x{data['payout']} payout",
                emoji=data.get("emoji", "🎯"))
            for variant, data in GAMES["roulette"]["variants"].items()
        ]

        self.select = discord.ui.Select(
            placeholder="Choose Red, Black, or a Number (0–36)...",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        variant_key = self.select.values[0]
        full_game_key = f"roulette:{variant_key}"
        variant = GAMES["roulette"]["variants"][variant_key]

        await interaction.response.send_message(
            f"🎯 Bet type: **{variant_key}**\n💰 Choose your wager:",
            view=BetAmountSelectionView(self.user_id, full_game_key, min_bet=100, max_bet=10000),
            ephemeral=True
        )

class BetAmountSelectionView(View):
    def __init__(self, user_id, game_key, min_bet, max_bet):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.game_key = game_key
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.amount = min_bet

        self.dropdown = BetAmountDropdown(self)
        self.play_button = GamblingPlayButton(user_id, game_key, lambda: self.amount)

        self.add_item(self.dropdown)
        self.add_item(self.play_button)
        self.add_item(RefreshGoldButton(user_id))


class RefreshGoldButton(discord.ui.Button):
    def __init__(self, user_id):
        super().__init__(label="Refresh Gold View", emoji="🔄", style=discord.ButtonStyle.grey)
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        user_data = get_user_data(self.user_id)
        await interaction.response.send_message(
            f"💰 You now have **{user_data['gold']}** gold.", ephemeral=True
        )

class GamblingPlayButton(discord.ui.Button):
    def __init__(self, user_id, game_key, get_amount_callback):
        super().__init__(label="Play", emoji="🎰", style=discord.ButtonStyle.red)
        self.user_id = user_id
        self.game_key = game_key
        self.get_amount = get_amount_callback  # A function that returns the current amount

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)

        amount = self.get_amount()
        user_data = get_user_data(self.user_id)

        now = int(time.time())
        if user_data.get("last_gamble_ts") and now - user_data["last_gamble_ts"] < 5:
            return await interaction.response.send_message("⏳ You must wait a few seconds before gambling again.", ephemeral=True)

        if self.game_key.startswith("slot_machine:"):
            variant = self.game_key.split(":")[1]
            game = GAMES["slot_machine"]["variants"].get(variant)
            if not game:
                return await interaction.response.send_message("❌ Invalid slot machine variant.", ephemeral=True)
        else:
            game = GAMES[self.game_key]

        if user_data["gold"] < amount:
            return await interaction.response.send_message(f"❌ You need at least {amount} gold to play.", ephemeral=True)

        win = random.random() < game["odds"]
        payout = int(amount * game["payout"]) if win else 0
        net_change = payout - amount
        user_data["gold"] += net_change
        user_data["last_gamble_ts"] = now
        update_user_gold(self.user_id, user_data["gold"])

        # Record stats
        with engine.begin() as conn:
            existing = conn.execute(select(gambling_stats).where(gambling_stats.c.user_id == self.user_id)).fetchone()
            values = {
                "total_bets": (existing.total_bets + 1) if existing else 1,
                "total_won": (existing.total_won + payout) if win and existing else (payout if win else 0),
                "total_lost": (existing.total_lost + amount) if not win and existing else (0 if win else amount),
                "net_winnings": (existing.net_winnings + net_change) if existing else net_change,
                "last_gamble_ts": now
            }
            if existing:
                conn.execute(update(gambling_stats).where(gambling_stats.c.user_id == self.user_id).values(**values))
            else:
                conn.execute(insert(gambling_stats).values(user_id=self.user_id, **values))

        outcome = f"✅ You won {payout} gold!" if win else f"💀 You lost {amount} gold."
        await interaction.response.send_message(outcome, ephemeral=True)

        exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
        if amount >= 1000 and exp_channel:
            await exp_channel.send(
                f"{game['emoji']} **{interaction.user.display_name}** wagered **{amount}** gold on {game['name']} and "
                f"{'won 🎉' if win else 'lost 💀'} **{abs(net_change)}** gold!"
            )


class BetAmountDropdown(discord.ui.Select):
    def __init__(self, parent_view):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label=str(x), value=str(x)) for x in [50, 100, 200, 250, 300, 500, 750, 1000, 2000, 2500, 3500, 5000]
            if parent_view.min_bet <= x <= parent_view.max_bet
        ]
        super().__init__(placeholder="💰 Choose your bet amount", options=options)

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.parent_view.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        self.parent_view.amount = int(self.values[0])
        self.parent_view.play_button.amount = self.parent_view.amount # ← THIS is key
        await interaction.response.send_message(
            f"✅ Bet amount set to **{self.values[0]} gold**. Press play when ready!",
            ephemeral=True
        )

class GamblingGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gamble", description="♠️ ♥️ ♦️ ♣️ Open the gambling hall and choose your game!")
    async def gamble(self, interaction: Interaction):
        user_data = get_user_data(interaction.user.id)
        if not user_data:
            await interaction.response.send_message("❌ Could not fetch user data.", ephemeral=True)
            return

        view = GameSelectionView(interaction.user.id, user_data["gold"])
        embed = Embed(
            title="🎰 Welcome to the Gambling Hall",
            description="Pick your game to begin.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"🎲 Gold: {user_data['gold']}")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    @app_commands.command(name="gamble_stats", description="🎰 - 📊 View your gambling history and performance")
    async def gamble_stats(self, interaction: Interaction):
        user_id = interaction.user.id
        with engine.begin() as conn:
            result = conn.execute(select(gambling_stats).where(gambling_stats.c.user_id == user_id)).fetchone()

        if not result:
            await interaction.response.send_message("❌ No gambling data found.", ephemeral=True)
            return

        embed = Embed(
            title=f"🎰 Gambling Stats for {interaction.user.display_name}",
            color=discord.Color.red()
        )
        embed.add_field(name="Total Bets", value=result.total_bets, inline=True)
        embed.add_field(name="Total Won", value=result.total_won, inline=True)
        embed.add_field(name="Total Lost", value=result.total_lost, inline=True)
        embed.add_field(name="Net Winnings", value=result.net_winnings, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(GamblingGroup(bot))
