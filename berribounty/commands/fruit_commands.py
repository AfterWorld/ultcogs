"""Devil fruit commands for the One Piece bot."""

import discord
import random
from redbot.core import commands
from typing import Optional
from ..ui import FruitSearchView
from ..constants.fruits import DEVIL_FRUITS
from ..formatters import format_devil_fruit_info, format_berries

class FruitCommands:
    """Devil fruit command handlers."""
    
    def __init__(self, bot, fruit_manager, player_manager):
        self.bot = bot
        self.fruit_manager = fruit_manager
        self.player_manager = player_manager
    
    async def search(self, ctx: commands.Context):
        """Search for devil fruits."""
        player = await self.player_manager.get_or_create_player(ctx.author)
        
        # Check if player already has a fruit
        if player.devil_fruit:
            embed = discord.Embed(
                title="🍎 You Already Have a Devil Fruit",
                description=f"You already possess the **{player.devil_fruit}**!\n"
                          "You cannot eat another devil fruit or it would be fatal!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Your Current Fruit",
                value=player.devil_fruit,
                inline=True
            )
            
            fruit_data = player.devil_fruit_data
            if fruit_data:
                embed.add_field(
                    name="Type",
                    value=fruit_data.get("type", "Unknown"),
                    inline=True
                )
            
            embed.add_field(
                name="💡 Tip",
                value="You can still visit the market to see other fruits!",
                inline=False
            )
            
            # Still allow market access
            view = FruitSearchView(player, self.fruit_manager)
            await ctx.send(embed=embed, view=view)
            return
        
        # Create search interface
        embed = discord.Embed(
            title="🏝️ Devil Fruit Search",
            description="Search the Grand Line for mysterious devil fruits!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🗺️ Search Islands",
            value="Explore mysterious islands to find devil fruits.\n"
                  "• Costs berries to search\n"
                  "• Higher chance with more berries\n"
                  "• 3 searches per day maximum",
            inline=True
        )
        
        embed.add_field(
            name="🏪 Visit Market",
            value="Browse devil fruits for sale.\n"
                  "• Guaranteed fruits available\n"
                  "• Higher prices for rare fruits\n"
                  "• Selection changes daily",
            inline=True
        )
        
        embed.add_field(
            name="📚 Your Collection",
            value="View your current devil fruit.\n"
                  "• See fruit abilities\n"
                  "• Check special moves\n"
                  "• Power information",
            inline=True
        )
        
        # Show player's current stats for context
        embed.add_field(
            name="💰 Your Resources",
            value=f"Berries: {format_berries(player.berries)}\n"
                  "Devil Fruit: None",
            inline=False
        )
        
        view = FruitSearchView(player, self.fruit_manager)
        await ctx.send(embed=embed, view=view)
    
    async def list_fruits(self, ctx: commands.Context, category: str = "all"):
        """List available devil fruits."""
        valid_categories = ["all", "common", "rare", "paramecia", "zoan", "logia"]
        
        if category.lower() not in valid_categories:
            await ctx.send(f"❌ Invalid category! Valid options: {', '.join(valid_categories)}")
            return
        
        embed = discord.Embed(
            title="📜 Devil Fruit Encyclopedia",
            color=discord.Color.purple()
        )
        
        # Add fruits based on category
        if category.lower() in ["all", "common"]:
            common_fruits = list(DEVIL_FRUITS["common"].keys())[:10]  # Show first 10
            if common_fruits:
                embed.add_field(
                    name="🍎 Common Fruits",
                    value="\n".join([f"• {fruit}" for fruit in common_fruits]),
                    inline=True
                )
        
        if category.lower() in ["all", "rare"]:
            rare_fruits = list(DEVIL_FRUITS["rare"].keys())[:10]  # Show first 10
            if rare_fruits:
                embed.add_field(
                    name="💎 Rare Fruits",
                    value="\n".join([f"• {fruit}" for fruit in rare_fruits]),
                    inline=True
                )
        
        # Filter by type if specified
        if category.lower() in ["paramecia", "zoan", "logia"]:
            type_fruits = []
            for rarity, fruits in DEVIL_FRUITS.items():
                for name, data in fruits.items():
                    if data.get("type", "").lower() == category.lower():
                        type_fruits.append(name)
            
            if type_fruits:
                embed.add_field(
                    name=f"🔮 {category.title()} Type Fruits",
                    value="\n".join([f"• {fruit}" for fruit in type_fruits[:15]]),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"🔮 {category.title()} Type Fruits",
                    value="No fruits found in this category.",
                    inline=False
                )
        
        # Add usage instructions
        embed.add_field(
            name="💡 Usage",
            value=f"Use `{ctx.prefix}fruit info <fruit_name>` to learn about a specific fruit!",
            inline=False
        )
        
        # Show total counts
        total_common = len(DEVIL_FRUITS["common"])
        total_rare = len(DEVIL_FRUITS["rare"])
        embed.set_footer(text=f"Total Fruits: {total_common + total_rare} ({total_common} Common, {total_rare} Rare)")
        
        await ctx.send(embed=embed)
    
    async def info(self, ctx: commands.Context, *, fruit_name: Optional[str] = None):
        """Get information about a devil fruit."""
        if fruit_name is None:
            # Show player's current fruit if they have one
            player = await self.player_manager.get_or_create_player(ctx.author)
            
            if not player.devil_fruit:
                await ctx.send("❌ You don't have a devil fruit! Use `fruit info <fruit_name>` to learn about specific fruits.")
                return
            
            fruit_name = player.devil_fruit
            embed = format_devil_fruit_info(fruit_name, player.devil_fruit_data)
            embed.title = f"🍎 Your Devil Fruit: {fruit_name}"
            embed.description = f"**{fruit_name}**\n{embed.description}"
            
            # Add personal stats if available
            if hasattr(player, 'fruit_mastery'):
                embed.add_field(
                    name="🎯 Mastery",
                    value=f"{player.fruit_mastery.get(fruit_name, 0)}%",
                    inline=True
                )
            
            await ctx.send(embed=embed)
            return
        
        # Search for the fruit in all categories
        found_fruit = None
        fruit_data = None
        fruit_category = None
       
        # Search in all categories
        for category, fruits in DEVIL_FRUITS.items():
           for name, data in fruits.items():
               if name.lower() == fruit_name.lower():
                   found_fruit = name
                   fruit_data = data
                   fruit_category = category
                   break
           if found_fruit:
               break
       
        # Try partial matching if exact match not found
        if not found_fruit:
           possible_matches = []
           for category, fruits in DEVIL_FRUITS.items():
               for name in fruits.keys():
                   if fruit_name.lower() in name.lower():
                       possible_matches.append((name, category))
           
           if len(possible_matches) == 1:
               found_fruit, fruit_category = possible_matches[0]
               fruit_data = DEVIL_FRUITS[fruit_category][found_fruit]
           elif len(possible_matches) > 1:
               embed = discord.Embed(
                   title="🔍 Multiple Fruits Found",
                   description=f"Found multiple fruits matching '{fruit_name}':",
                   color=discord.Color.orange()
               )
               
               match_text = "\n".join([f"• {name} ({category})" for name, category in possible_matches[:10]])
               embed.add_field(name="Matches", value=match_text, inline=False)
               embed.add_field(
                   name="💡 Tip",
                   value="Please be more specific with the fruit name.",
                   inline=False
               )
               
               await ctx.send(embed=embed)
               return
       
        if not found_fruit:
           embed = discord.Embed(
               title="❌ Fruit Not Found",
               description=f"Could not find a devil fruit named '{fruit_name}'.",
               color=discord.Color.red()
           )
           
           embed.add_field(
               name="💡 Suggestions",
               value=f"• Check spelling\n"
                     f"• Use `{ctx.prefix}fruit list` to see available fruits\n"
                     f"• Try searching with partial names",
               inline=False
           )
           
           await ctx.send(embed=embed)
           return
       
        # Create detailed fruit information embed
        embed = format_devil_fruit_info(found_fruit, fruit_data)
        embed.color = discord.Color.red() if fruit_category == "rare" else discord.Color.orange()
       
        # Add rarity and availability info
        embed.add_field(
           name="📊 Rarity",
           value=fruit_category.title(),
           inline=True
        )
       
        # Check if fruit is available
        available_fruits = self.fruit_manager.get_available_fruits(fruit_category)
        is_available = found_fruit in available_fruits
       
        embed.add_field(
           name="🎯 Availability",
           value="✅ Available" if is_available else "❌ Taken",
           inline=True
        )
       
        # Add estimated market value
        if fruit_category == "rare":
           estimated_value = random.randint(50_000_000, 200_000_000)
        else:
           estimated_value = random.randint(2_000_000, 8_000_000)
       
        embed.add_field(
           name="💰 Est. Market Value",
           value=format_berries(estimated_value),
           inline=True
        )
       
        # Add search tips
        embed.add_field(
           name="🔍 How to Obtain",
           value="• Search mysterious islands\n"
                 "• Purchase from market\n"
                 "• Win in special events",
           inline=False
        )
       
        await ctx.send(embed=embed)
   
    async def encyclopedia(self, ctx: commands.Context, page: int = 1):
       """Browse the devil fruit encyclopedia."""
       # Calculate pagination
       fruits_per_page = 5
       all_fruits = []
       
       # Collect all fruits with their data
       for category, fruits in DEVIL_FRUITS.items():
           for name, data in fruits.items():
               all_fruits.append((name, data, category))
       
       # Sort alphabetically
       all_fruits.sort(key=lambda x: x[0])
       
       total_pages = (len(all_fruits) + fruits_per_page - 1) // fruits_per_page
       page = max(1, min(page, total_pages))
       
       # Get fruits for current page
       start_idx = (page - 1) * fruits_per_page
       end_idx = start_idx + fruits_per_page
       page_fruits = all_fruits[start_idx:end_idx]
       
       # Create encyclopedia embed
       embed = discord.Embed(
           title="📚 Devil Fruit Encyclopedia",
           description=f"Comprehensive guide to devil fruits (Page {page}/{total_pages})",
           color=discord.Color.dark_purple()
       )
       
       for fruit_name, fruit_data, category in page_fruits:
           fruit_type = fruit_data.get("type", "Unknown")
           rarity = "💎" if category == "rare" else "🍎"
           
           # Create a short description
           description = fruit_data.get("description", "")
           if len(description) > 100:
               description = description[:97] + "..."
           
           embed.add_field(
               name=f"{rarity} {fruit_name}",
               value=f"**Type:** {fruit_type}\n{description}",
               inline=False
           )
       
       # Add navigation info
       embed.set_footer(
           text=f"Use '{ctx.prefix}fruit encyclopedia {page + 1}' for next page | "
                f"Total Fruits: {len(all_fruits)}"
       )
       
       await ctx.send(embed=embed)
   
    async def mastery(self, ctx: commands.Context, member: Optional[discord.Member] = None):
       """Check devil fruit mastery level."""
       if member is None:
           member = ctx.author
       
       player = await self.player_manager.get_or_create_player(member)
       
       if not player.devil_fruit:
           embed = discord.Embed(
               title="🍎 No Devil Fruit",
               description=f"{member.display_name} doesn't have a devil fruit!",
               color=discord.Color.red()
           )
           await ctx.send(embed=embed)
           return
       
       # Get mastery information
       fruit_name = player.devil_fruit
       mastery_level = getattr(player, 'fruit_mastery', {}).get(fruit_name, 0)
       
       # Calculate mastery details
       mastery_tier = "Beginner"
       if mastery_level >= 75:
           mastery_tier = "Master"
       elif mastery_level >= 50:
           mastery_tier = "Advanced"
       elif mastery_level >= 25:
           mastery_tier = "Intermediate"
       
       embed = discord.Embed(
           title=f"🍎 {member.display_name}'s Devil Fruit Mastery",
           color=discord.Color.blue()
       )
       
       embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
       
       embed.add_field(
           name="🍎 Devil Fruit",
           value=fruit_name,
           inline=True
       )
       
       embed.add_field(
           name="📊 Mastery Level",
           value=f"{mastery_level}%",
           inline=True
       )
       
       embed.add_field(
           name="🎯 Mastery Tier",
           value=mastery_tier,
           inline=True
       )
       
       # Show unlocked abilities based on mastery
       fruit_data = player.devil_fruit_data
       if fruit_data and "moves" in fruit_data:
           unlocked_moves = []
           for i, move in enumerate(fruit_data["moves"]):
               required_mastery = i * 20  # Each move requires 20% more mastery
               if mastery_level >= required_mastery:
                   unlocked_moves.append(f"✅ {move['name']}")
               else:
                   unlocked_moves.append(f"🔒 {move['name']} (Req: {required_mastery}%)")
           
           embed.add_field(
               name="⚔️ Abilities",
               value="\n".join(unlocked_moves[:5]),  # Show first 5
               inline=False
           )
       
       # Mastery progression
       battles_with_fruit = getattr(player, 'battles_with_fruit', 0)
       embed.add_field(
           name="📈 Progression",
           value=f"Battles with Fruit: {battles_with_fruit}\n"
                 f"Next Tier: {100 - mastery_level}% remaining",
           inline=True
       )
       
       # Mastery bonuses
       mastery_bonuses = []
       if mastery_level >= 25:
           mastery_bonuses.append("• +10% damage with fruit moves")
       if mastery_level >= 50:
           mastery_bonuses.append("• -20% MP cost for fruit abilities")
       if mastery_level >= 75:
           mastery_bonuses.append("• Unlocked awakening potential")
       
       if mastery_bonuses:
           embed.add_field(
               name="🎁 Mastery Bonuses",
               value="\n".join(mastery_bonuses),
               inline=False
           )
       
       await ctx.send(embed=embed)
   
    async def market_prices(self, ctx: commands.Context):
       """Show current devil fruit market prices."""
       embed = discord.Embed(
           title="🏪 Devil Fruit Market Prices",
           description="Current market prices for devil fruits",
           color=discord.Color.gold()
       )
       
       # Show price ranges for different categories
       embed.add_field(
           name="🍎 Common Fruits",
           value="Price Range: 2M - 8M berries\n"
                 "Availability: High\n"
                 "Daily Refresh: Yes",
           inline=True
       )
       
       embed.add_field(
           name="💎 Rare Fruits",
           value="Price Range: 50M - 200M berries\n"
                 "Availability: Limited\n"
                 "Daily Refresh: Yes",
           inline=True
       )
       
       # Show market factors
       embed.add_field(
           name="📊 Price Factors",
           value="• Fruit rarity\n"
                 "• Power level\n"
                 "• Market demand\n"
                 "• Random daily variation",
           inline=False
       )
       
       # Market tips
       embed.add_field(
           name="💡 Market Tips",
           value="• Prices change daily\n"
                 "• Rare fruits appear randomly\n"
                 "• Check back regularly for deals\n"
                 "• Save up for rare opportunities",
           inline=False
       )
       
       # Current market status (simulated)
       market_status = random.choice([
           ("🟢 Buyers Market", "Lower than average prices"),
           ("🔵 Stable Market", "Average market prices"),
           ("🟡 Sellers Market", "Higher than average prices"),
           ("🔴 Volatile Market", "Unpredictable price swings")
       ])
       
       embed.add_field(
           name="📈 Market Status",
           value=f"{market_status[0]}\n{market_status[1]}",
           inline=True
       )
       
       embed.set_footer(text="Prices are estimates and may vary in actual transactions")
       
       await ctx.send(embed=embed)
   
    async def gift(self, ctx: commands.Context, recipient: discord.Member, *, fruit_name: str):
       """Gift a devil fruit to another player (admin only)."""
       # Check if user has admin permissions
       if not ctx.author.guild_permissions.administrator:
           await ctx.send("❌ You need administrator permissions to gift devil fruits!")
           return
       
       # Find the fruit
       found_fruit = None
       fruit_data = None
       fruit_category = None
       
       for category, fruits in DEVIL_FRUITS.items():
           for name, data in fruits.items():
               if name.lower() == fruit_name.lower():
                   found_fruit = name
                   fruit_data = data
                   fruit_category = category
                   break
           if found_fruit:
               break
       
       if not found_fruit:
           await ctx.send(f"❌ Could not find devil fruit '{fruit_name}'!")
           return
       
       # Check if recipient already has a fruit
       recipient_player = await self.player_manager.get_or_create_player(recipient)
       if recipient_player.devil_fruit:
           await ctx.send(f"❌ {recipient.display_name} already has a devil fruit ({recipient_player.devil_fruit})!")
           return
       
       # Give the fruit
       success = await self.fruit_manager.give_fruit(recipient_player, found_fruit)
       
       if success:
           embed = discord.Embed(
               title="🎁 Devil Fruit Gifted!",
               description=f"**{found_fruit}** has been gifted to {recipient.display_name}!",
               color=discord.Color.green()
           )
           
           embed.add_field(name="Fruit", value=found_fruit, inline=True)
           embed.add_field(name="Type", value=fruit_data.get("type", "Unknown"), inline=True)
           embed.add_field(name="Recipient", value=recipient.mention, inline=True)
           embed.add_field(name="Gifted By", value=ctx.author.mention, inline=True)
           
           await ctx.send(embed=embed)
       else:
           await ctx.send("❌ Failed to gift devil fruit!")
   
    async def remove(self, ctx: commands.Context, member: discord.Member):
       """Remove a player's devil fruit (admin only)."""
       # Check if user has admin permissions
       if not ctx.author.guild_permissions.administrator:
           await ctx.send("❌ You need administrator permissions to remove devil fruits!")
           return
       
       player = await self.player_manager.get_or_create_player(member)
       
       if not player.devil_fruit:
           await ctx.send(f"❌ {member.display_name} doesn't have a devil fruit to remove!")
           return
       
       # Store fruit name for the message
       removed_fruit = player.devil_fruit
       
       # Remove the fruit
       success = await self.fruit_manager.remove_fruit(player)
       
       if success:
           embed = discord.Embed(
               title="🗑️ Devil Fruit Removed",
               description=f"**{removed_fruit}** has been removed from {member.display_name}!",
               color=discord.Color.orange()
           )
           
           embed.add_field(name="Removed Fruit", value=removed_fruit, inline=True)
           embed.add_field(name="From Player", value=member.mention, inline=True)
           embed.add_field(name="Removed By", value=ctx.author.mention, inline=True)
           
           await ctx.send(embed=embed)
       else:
           await ctx.send("❌ Failed to remove devil fruit!")