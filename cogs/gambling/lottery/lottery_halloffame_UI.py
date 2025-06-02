import discord
from discord.ext import commands
from discord.ui import View, Button

class HallOfFameView(View):
    def __init__(self, cog, interaction):
        super().__init__(timeout=60)
        self.cog = cog
        self.interaction = interaction

    @discord.ui.button(label="All Time", style=discord.ButtonStyle.primary)
    async def all_time(self, interaction: discord.Interaction, button: Button):
        await self.cog.send_halloffame_embed(interaction, "all")

    @discord.ui.button(label="Monthly", style=discord.ButtonStyle.secondary)
    async def monthly(self, interaction: discord.Interaction, button: Button):
        await self.cog.send_halloffame_embed(interaction, "monthly")

    @discord.ui.button(label="Weekly", style=discord.ButtonStyle.secondary)
    async def weekly(self, interaction: discord.Interaction, button: Button):
        await self.cog.send_halloffame_embed(interaction, "weekly")
