import discord
from discord.ext import commands
from discord import app_commands
from cogs.store.store_utils import STORE_CATEGORIES, get_all_items, get_item_by_id, get_item_by_category
from cogs.store.store_search import filter_weapon_items


class CategorySelect(discord.ui.Select):
    def __init__(self, interaction, callback_func):
        self.interaction = interaction
        options = [discord.SelectOption(label=cat, value=cat) for cat in STORE_CATEGORIES]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values[0])


class CategoryView(discord.ui.View):
    def __init__(self, interaction, callback_func):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(interaction, callback_func))


class StoreGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Create the /shop command group
        self.shop_group = app_commands.Group(name="shop", description="Access Malta's CRPG shop")

        @self.shop_group.command(name="open", description="🍯 - 🛒 Open the shop UI")
        async def shop_main(interaction: discord.Interaction):
            print(f"[🍯🛒 DEBUG] /shop open used by {interaction.user} (ID: {interaction.user.id})")

            embed = discord.Embed(title="🍯 Malta's CRPG Item Shop", color=discord.Color.gold())
            embed.description = "Select a category below to view items."

            # Embed an image (must be a public direct image URL)
            embed.set_image(url="http://ynyng.org/wp-content/uploads/2025/03/ynyng_malta__hospitaller_very_organized_and_open_medieval_shop__26cf32ee-fe4e-405e-ba6c-b306edae40e6-1.png")

            await interaction.response.send_message(embed=embed, view=CategoryView(interaction, self.show_items_by_category), ephemeral=True)

        @self.shop_group.command(name="filter", description="🍯 - 🔍 Filter weapons by damage type and weapon type (1h, 2h, polearm)")
        @app_commands.describe(damage_type="e.g. blunt, pierce", weapon_type="e.g. 1h, 2h")
        async def shop_filter(interaction: discord.Interaction, damage_type: str = None, weapon_type: str = None):
            print(f"[🍯ℹ️ DEBUG] /shop filter used by {interaction.user} (ID: {interaction.user.id})")
            all_items = get_all_items()
            filtered = filter_weapon_items(all_items, damage_types=damage_type, weapon_types=weapon_type)

            if not filtered:
                await interaction.response.send_message("No items match the filter.", ephemeral=True)
                return

            embed = discord.Embed(title="Filtered Weapons", color=discord.Color.purple())
            for item in filtered[:15]:
                embed.add_field(
                    name=f"{item['name']} - {item.get('price', 0)} gold",
                    value=f"Damage: {', '.join(item.get('damage_types', []))} | Handling: {item.get('handling', '?')}",
                    inline=False
                )
            if len(filtered) > 15:
                embed.set_footer(text=f"Showing first 15 of {len(filtered)} results.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @self.shop_group.command(name="info", description="🍯 - 📘 Get detailed information about an item by its ID")
        @app_commands.describe(item_id="The item ID to look up")
        async def shop_info(interaction: discord.Interaction, item_id: str):
            print(f"[🍯ℹ️ DEBUG] /shop info '{item_id}' used by {interaction.user} (ID: {interaction.user.id})")
            item = get_item_by_id(item_id)
            if not item:
                await interaction.response.send_message(f"Item with ID `{item_id}` not found.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"{item.get('name', 'Unknown Item')} - {item.get('price', 0)} gold",
                color=discord.Color.teal(),
                description=item.get('description', 'No description.')
            )
            embed.add_field(name="Type", value=item.get("type", "N/A"), inline=True)
            embed.add_field(name="Category", value=item.get("category", "N/A"), inline=True)
            embed.add_field(name="Tier", value=str(item.get("tier", "N/A")), inline=True)

            if item.get("damage_types"):
                embed.add_field(name="Damage Types", value=", ".join(item["damage_types"]), inline=False)

            for stat in ["handling", "swing_speed", "thrust_speed", "length", "reach", "armor_value", "hit_points"]:
                if stat in item:
                    embed.add_field(name=stat.replace("_", " ").title(), value=str(item[stat]), inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def show_items_by_category(self, interaction, category_name):
        items = get_item_by_category(category_name)
        if not items:
            await interaction.response.send_message(f"No items found in category `{category_name}`.", ephemeral=True)
            return

        pages = [items[i:i+5] for i in range(0, len(items), 5)]
        current_page = 0

        async def get_embed(page):
            embed = discord.Embed(title=f"🔹 {category_name.title()} Items (Page {page+1}/{len(pages)})", color=discord.Color.blue())
            for item in pages[page]:
                embed.add_field(
                    name=f"{item['name']} - {item.get('price', 0)} gold",
                    value=item.get('short_description', 'No description.'),
                    inline=False
                )
            return embed

        class Paginator(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
                self.page = current_page

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
            async def prev(self, button, interaction):
                if self.page > 0:
                    self.page -= 1
                    await interaction.response.edit_message(embed=await get_embed(self.page), view=self)

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
            async def next(self, button, interaction):
                if self.page < len(pages) - 1:
                    self.page += 1
                    await interaction.response.edit_message(embed=await get_embed(self.page), view=self)

        await interaction.response.send_message(embed=await get_embed(current_page), view=Paginator(), ephemeral=True)

    def cog_load(self):
        pass


async def setup(bot):
    cog = StoreGroup(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.shop_group)  # <-- this ensures /shop commands get registered

