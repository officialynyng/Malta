import discord
from discord.ui import Button
from discord import Interaction
from discord.ui import Button

class BackToGameButton(Button):
    def __init__(self, user_id, parent):
        super().__init__(label="⬅️ Back", style=discord.ButtonStyle.secondary)
        self.user_id = user_id
        self.parent = parent

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=None, view=self.parent)
