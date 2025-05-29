# ui_common.py
from discord.ui import Button
from discord import Interaction

class BackToGameButton(Button):
    def __init__(self, user_id, parent):
        super().__init__(label="⬅️ Back", style=discord.ButtonStyle.secondary)
        self.user_id = user_id
        self.parent = parent

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=None, view=self.parent)


class PlayAgainButton(Button):
    def __init__(self, user_id, parent_view):
        super().__init__(label="🔁 Play Again", style=discord.ButtonStyle.success)
        self.user_id = user_id
        self.parent = parent_view

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your session!", ephemeral=True)
        await interaction.response.edit_message(content=None, embed=None, view=self.parent)
