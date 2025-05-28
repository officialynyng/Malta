import discord
from discord import app_commands, Interaction
from discord.ext import commands
from sqlalchemy.sql import select, update
from sqlalchemy import or_

from cogs.exp_config import EXP_CHANNEL_ID
from cogs.store.store_utils import get_item_by_id
from cogs.exp_config import engine
from cogs.database.user_inventory_table import user_inventory



DEBUG = True
user_group = app_commands.Group(name="user", description="Manage your inventory and items")

class UserInventoryGroup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

@user_group.command(name="inventory", description="👤 - 🎒 View your current inventory and equipped items")
async def view_inventory(interaction: Interaction):
    user_id = interaction.user.id
    if DEBUG:
        print(f"[DEBUG]👤🎒 Checking inventory for user {user_id}")

    with engine.connect() as conn:
        stmt = select(user_inventory).where(user_inventory.c.user_id == user_id)
        results = conn.execute(stmt).fetchall()

    equipped = [row for row in results if row.equipped]
    unequipped = [row for row in results if not row.equipped]

    embed = discord.Embed(title=f"🎒 Inventory for {interaction.user.display_name}", color=discord.Color.green())
    embed.add_field(name="🛡️ Equipped Gear", value="\u200b", inline=False)

    armor_slots = ["armor_head", "armor_torso", "armor_shoulders", "armor_legs", "armor_hands"]
    gear_displayed = set()

    for slot in armor_slots:
        found = next((item for item in equipped if item.item_type == slot), None)
        label = slot.replace("armor_", "").capitalize()
        if found:
            embed.add_field(name=f"{label}:", value=f"{found.item_id}", inline=True)
            gear_displayed.add(found.item_id)
        else:
            embed.add_field(name=f"{label}:", value="(empty)", inline=True)

    title = next((item for item in equipped if item.item_type == "titles"), None)
    embed.add_field(name="Title:", value=title.item_id if title else "(empty)", inline=True)

    trail = next((item for item in equipped if item.item_type == "trails"), None)
    embed.add_field(name="Trail:", value=trail.item_id if trail else "(empty)", inline=True)

    shield = next((item for item in equipped if item.item_type == "shields"), None)
    embed.add_field(name="Shield:", value=shield.item_id if shield else "(empty)", inline=True)

    for label, key in [("Pet", "pets"), ("Mount", "mounts"), ("Estate", "estates"), ("Utility", "utility")]:
        entry = next((item for item in equipped if item.item_type == key), None)
        embed.add_field(name=f"{label}:", value=entry.item_id if entry else "(empty)", inline=True)

    weapon_types = ["weapons", "arrows", "bolts"]
    shared_weapons = [item for item in equipped if any(item.item_type.startswith(prefix) for prefix in weapon_types)]
    for idx in range(4):
        try:
            embed.add_field(name=f"Slot {idx+1}:", value=shared_weapons[idx].item_id, inline=True)
        except IndexError:
            embed.add_field(name=f"Slot {idx+1}:", value="(empty)", inline=True)

    unequipped_ids = [f"{item.item_id} [{item.item_type}]" for item in unequipped]
    uneq_str = "\n".join(unequipped_ids) or "(none)"
    embed.add_field(name="🎒 Unequipped(Inventory)", value=uneq_str, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)



@user_group.command(name="unequip", description="👤 - ❌📦 Unequip an item by name")
@app_commands.describe(item_id="The ID of the item you want to unequip")
async def unequip_item(interaction: Interaction, item_id: str):
    user_id = interaction.user.id
    if DEBUG:
        print(f"[DEBUG]👤📦❌ Attempting to unequip '{item_id}' for user {user_id}")

    with engine.begin() as conn:
        stmt = select(user_inventory).where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_id == item_id)
        )
        result = conn.execute(stmt).fetchone()

        if not result:
            if DEBUG:
                print(f"[DEBUG]👤📦❌ Item '{item_id}' not found in inventory for user {user_id}")
            await interaction.response.send_message("❌ Item not found in your inventory.", ephemeral=True)
            return

        if result.item_type == "titles":
            if DEBUG:
                print(f"[DEBUG]👤📦🚫 Attempted to unequip title '{item_id}' for user {user_id}")
            await interaction.response.send_message("❌ Titles cannot be unequipped.", ephemeral=True)
            return

        update_stmt = update(user_inventory).where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_id == item_id)
        ).values(equipped=False)
        conn.execute(update_stmt)

    if DEBUG:
        print(f"[DEBUG]👤📦✅ Unequipped item '{item_id}' for user {user_id}")
    await interaction.response.send_message(f"❌ You have unequipped **{item_id}**.", ephemeral=True)

