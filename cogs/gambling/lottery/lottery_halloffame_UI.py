import discord
from discord.ext import commands
from discord.ui import View, Button

class HallOfFameView(View):
    def __init__(self, cog, interaction=None):
        super().__init__(timeout=None)  # persistent: no timeout
        self.cog = cog
        self.interaction = interaction  # optional, keep if needed

    @discord.ui.button(label="All Time", style=discord.ButtonStyle.secondary, custom_id="hof_all_time")
    async def all_time(self, interaction: discord.Interaction, button: Button):
        await self.cog.send_halloffame_embed(interaction, "all")

    @discord.ui.button(label="Monthly", style=discord.ButtonStyle.secondary, custom_id="hof_monthly")
    async def monthly(self, interaction: discord.Interaction, button: Button):
        await self.cog.send_halloffame_embed(interaction, "monthly")

    @discord.ui.button(label="Weekly", style=discord.ButtonStyle.secondary, custom_id="hof_weekly")
    async def weekly(self, interaction: discord.Interaction, button: Button):
        await self.cog.send_halloffame_embed(interaction, "weekly")
