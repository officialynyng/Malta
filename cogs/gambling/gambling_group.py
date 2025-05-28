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
                emoji = game.get("emoji", "🎰")
                emoji = emoji if isinstance(emoji, str) and len(emoji) <= 2 else None
                options.append(discord.SelectOption(
                    label=game["name"],
                    value=key,
                    description=game["description"][:100],
                    emoji=emoji
                ))

        self.select = discord.ui.Select(
            placeholder="🎲 Choose a gambling game...",
            options=options,
            custom_id="gamble_game_select"
        )

        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your selection!", ephemeral=True)

        selection = self.select.values[0]
        if selection.startswith("slot_machine:"):
            variant_key = selection.split(":")[1]
            game = GAMES["slot_machine"]["variants"][variant_key]
            game_key = f"slot_machine:{variant_key}"
        else:
            game_key = selection
            game = GAMES[game_key]

        min_bet = game.get("min_bet", 1)
        suggestion = max(min_bet, min(100, self.user_gold // 10))

        if DEBUG:
            print(f"[DEBUG🎰] {interaction.user.display_name} selected {game_key}. Suggested bet: {suggestion}")

        embed = Embed(
            title=f"{game['emoji']} {game['name']}",
            description=(
                f"{game['description']}\n\n"
                f"💰 Min Bet: **{min_bet}** gold\n"
                f"🎯 Odds: **{int(game['odds'] * 100)}%**\n"
                f"🏆 Payout: **x{game['payout']}**\n\n"
                f"Use `/bet {game_key} <amount>` to continue — suggested: **{suggestion}** gold."
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text=f"You have {self.user_gold} gold.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
            description="Pick your game from the dropdown menu to begin betting!",
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
