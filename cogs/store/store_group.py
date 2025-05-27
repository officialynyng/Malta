import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ui import View, button
from cogs.store.store_utils import STORE_CATEGORIES, get_all_items, get_item_by_id, get_item_by_category, roll_random_title_for_user
from cogs.store.store_search import filter_weapon_items
from cogs.store.store_utils import get_item_by_id, get_item_by_category
from cogs.exp_config import EXP_CHANNEL_ID
from cogs.store.store_search import get_item_from_any_store
from sqlalchemy.sql import select
import traceback
DEBUG = True
ROLL_PRICE = 10000

class CategorySelect(discord.ui.Select):
    def __init__(self, interaction, callback_func):
        self.interaction = interaction
        options = [discord.SelectOption(label=cat, value=cat) for cat in STORE_CATEGORIES]
        super().__init__(placeholder="Select a category...", min_values=1, max_values=1, options=options)
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        try:
            await self.callback_func(interaction, self.values[0])
        except Exception as e:
            print(f"[ERROR] CategorySelect callback failed: {e}")
            await interaction.response.send_message("❌ Something went wrong while loading the category.", ephemeral=True)



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
                    name=f"{item.get('display', '')} {item['name']} - {item.get('price', 0)} gold",
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
            
        @self.shop_group.command(name="buy", description="🍯 - 🛒 Buy an item by category and ID with confirmation")
        @app_commands.describe(
            category="The item category (e.g. trail, armor, weapon)",
            item_id="The item ID to buy from that category"
        )
        async def shop_buy(interaction: discord.Interaction, category: str, item_id: str):
            from store_utils import get_item_by_category

            # Fetch items by category
            items = get_item_by_category(category.lower())
            if not items:
                return await interaction.response.send_message(
                    f"❌ No items found for category `{category}`.",
                    ephemeral=True
                )

            # Try to find item in that category
            item = next((i for i in items if i.get("id", "").lower() == item_id.lower()), None)
            if not item:
                return await interaction.response.send_message(
                    f"❌ No item with ID `{item_id}` found in category `{category}`.",
                    ephemeral=True
                )

            item_type = item.get("category", "").lower()

            # 🚫 Block direct title purchases
            if item_type == "titles":
                return await interaction.response.send_message(
                    "🎲 Titles can only be obtained through rolls using `/shop roll`. Direct purchase is not allowed.",
                    ephemeral=True
                )

            name = item.get("name", item_id)
            price = item.get("price", 0)

            embed = discord.Embed(
                title=f"🛒 Confirm Purchase: {name}",
                description=f"**Price:** {price} gold\nDo you want to buy this item?",
                color=discord.Color.gold()
            )

            view = ConfirmPurchaseView(interaction.user.id, item["id"], item_type)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


        @self.shop_group.command(name="sell", description="🍯 - 💰 Sell an unequipped item for 60% of its value")
        @app_commands.describe(item_id="The ID of the item you want to sell")
        async def shop_sell(interaction: discord.Interaction, item_id: str):
            user_id = interaction.user.id

            from cogs.character.user_inventory import user_inventory, engine
            from cogs.store.store_utils import get_item_by_id, get_user_data, update_user_data, remove_item_from_inventory

            if DEBUG:
                print(f"[DEBUG]🍯💰 Attempting to sell item '{item_id}' for user {user_id}")

            with engine.begin() as conn:
                stmt = select(user_inventory).where(
                    (user_inventory.c.user_id == user_id) &
                    (user_inventory.c.item_id == item_id)
                )
                result = conn.execute(stmt).fetchone()

                if not result:
                    await interaction.response.send_message("❌ Item not found in your inventory.", ephemeral=True)
                    return

                if result.equipped:
                    await interaction.response.send_message("❌ You must unequip the item before selling it.", ephemeral=True)
                    return

                if result.item_type == "titles":
                    await interaction.response.send_message("❌ Titles cannot be sold.", ephemeral=True)
                    return

            item = get_item_by_id(item_id)
            if not item:
                await interaction.response.send_message("❌ Item data not found.", ephemeral=True)
                return

            price = item.get("price", 0)
            refund = int(price * 0.6)

            data = get_user_data(user_id)
            data["gold"] += refund
            update_user_data(
                user_id,
                data["multiplier"],
                data["daily_multiplier"],
                data["last_message_ts"],
                data["last_multiplier_update"],
                gold=data["gold"]
            )

            remove_item_from_inventory(user_id, item_id, result.item_type)

            if DEBUG:
                print(f"[DEBUG]🍯💰 User {user_id} sold '{item_id}' for {refund} gold.")
            await interaction.response.send_message(
                f"✅ You sold **{item.get('name', item_id)}** for **{refund}** gold!", ephemeral=True
            )


        @self.shop_group.command(name="roll", description="🍯 - 🎲 Roll for a random unclaimed title")
        async def roll_title(interaction: Interaction):
            embed = Embed(
                title="🎲 Roll for a Title",
                description=f"Rolling costs **{ROLL_PRICE} gold**. You will receive a random unclaimed title.\nDo you want to proceed?",
                color=discord.Color.gold()
            )

            view = ConfirmTitleRollView(interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        class ConfirmTitleRollView(View):
            def __init__(self, user_id):
                super().__init__(timeout=30)
                self.user_id = user_id

            @button(label="Yes", style=ButtonStyle.green, emoji="🎲")
            async def confirm(self, interaction: Interaction, button):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("🍯❌ Not your confirmation!", ephemeral=True)

                success, result = roll_random_title_for_user(self.user_id, price=ROLL_PRICE)

                if not success:
                    await interaction.response.edit_message(content=result, view=None)  # result is error message
                    return

                title = result  # result is the title dict

                embed = discord.Embed(
                    title=f"🎲 {interaction.user.display_name} has claimed a Title!",
                    description=f"**{title['name']}**\n{title.get('description', 'A rare find...')}",
                    color=discord.Color.gold()
                )

                if title.get("avatar_url"):
                    embed.set_image(url=title["avatar_url"])

                # Send to public EXP channel
                channel = interaction.client.get_channel(EXP_CHANNEL_ID)
                if channel:
                    await channel.send(embed=embed)

                # Remove the ephemeral view
                await interaction.response.edit_message(content="🎲 Title rolled and broadcasted!", view=None)

            @button(label="No", style=ButtonStyle.red, emoji="❌")
            async def cancel(self, interaction: Interaction, button):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("🍯❌ Not your confirmation!", ephemeral=True)
                await interaction.response.edit_message(content="🎲❌ Roll cancelled.", view=None)




    async def show_items_by_category(self, interaction, category_name):
        category_key = category_name.lower()
        items = get_item_by_category(category_key)
        if not items:
            await interaction.response.send_message(f"No items found in category `{category_name}`.", ephemeral=True)
            return

        is_title = category_key == "titles"

        if is_title:
            pages = items  # One title per page
        else:
            pages = [items[i:i+5] for i in range(0, len(items), 5)]

        current_page = 0


        async def get_embed(page):
            if is_title:
                item = items[page]
                embed = discord.Embed(
                    title=f"🍯 {item['name']}",
                    description=item.get('short_description') or item.get('description', 'No description.'),
                    color=discord.Color.dark_gold()
                )
                embed.set_footer(text=f"Title {page+1} of {len(items)}")

                if item.get("avatar_url"):
                    embed.set_image(url=item["avatar_url"])

                # ⬇️ Ownership status logic
                from cogs.store.store_utils import get_user_by_title_id

                owner_id = get_user_by_title_id(item['id'])
                if owner_id:
                    try:
                        user = await interaction.client.fetch_user(owner_id)
                        embed.add_field(name="Status", value=f"🍯❌ Taken by {user.mention}", inline=False)
                    except Exception as e:
                        print(f"[ERROR] Failed to fetch user for title owner: {e}")
                        traceback.print_exc()
                        embed.add_field(name="Status", value="🍯❌ Taken (unable to resolve user)", inline=False)
                else:
                    embed.add_field(name="Status", value="🍯✅ Available", inline=False)

            else:
                embed = discord.Embed(
                    title=f"🍯 {category_name.title()} Items (Page {page+1}/{len(pages)})",
                    color=discord.Color.blue()
                )
                for item in pages[page]:
                    title_line = f"{item.get('display', '')} {item['name']} - {item.get('price', 0)} gold".strip()
                    description = item.get('short_description') or item.get('description', 'No description.')
                    embed.add_field(name=title_line, value=description, inline=False)

            return embed

        view = Paginator(get_embed, pages, self.send_category_selection)
        await interaction.response.edit_message(embed=await get_embed(current_page), view=view)

        
    async def send_category_selection(self, interaction):
        embed = discord.Embed(title="🍯 Malta's CRPG Item Shop", color=discord.Color.gold())
        embed.description = "Select a category below to view items."
        embed.set_image(url="http://ynyng.org/wp-content/uploads/2025/03/ynyng_malta__hospitaller_very_organized_and_open_medieval_shop__26cf32ee-fe4e-405e-ba6c-b306edae40e6-1.png")

        await interaction.response.edit_message(embed=embed, view=CategoryView(interaction, self.show_items_by_category))



class Paginator(discord.ui.View):
    def __init__(self, get_embed, pages, show_category_callback):
        super().__init__(timeout=120)
        self.page = 0
        self.get_embed = get_embed
        self.pages = pages
        self.show_category_callback = show_category_callback

    @discord.ui.button(label="🍯 Back to Shop", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_category_callback(interaction)

    @discord.ui.button(label="🍯⬅️ Previous", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=await self.get_embed(self.page), view=self)

    @discord.ui.button(label="Next ➡️🍯", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.pages) - 1:
            self.page += 1
            await interaction.response.edit_message(embed=await self.get_embed(self.page), view=self)

class ConfirmPurchaseView(discord.ui.View):
    def __init__(self, user_id, item_id, item_type):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.item_id = item_id
        self.item_type = item_type

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, emoji="💰")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🍯❌ Not your confirmation!", ephemeral=True)

        from cogs.store.store_utils import process_purchase, get_item_by_id
        from cogs.exp_config import EXP_CHANNEL_ID

        success, message = process_purchase(self.user_id, self.item_id, self.item_type)

        await interaction.response.edit_message(content=message, view=None)

        if success:
            item = get_item_by_id(self.item_id)
            item_name = item.get("name", self.item_id)
            public_message = f"🍯🛒 **{interaction.user.display_name}** has purchased **{item_name}**!"
            exp_channel = interaction.client.get_channel(EXP_CHANNEL_ID)
            if exp_channel:
                await exp_channel.send(public_message)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("🍯❌ Not your confirmation!", ephemeral=True)

        await interaction.response.edit_message(content="🍯❌ Purchase cancelled.", view=None)


    def cog_load(self):
        pass

async def setup(bot):
    cog = StoreGroup(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.shop_group)  # <-- this ensures /shop commands get registered

