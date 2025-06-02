import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ui import View, Button

from cogs.exp_utils import get_user_data

DEBUG = True

def is_admin():
    async def predicate(interaction: Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

class HubView(View):
    def __init__(self, user_id, user_data):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_data = user_data
        self.add_item(ViewInventoryButton(self))
        self.add_item(ViewTransactionsButton(self))
        self.add_item(ViewStoreButton(self))
        self.add_item(ViewLotteryButton(self))
        self.add_item(ViewGambleButton(self))
        self.add_item(ViewTitlesButton(self))
        self.add_item(ViewStatsButton(self))

    def get_embed(self):
        embed = Embed(title="🧑 Your CRPG Profile", color=discord.Color.from_rgb(0, 0, 0))
        embed.add_field(name="💼 Gold", value=f"{self.user_data['gold']:,}", inline=True)
        embed.add_field(name="🧬 Multiplier", value=f"{self.user_data['multiplier']:.2f}x", inline=True)
        embed.add_field(name="🪙 Heirloom Points", value=str(self.user_data['heirloom_points']), inline=True)
        embed.add_field(name="🪦 Retirements", value=str(self.user_data['retirements']), inline=True)
        embed.add_field(name="🧪 Daily Multiplier", value=f"{self.user_data['daily_multiplier']}x", inline=True)
        return embed

# Buttons with page switch logic
class ViewInventoryButton(Button):
    def __init__(self, view): super().__init__(label="Inventory", style=ButtonStyle.secondary); self.view_ref = view
    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id: return await interaction.response.send_message("❌ Not your profile.", ephemeral=True)
        await interaction.response.edit_message(embed=Embed(title="📦 Inventory"), view=BackToHubView(self.view_ref))

class ViewTransactionsButton(Button):
    def __init__(self, view): super().__init__(label="Transactions", style=ButtonStyle.secondary); self.view_ref = view
    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id: return await interaction.response.send_message("❌ Not your profile.", ephemeral=True)
        await interaction.response.edit_message(embed=Embed(title="💼 Transactions"), view=BackToHubView(self.view_ref))

class ViewStoreButton(Button):
    def __init__(self, view): super().__init__(label="Store", style=ButtonStyle.secondary); self.view_ref = view
    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id: return await interaction.response.send_message("❌ Not your profile.", ephemeral=True)
        await interaction.response.edit_message(embed=Embed(title="🛒 Store"), view=BackToHubView(self.view_ref))

class ViewLotteryButton(Button):
    def __init__(self, view): super().__init__(label="Lottery", style=ButtonStyle.secondary); self.view_ref = view
    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id: return await interaction.response.send_message("❌ Not your profile.", ephemeral=True)
        await interaction.response.edit_message(embed=Embed(title="🎟️ Lottery"), view=BackToHubView(self.view_ref))

class ViewGambleButton(Button):
    def __init__(self, view): super().__init__(label="Gamble", style=ButtonStyle.secondary); self.view_ref = view
    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id: return await interaction.response.send_message("❌ Not your profile.", ephemeral=True)
        await interaction.response.edit_message(embed=Embed(title="♠️ Gambling Hall"), view=BackToHubView(self.view_ref))

class ViewTitlesButton(Button):
    def __init__(self, view): super().__init__(label="Titles", style=ButtonStyle.secondary); self.view_ref = view
    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id: return await interaction.response.send_message("❌ Not your profile.", ephemeral=True)
        await interaction.response.edit_message(embed=Embed(title="📜 Titles"), view=BackToHubView(self.view_ref))

class ViewStatsButton(Button):
    def __init__(self, view): super().__init__(label="Stats", style=ButtonStyle.secondary); self.view_ref = view
    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.view_ref.user_id: return await interaction.response.send_message("❌ Not your profile.", ephemeral=True)
        await interaction.response.edit_message(embed=Embed(title="📊 Stats"), view=BackToHubView(self.view_ref))

# View with "Back" button
class BackToHubView(View):
    def __init__(self, hub_view):
        super().__init__(timeout=60)
        self.hub_view = hub_view
        self.add_item(BackToHubButton(self))

class BackToHubButton(Button):
    def __init__(self, view): super().__init__(label="Back", style=ButtonStyle.danger); self.view_ref = view
    async def callback(self, interaction: Interaction):
        await interaction.response.edit_message(embed=self.view_ref.hub_view.get_embed(), view=self.view_ref.hub_view)

class HubGroup(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name="hub", description="🧑 View your CRPG profile and access all features")
    @is_admin()
    async def hub(self, interaction: Interaction):
        user_id = interaction.user.id
        user_data = get_user_data(user_id)

        if not user_data:
            await interaction.response.send_message("❌ Couldn't fetch your profile.", ephemeral=True)
            return

        view = HubView(user_id, user_data)
        embed = view.get_embed()
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HubGroup(bot))
