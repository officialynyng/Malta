import discord
from discord.ext import commands
from cogs.store.store_utils import STORE_CATEGORIES, get_all_items, get_item_by_id, get_item_by_category
from cogs.store.store_search import filter_weapon_items

class CategorySelect(discord.ui.Select):
    def __init__(self, ctx, callback_func):
        self.ctx = ctx
        options = [discord.SelectOption(label=cat, value=cat) for cat in STORE_CATEGORIES]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values[0])

class CategoryView(discord.ui.View):
    def __init__(self, ctx, callback_func):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(ctx, callback_func))

class StoreGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_category_tree(self):
        tree = {}
        for path in STORE_CATEGORIES:
            parts = path.split("/")
            if len(parts) == 2:
                parent, child = parts
                if parent not in tree:
                    tree[parent] = []
                tree[parent].append(child)
            else:
                tree[parts[0]] = []
        return tree

    @commands.group(name='shop', invoke_without_command=True)
    async def shop(self, ctx):
        """Displays available shop categories with dropdown."""
        print(f"[🍯 DEBUG] /shop used by {ctx.author} (ID: {ctx.author.id})")
        embed = discord.Embed(title="🍯 Malta's CRPG Item Shop", color=discord.Color.gold())
        embed.description = "Select a category below to view items."
        await ctx.send(embed=embed, view=CategoryView(ctx, self.show_items_by_category), ephemeral=True)

    async def show_items_by_category(self, interaction, category_name):
        print(f"[🍯 DEBUG] Dropdown category '{category_name}' selected by {interaction.user} (ID: {interaction.user.id})")
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

    @shop.command(name='filter')
    async def shop_filter(self, ctx, damage_type: str = None, weapon_type: str = None):
        """Filter weapons by damage type and weapon type (1h, 2h, polearm)."""
        print(f"[🍯 DEBUG] /shop filter used by {ctx.author} (ID: {ctx.author.id})")
        print(f"[🍯 DEBUG] Filtering by damage_type={damage_type}, weapon_type={weapon_type}")
        all_items = get_all_items()
        filtered = filter_weapon_items(
            all_items,
            damage_types=damage_type,
            weapon_types=weapon_type
        )
        print(f"[🍯 DEBUG] Found {len(filtered)} matching items")
        if not filtered:
            await ctx.send("No items match the filter.", ephemeral=True)
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
        await ctx.send(embed=embed, ephemeral=True)

    @shop.command(name='info')
    async def shop_info(self, ctx, item_id: str):
        """Display detailed information about an item by its ID."""
        print(f"[🍯 DEBUG] /shop info '{item_id}' used by {ctx.author} (ID: {ctx.author.id})")
        item = get_item_by_id(item_id)

        if not item:
            print(f"[🍯 DEBUG] Item '{item_id}' not found")
            await ctx.send(f"Item with ID `{item_id}` not found.", ephemeral=True)
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

        # Add stats dynamically
        for stat in ["handling", "swing_speed", "thrust_speed", "length", "reach", "armor_value", "hit_points"]:
            if stat in item:
                embed.add_field(name=stat.replace("_", " ").title(), value=str(item[stat]), inline=True)

        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(StoreGroup(bot))