@user_group.command(name="equip", description="👤 - ✅📦 Equip an item by name")
@app_commands.describe(item_id="The ID of the item you want to equip")
async def equip_item(interaction: Interaction, item_id: str):
    user_id = interaction.user.id
    if DEBUG:
        print(f"[DEBUG]👤📦✅ Attempting to equip '{item_id}' for user {user_id}")

    with engine.begin() as conn:
        # Confirm ownership
        stmt = select(user_inventory).where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_id == item_id)
        )
        result = conn.execute(stmt).fetchone()

        if not result:
            if DEBUG:
                print(f"[DEBUG]👤📦❌ Item '{item_id}' not found in inventory for user {user_id}")
            await interaction.response.send_message("❌ Item not found in your inventory.", ephemeral=True)
            return

        if result.item_type == "titles":
            if DEBUG:
                print(f"[DEBUG]👤📦🚫 Attempted to equip title '{item_id}' manually for user {user_id}")
            await interaction.response.send_message("❌ Titles are auto-equipped and cannot be changed manually.", ephemeral=True)
            return

        if any(result.item_type.startswith(prefix) for prefix in ["weapons", "arrows", "bolts"]):
            weapon_ammo_filters = or_(
                user_inventory.c.item_type.like("weapons%"),
                user_inventory.c.item_type.like("arrows%"),
                user_inventory.c.item_type.like("bolts%")
            )
            count_stmt = select(user_inventory).where(
                (user_inventory.c.user_id == user_id) &
                weapon_ammo_filters &
                (user_inventory.c.equipped == True)
            )
            equipped_count = len(conn.execute(count_stmt).fetchall())
            if equipped_count >= 4:
                if DEBUG:
                    print(f"[DEBUG]👤📦❌ User {user_id} already has 4 equipped weapon/ammo items.")
                await interaction.response.send_message("❌ You can only have 4 total weapons/ammo equipped.", ephemeral=True)
                return

        else:
            # Unequip others of same type (for armor)
            unequip_stmt = update(user_inventory).where(
                (user_inventory.c.user_id == user_id) &
                (user_inventory.c.item_type == result.item_type)
            ).values(equipped=False)
            conn.execute(unequip_stmt)

        equip_stmt = update(user_inventory).where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_id == item_id)
        ).values(equipped=True)
        conn.execute(equip_stmt)

    if DEBUG:
        print(f"[DEBUG]👤📦✅ Equipped item '{item_id}' for user {user_id}")
    await interaction.response.send_message(f"✅ You have equipped **{item_id}**.", ephemeral=True)

@user_group.command(name="gift", description="👤 - 🎁 Gift an item to another user")
@app_commands.describe(item_id="The ID of the item you want to gift", member="The user to gift the item to")
async def gift_item(interaction: Interaction, item_id: str, member: discord.Member):
    user_id = interaction.user.id
    recipient_id = member.id

    if DEBUG:
        print(f"[DEBUG]🎁 Attempting gift of '{item_id}' from {user_id} to {recipient_id}")

    if user_id == recipient_id:
        return await interaction.response.send_message("❌ You can't gift items to yourself.", ephemeral=True)

    with engine.connect() as conn:
        stmt = select(user_inventory).where(
            (user_inventory.c.user_id == user_id) &
            (user_inventory.c.item_id == item_id)
        )
        result = conn.execute(stmt).fetchone()

    if not result:
        return await interaction.response.send_message("❌ Item not found in your inventory.", ephemeral=True)

    if result.item_type == "titles":
        return await interaction.response.send_message("❌ Titles cannot be gifted.", ephemeral=True)

    item = get_item_by_id(item_id)
    item_name = item.get("display", item_id)

    embed = discord.Embed(
        title="🎁 Confirm Gift",
        description=f"Are you sure you want to gift **{item_name}** to **{member.display_name}**?\n\n⚠️ *There is no guarantee you will ever get this item back.*",
        color=discord.Color.orange()
    )

    class ConfirmGiftView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)

        @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, emoji="✅")
        async def confirm(self, i: Interaction, _):
            if i.user.id != user_id:
                return await i.response.send_message("❌ Not your confirmation.", ephemeral=True)

            with engine.begin() as conn:
                # Remove from sender
                conn.execute(
                    user_inventory.delete().where(
                        (user_inventory.c.user_id == user_id) &
                        (user_inventory.c.item_id == item_id)
                    )
                )
                # Add to recipient unequipped
                conn.execute(
                    user_inventory.insert().values(
                        user_id=recipient_id,
                        item_id=item_id,
                        item_type=result.item_type,
                        equipped=False
                    )
                )

            # Public EXP post
            channel = interaction.client.get_channel(EXP_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"🎁 **{interaction.user.display_name}** has gifted **{item_name}** to **{member.display_name}**!"
                )

            await i.response.edit_message(content=f"🎁 Gifted **{item_name}** to {member.mention}!", view=None)

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
        async def cancel(self, i: Interaction, _):
            if i.user.id != user_id:
                return await i.response.send_message("❌ Not your confirmation.", ephemeral=True)
            await i.response.edit_message(content="❌ Gift cancelled.", view=None)

    await interaction.response.send_message(embed=embed, view=ConfirmGiftView(), ephemeral=True)


async def setup(bot):
    cog = UserInventoryGroup(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(user_group)
