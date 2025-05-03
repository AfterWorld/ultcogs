import discord
import random
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from redbot.core import commands

class FruitCommands:
    """Handles all devil fruit related commands."""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.config = cog.config
        self.logger = cog.logger
        self.data_manager = cog.data_manager
        
        # Import constants
        from ..constants.devil_fruits import DEVIL_FRUITS
        self.DEVIL_FRUITS = DEVIL_FRUITS
        
    def is_fruit_rare(self, fruit_name: str) -> bool:
        """Check if a devil fruit is rare."""
        return fruit_name in self.DEVIL_FRUITS["Rare"]
        
    @commands.command()
    async def removefruit(self, ctx, member: discord.Member = None):
        """Remove a user's Devil Fruit. Owners and Admins remove for free, others pay 1,000,000 berries from their bounty."""
        user = ctx.author
        member = member or user  # Defaults to the user running the command
        
        # Check if user is bot owner or has admin permissions
        is_owner = await self.bot.is_owner(user)
        is_admin = ctx.author.guild_permissions.administrator

        # Add permissions message for removing other people's fruits
        if member != user and not (is_owner or is_admin):
            return await ctx.send("❌ You can only remove your own Devil Fruit unless you're an admin!")

        # Check if user has a fruit
        fruit = await self.data_manager.get_devil_fruit(member)
        if not fruit:
            return await ctx.send(f"🍏 **{member.display_name}** has no Devil Fruit to remove!")

        # Owners and Admins remove the fruit for free
        if is_owner or is_admin:
            # Clear the fruit
            success = await self.data_manager.set_devil_fruit(member, None)
            if not success:
                return await ctx.send("❌ An error occurred while removing the fruit. Please try again.")
            
            return await ctx.send(f"🛡️ **{user.display_name}** removed `{fruit}` from **{member.display_name}** for free!")

        # Normal users must pay from their bounty
        cost = 1_000_000
        current_bounty = await self.data_manager.get_bounty(user)

        if current_bounty < cost:
            return await ctx.send(f"❌ You need a bounty of at least **{cost:,}** berries to remove your Devil Fruit.")

        # Deduct cost and remove fruit
        new_bounty = await self.data_manager.safe_modify_bounty(user, cost, "subtract")
        if new_bounty is None:
            return await ctx.send("❌ Failed to update your bounty. Please try again.")
            
        success = await self.data_manager.set_devil_fruit(member, None)
        if not success:
            # Refund the cost if fruit removal fails
            await self.data_manager.safe_modify_bounty(user, cost, "add")
            return await ctx.send("❌ An error occurred while removing the fruit. Please try again.")

        await ctx.send(
            f"<:Beli:1237118142774247425> **{user.display_name}** paid **{cost:,}** berries from their bounty to remove `{fruit}`!\n"
            f"That fruit can now be found again! 🍏"
        )
    
    @commands.group(name="fruits", invoke_without_command=True)
    async def fruits(self, ctx):
        """
        Display Devil Fruit statistics and information.
        Use subcommands 'rare' or 'common' to view specific fruit lists.
        """
        # Load bounties data
        bounties = self.data_manager.load_bounties()
        
        # Count fruits by type
        rare_owned = 0
        common_owned = 0
        total_rare = len(self.DEVIL_FRUITS["Rare"])
        total_common = len(self.DEVIL_FRUITS["Common"])
        
        # Track fruit ownership
        for data in bounties.values():
            fruit = data.get("fruit")
            if fruit:
                if fruit in self.DEVIL_FRUITS["Rare"]:
                    rare_owned += 1
                elif fruit in self.DEVIL_FRUITS["Common"]:
                    common_owned += 1
        
        embed = discord.Embed(
            title="<:MeraMera:1336888578705330318> Devil Fruit Statistics <:MeraMera:1336888578705330318>",
            color=discord.Color.gold()
        )
        
        # Add general statistics
        embed.add_field(
            name="📊 Overall Statistics",
            value=(
                f"**Total Devil Fruits:** `{total_rare + total_common}`\n"
                f"**Currently Owned:** `{rare_owned + common_owned}`\n"
                f"**Available:** `{(total_rare + total_common) - (rare_owned + common_owned)}`"
            ),
            inline=False
        )
        
        # Add rare fruit statistics
        embed.add_field(
            name="🌟 Rare Fruits",
            value=(
                f"**Total:** `{total_rare}`\n"
                f"**Owned:** `{rare_owned}`\n"
                f"**Available:** `{total_rare - rare_owned}`"
            ),
            inline=True
        )
        
        # Add common fruit statistics
        embed.add_field(
            name="🍎 Common Fruits",
            value=(
                f"**Total:** `{total_common}`\n"
                f"**Owned:** `{common_owned}`\n"
                f"**Available:** `{total_common - common_owned}`"
            ),
            inline=True
        )
        
        # Add command help
        embed.add_field(
            name="💡 Available Commands",
            value=(
                "`.fruits rare` - View rare Devil Fruits\n"
                "`.fruits common` - View common Devil Fruits"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @fruits.command(name="rare")
    async def fruits_rare(self, ctx):
        """Display all rare Devil Fruit users with detailed information."""
        # Load bounties data
        bounties = self.data_manager.load_bounties()
        
        # Get rare fruits data
        rare_fruits = self.DEVIL_FRUITS["Rare"]
        
        # Track ownership
        owned_fruits = {}
        available_fruits = []
        
        # Check ownership
        for user_id, data in bounties.items():
            fruit = data.get("fruit")
            if fruit in rare_fruits:
                try:
                    member = ctx.guild.get_member(int(user_id))
                    if member:
                        fruit_data = rare_fruits[fruit]
                        owned_fruits[fruit] = {
                            "owner": member.display_name,
                            "type": fruit_data["type"],
                            "bonus": fruit_data["bonus"]
                        }
                except:
                    continue
        
        # Get available fruits
        available_fruits = [fruit for fruit in rare_fruits if fruit not in owned_fruits]
        
        # Create pages - separate owners and available fruits
        owned_embeds = []
        available_embeds = []
        
        # Process owned fruits (3 per page)
        owned_chunks = [list(owned_fruits.items())[i:i + 3] for i in range(0, len(owned_fruits), 3)]
        
        for page, chunk in enumerate(owned_chunks):
            embed = discord.Embed(
                title="🌟 Rare Devil Fruits - Owned",
                description=f"Page {page + 1}/{len(owned_chunks) or 1}",
                color=discord.Color.gold()
            )
            
            for fruit, data in chunk:
                embed.add_field(
                    name=f"{fruit} ({data['type']})",
                    value=(
                        f"👤 Owner: {data['owner']}\n"
                        f"✨ Power: {data['bonus']}"
                    ),
                    inline=False
                )
            
            owned_embeds.append(embed)
        
        # Process available fruits (5 per page)
        available_chunks = [available_fruits[i:i + 5] for i in range(0, len(available_fruits), 5)]
        
        for page, chunk in enumerate(available_chunks):
            embed = discord.Embed(
                title="🌟 Rare Devil Fruits - Available",
                description=f"Page {page + 1}/{len(available_chunks) or 1}",
                color=discord.Color.purple()
            )
            
            for fruit in chunk:
                fruit_data = rare_fruits[fruit]
                embed.add_field(
                    name=f"{fruit} ({fruit_data['type']})",
                    value=f"✨ Power: {fruit_data['bonus']}",
                    inline=False
                )
            
            available_embeds.append(embed)
        
        # Add statistics embed
        stats_embed = discord.Embed(
            title="🌟 Rare Devil Fruits - Statistics",
            color=discord.Color.gold()
        )
        
        stats_embed.add_field(
            name="📊 Statistics",
            value=(
                f"Total Rare Fruits: `{len(rare_fruits)}`\n"
                f"Owned Fruits: `{len(owned_fruits)}`\n"
                f"Available Fruits: `{len(available_fruits)}`"
            ),
            inline=False
        )
        
        # Combine all embeds
        all_embeds = owned_embeds + available_embeds + [stats_embed]
        
        if not all_embeds:
            embed = discord.Embed(
                title="🌟 Rare Devil Fruits",
                description="No rare Devil Fruits found!",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)
        
        # Send first embed
        current_page = 0
        message = await ctx.send(embed=all_embeds[current_page])
        
        # Add navigation reactions if multiple pages
        if len(all_embeds) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == "➡️":
                        current_page = (current_page + 1) % len(all_embeds)
                    elif str(reaction.emoji) == "⬅️":
                        current_page = (current_page - 1) % len(all_embeds)
                        
                    await message.edit(embed=all_embeds[current_page])
                    await message.remove_reaction(reaction, user)
                    
                except asyncio.TimeoutError:
                    break
            
            await message.clear_reactions()

    @fruits.command(name="common")
    async def fruits_common(self, ctx):
        """Display all common Devil Fruit users with detailed information."""
        # Load bounties data
        bounties = self.data_manager.load_bounties()
        
        # Get common fruits data
        common_fruits = self.DEVIL_FRUITS["Common"]
        
        # Track ownership
        owned_fruits = {}
        available_fruits = []
        
        # Check ownership
        for user_id, data in bounties.items():
            fruit = data.get("fruit")
            if fruit in common_fruits:
                try:
                    member = ctx.guild.get_member(int(user_id))
                    if member:
                        fruit_data = common_fruits[fruit]
                        owned_fruits[fruit] = {
                            "owner": member.display_name,
                            "type": fruit_data["type"],
                            "bonus": fruit_data["bonus"]
                        }
                except:
                    continue
        
        # Get available fruits
        available_fruits = [fruit for fruit in common_fruits if fruit not in owned_fruits]
        
        # Create pages - separate owners and available fruits across multiple pages
        owned_embeds = []
        available_embeds = []
        
        # Process owned fruits (5 per page to ensure we don't exceed limits)
        owned_chunks = [list(owned_fruits.items())[i:i + 5] for i in range(0, len(owned_fruits), 5)]
        
        for page, chunk in enumerate(owned_chunks):
            embed = discord.Embed(
                title="🍎 Common Devil Fruits - Owned",
                description=f"Page {page + 1}/{len(owned_chunks) or 1}",
                color=discord.Color.blue()
            )
            
            for fruit, data in chunk:
                embed.add_field(
                    name=f"{fruit} ({data['type']})",
                    value=(
                        f"👤 Owner: {data['owner']}\n"
                        f"✨ Power: {data['bonus']}"
                    ),
                    inline=False
                )
            
            owned_embeds.append(embed)
        
        # Process available fruits (10 per page - they're shorter)
        available_chunks = [available_fruits[i:i + 10] for i in range(0, len(available_fruits), 10)]
        
        for page, chunk in enumerate(available_chunks):
            embed = discord.Embed(
                title="🍎 Common Devil Fruits - Available",
                description=f"Page {page + 1}/{len(available_chunks) or 1}",
                color=discord.Color.green()
            )
            
            for fruit in chunk:
                fruit_data = common_fruits[fruit]
                embed.add_field(
                    name=f"{fruit} ({fruit_data['type']})",
                    value=f"✨ Power: {fruit_data['bonus']}",
                    inline=False
                )
            
            available_embeds.append(embed)
        
        # Add statistics embed
        stats_embed = discord.Embed(
            title="🍎 Common Devil Fruits - Statistics",
            color=discord.Color.gold()
        )
        
        stats_embed.add_field(
            name="📊 Statistics",
            value=(
                f"Total Common Fruits: `{len(common_fruits)}`\n"
                f"Owned Fruits: `{len(owned_fruits)}`\n"
                f"Available Fruits: `{len(available_fruits)}`"
            ),
            inline=False
        )
        
        # Combine all embeds
        all_embeds = owned_embeds + available_embeds + [stats_embed]
        
        if not all_embeds:
            embed = discord.Embed(
                title="🍎 Common Devil Fruits",
                description="No Devil Fruits found!",
                color=discord.Color.blue()
            )
            return await ctx.send(embed=embed)
        
        # Send first embed
        current_page = 0
        message = await ctx.send(embed=all_embeds[current_page])
        
        # Add navigation reactions if multiple pages
        if len(all_embeds) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == "➡️":
                        current_page = (current_page + 1) % len(all_embeds)
                    elif str(reaction.emoji) == "⬅️":
                        current_page = (current_page - 1) % len(all_embeds)
                        
                    await message.edit(embed=all_embeds[current_page])
                    await message.remove_reaction(reaction, user)
                    
                except asyncio.TimeoutError:
                    break
            
            await message.clear_reactions()
