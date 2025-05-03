import discord
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from redbot.core import commands

class AdminCommands:
    """Admin commands for the BountyBattle cog."""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.config = cog.config
        self.logger = cog.logger
        self.data_manager = cog.data_manager
    
    @commands.group(name="bbadmin")
    @commands.admin_or_permissions(administrator=True)
    async def bb_admin(self, ctx):
        """Admin controls for BountyBattle (Admin only)"""
        if ctx.invoked_subcommand is None:
            # Show current status
            settings = await self.config.guild(ctx.guild).all()
            
            embed = discord.Embed(
                title="🛠️ BountyBattle Admin Panel",
                color=discord.Color.blue()
            )
            
            # Get status information
            is_paused = settings.get("is_paused", False)
            restricted_channel = settings.get("restricted_channel")
            disabled_commands = settings.get("disabled_commands", [])
            maintenance_mode = settings.get("maintenance_mode", False)
            
            if restricted_channel:
                channel = ctx.guild.get_channel(restricted_channel)
                channel_name = channel.name if channel else "Unknown"
            else:
                channel_name = "None"
            
            embed.add_field(
                name="📊 Current Status",
                value=(
                    f"🔒 System Paused: `{'Yes' if is_paused else 'No'}`\n"
                    f"📍 Restricted Channel: `{channel_name}`\n"
                    f"🛠️ Maintenance Mode: `{'Yes' if maintenance_mode else 'No'}`\n"
                    f"❌ Disabled Commands: `{', '.join(disabled_commands) if disabled_commands else 'None'}`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Available Commands",
                value=(
                    "`pause` - Temporarily pause all commands\n"
                    "`unpause` - Resume all commands\n"
                    "`restrict` - Restrict commands to one channel\n"
                    "`unrestrict` - Remove channel restriction\n"
                    "`disable` - Disable specific commands\n"
                    "`enable` - Re-enable specific commands\n"
                    "`maintenance` - Toggle maintenance mode\n"
                    "`status` - Show current status"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)

    @bb_admin.command(name="pause")
    async def pause_system(self, ctx, duration: str = None):
        """Temporarily pause all BountyBattle commands.
        
        Duration format: 1h, 30m, etc. Leave blank for indefinite."""
        await self.config.guild(ctx.guild).is_paused.set(True)
        
        if duration:
            try:
                # Parse duration
                time_convert = {"h": 3600, "m": 60, "s": 1}
                time_str = duration[-1].lower()
                time_amount = int(duration[:-1])
                seconds = time_amount * time_convert[time_str]
                
                embed = discord.Embed(
                    title="⏸️ System Paused",
                    description=f"BountyBattle commands paused for {duration}",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                
                # Wait and then unpause
                await asyncio.sleep(seconds)
                await self.config.guild(ctx.guild).is_paused.set(False)
                
                embed = discord.Embed(
                    title="▶️ System Resumed",
                    description="BountyBattle commands have been automatically resumed",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                
            except (KeyError, ValueError):
                await ctx.send("❌ Invalid duration format! Use format like: 1h, 30m, 60s")
        else:
            embed = discord.Embed(
                title="⏸️ System Paused",
                description="BountyBattle commands paused indefinitely",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

    @bb_admin.command(name="unpause")
    async def unpause_system(self, ctx):
        """Resume all BountyBattle commands."""
        await self.config.guild(ctx.guild).is_paused.set(False)
        
        embed = discord.Embed(
            title="▶️ System Resumed",
            description="BountyBattle commands have been resumed",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @bb_admin.command(name="restrict")
    async def restrict_channel(self, ctx, channel: discord.TextChannel = None):
        """Restrict BountyBattle commands to a specific channel."""
        channel = channel or ctx.channel
        await self.config.guild(ctx.guild).restricted_channel.set(channel.id)
        
        embed = discord.Embed(
            title="📍 Channel Restricted",
            description=f"BountyBattle commands restricted to {channel.mention}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @bb_admin.command(name="unrestrict")
    async def unrestrict_channel(self, ctx):
        """Remove channel restriction for BountyBattle commands."""
        await self.config.guild(ctx.guild).restricted_channel.set(None)
        
        embed = discord.Embed(
            title="🔓 Channel Restriction Removed",
            description="BountyBattle commands can now be used in any channel",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @bb_admin.command(name="disable")
    async def disable_commands(self, ctx, *commands):
        """Disable specific BountyBattle commands."""
        if not commands:
            return await ctx.send("❌ Please specify which commands to disable!")
            
        disabled_commands = await self.config.guild(ctx.guild).disabled_commands()
        newly_disabled = []
        
        for cmd in commands:
            # Check if command exists in the cog
            cmd_exists = hasattr(self.cog, cmd) or any(
                hasattr(handler, cmd) for handler in [
                    self.cog.bounty_commands,
                    self.cog.battle_commands,
                    self.cog.economy_commands,
                    self.cog.fruit_commands,
                    self.cog.admin_commands
                ]
            )
            
            if cmd_exists and cmd not in disabled_commands:
                disabled_commands.append(cmd)
                newly_disabled.append(cmd)
        
        await self.config.guild(ctx.guild).disabled_commands.set(disabled_commands)
        
        if newly_disabled:
            embed = discord.Embed(
                title="❌ Commands Disabled",
                description=f"Disabled commands: `{', '.join(newly_disabled)}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No new commands were disabled.")

    @bb_admin.command(name="enable")
    async def enable_commands(self, ctx, *commands):
        """Re-enable specific BountyBattle commands."""
        if not commands:
            return await ctx.send("❌ Please specify which commands to enable!")
            
        disabled_commands = await self.config.guild(ctx.guild).disabled_commands()
        newly_enabled = []
        
        for cmd in commands:
            if cmd in disabled_commands:
                disabled_commands.remove(cmd)
                newly_enabled.append(cmd)
        
        await self.config.guild(ctx.guild).disabled_commands.set(disabled_commands)
        
        if newly_enabled:
            embed = discord.Embed(
                title="✅ Commands Enabled",
                description=f"Re-enabled commands: `{', '.join(newly_enabled)}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No commands were enabled.")

    @bb_admin.command(name="maintenance")
    async def toggle_maintenance(self, ctx, duration: str = None):
        """Toggle maintenance mode for BountyBattle.
        
        Duration format: 1h, 30m, etc. Leave blank for indefinite."""
        current_mode = await self.config.guild(ctx.guild).maintenance_mode()
        
        if current_mode:
            await self.config.guild(ctx.guild).maintenance_mode.set(False)
            embed = discord.Embed(
                title="✅ Maintenance Mode Ended",
                description="BountyBattle is now fully operational",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return
            
        await self.config.guild(ctx.guild).maintenance_mode.set(True)
        
        if duration:
            try:
                # Parse duration
                time_convert = {"h": 3600, "m": 60, "s": 1}
                time_str = duration[-1].lower()
                time_amount = int(duration[:-1])
                seconds = time_amount * time_convert[time_str]
                
                embed = discord.Embed(
                    title="🛠️ Maintenance Mode Active",
                    description=f"BountyBattle entering maintenance mode for {duration}",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                
                # Wait and then end maintenance
                await asyncio.sleep(seconds)
                await self.config.guild(ctx.guild).maintenance_mode.set(False)
                
                embed = discord.Embed(
                    title="✅ Maintenance Complete",
                    description="BountyBattle is now fully operational",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                
            except (KeyError, ValueError):
                await ctx.send("❌ Invalid duration format! Use format like: 1h, 30m, 60s")
        else:
            embed = discord.Embed(
                title="🛠️ Maintenance Mode Active",
                description="BountyBattle entering maintenance mode indefinitely",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
    
    @bb_admin.command(name="status")
    async def show_status(self, ctx):
        """Show current BountyBattle system status."""
        settings = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="📊 BountyBattle System Status",
            color=discord.Color.blue()
        )
        
        # Get status information
        is_paused = settings.get("is_paused", False)
        restricted_channel = settings.get("restricted_channel")
        disabled_commands = settings.get("disabled_commands", [])
        maintenance_mode = settings.get("maintenance_mode", False)
        
        if restricted_channel:
            channel = ctx.guild.get_channel(restricted_channel)
            channel_name = channel.mention if channel else "Unknown"
        else:
            channel_name = "None"
        
        embed.add_field(
            name="System State",
            value=(
                f"🔒 System Paused: `{'Yes' if is_paused else 'No'}`\n"
                f"📍 Restricted Channel: {channel_name}\n"
                f"🛠️ Maintenance Mode: `{'Yes' if maintenance_mode else 'No'}`"
            ),
            inline=False
        )
        
        if disabled_commands:
            embed.add_field(
                name="❌ Disabled Commands",
                value=f"`{', '.join(disabled_commands)}`",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def givefruit(self, ctx, member: discord.Member, *, fruit_name: str):
        """Give a user a Devil Fruit (Admin/Owner only)."""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
        
        # Validate the fruit name
        from ..constants.devil_fruits import DEVIL_FRUITS
        fruit_data = None
        
        for category in ["Common", "Rare"]:
            if fruit_name in DEVIL_FRUITS[category]:
                fruit_data = DEVIL_FRUITS[category][fruit_name]
                break
                
        if not fruit_data:
            return await ctx.send(f"❌ The fruit `{fruit_name}` does not exist!")
            
        # Check if another user already has this fruit (if it's rare)
        if fruit_name in DEVIL_FRUITS["Rare"]:
            bounties = self.data_manager.load_bounties()
            for user_id, data in bounties.items():
                if data.get("fruit") == fruit_name:
                    user = ctx.guild.get_member(int(user_id))
                    if user:
                        return await ctx.send(f"❌ The rare fruit `{fruit_name}` is already owned by {user.display_name}!")
        
        # Check if the member already has a fruit
        current_fruit = await self.data_manager.get_devil_fruit(member)
        if current_fruit:
            return await ctx.send(f"❌ {member.display_name} already has the `{current_fruit}`! Remove it first.")

        # Assign fruit
        success = await self.data_manager.set_devil_fruit(member, fruit_name)
        if not success:
            return await ctx.send("❌ Failed to give the Devil Fruit. Please try again.")
        
        # Update last active time
        await self.config.member(member).last_active.set(datetime.utcnow().isoformat())

        # Create success embed
        embed = discord.Embed(
            title="<:MeraMera:1336888578705330318> Devil Fruit Given!",
            description=f"**{member.display_name}** has been given the `{fruit_name}`!",
            color=discord.Color.green()
        )
        embed.add_field(name="Type", value=fruit_data["type"], inline=True)
        embed.add_field(name="Power", value=fruit_data["bonus"], inline=False)

        await ctx.send(embed=embed)
        
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def fruitcleanup(self, ctx, days: int = 30):
        """Clean up Devil Fruits from inactive players and users who left the server (Admin/Owner only)."""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
                
        try:
            current_time = datetime.utcnow()
            bounties = self.data_manager.load_bounties()
            cleaned_fruits = []
            left_server_fruits = []
            
            # Step 1: Process inactive users in the server
            for user_id, data in list(bounties.items()):
                # Skip if no fruit
                if not data.get("fruit"):
                    continue

                try:
                    # Check if user is still in server
                    member = ctx.guild.get_member(int(user_id))
                    if not member:
                        # User left server, clean up their fruit
                        fruit_name = data["fruit"]
                        bounties[user_id]["fruit"] = None
                        left_server_fruits.append((user_id, fruit_name))
                        continue
                        
                    # User is in server, check if inactive
                    last_active = await self.config.member(member).last_active()
                    if not last_active:
                        continue

                    last_active_date = datetime.fromisoformat(last_active)
                    days_since_active = (current_time - last_active_date).days

                    # Remove fruit if inactive for specified period
                    if days_since_active >= days:
                        fruit_name = data["fruit"]
                        bounties[user_id]["fruit"] = None
                        await self.config.member(member).devil_fruit.set(None)
                        cleaned_fruits.append((member.display_name, fruit_name))

                except (ValueError, AttributeError) as e:
                    self.logger.error(f"Error processing user {user_id}: {e}")
                    continue

            # Save changes
            self.data_manager.save_bounties(bounties)

            # Create report embed
            embed = discord.Embed(
                title="<:MeraMera:1336888578705330318> Devil Fruit Cleanup Report",
                description="Results of the cleanup operation:",
                color=discord.Color.blue()
            )
            
            # Add section for inactive users
            if cleaned_fruits:
                embed.add_field(
                    name=f"🕒 Removed from {len(cleaned_fruits)} inactive players",
                    value="\n".join([f"**{name}**: `{fruit}`" for name, fruit in cleaned_fruits[:10]]) + 
                        (f"\n*...and {len(cleaned_fruits) - 10} more*" if len(cleaned_fruits) > 10 else ""),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🕒 Inactive Players",
                    value="No inactive Devil Fruit users found!",
                    inline=False
                )
                
            # Add section for users who left the server
            if left_server_fruits:
                embed.add_field(
                    name=f"👋 Removed from {len(left_server_fruits)} users who left the server",
                    value="\n".join([f"**ID {user_id}**: `{fruit}`" for user_id, fruit in left_server_fruits[:10]]) +
                        (f"\n*...and {len(left_server_fruits) - 10} more*" if len(left_server_fruits) > 10 else ""),
                    inline=False
                )
            else:
                embed.add_field(
                    name="👋 Left Server Users",
                    value="No Devil Fruit users have left the server!",
                    inline=False
                )
                
            # Add summary
            total_cleaned = len(cleaned_fruits) + len(left_server_fruits)
            if total_cleaned > 0:
                embed.add_field(
                    name="📊 Summary",
                    value=f"**{total_cleaned}** Devil Fruits have been returned to circulation!",
                    inline=False
                )
                
                # Check for rare fruits that were reclaimed
                from ..constants.devil_fruits import DEVIL_FRUITS
                rare_fruits = [fruit for _, fruit in cleaned_fruits + left_server_fruits 
                            if fruit in DEVIL_FRUITS["Rare"]]
                if rare_fruits:
                    embed.add_field(
                        name="🌟 Rare Fruits Reclaimed",
                        value="\n".join([f"`{fruit}`" for fruit in rare_fruits]),
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
            # Send announcements for rare fruits
            for _, fruit in cleaned_fruits + left_server_fruits:
                if fruit in DEVIL_FRUITS["Rare"]:
                    announcement_embed = discord.Embed(
                        title="🌟 Rare Devil Fruit Available!",
                        description=(
                            f"The `{fruit}` has returned to circulation!\n"
                            f"Previous owner is no longer using it."
                        ),
                        color=discord.Color.gold()
                    )
                    
                    # Try to send to a designated channel if it exists
                    announcement_channel = discord.utils.get(ctx.guild.text_channels, name="fruit-announcements") or \
                                        discord.utils.get(ctx.guild.text_channels, name="announcements") or \
                                        discord.utils.get(ctx.guild.text_channels, name="general")
                    
                    if announcement_channel and announcement_channel != ctx.channel:
                        await announcement_channel.send(embed=announcement_embed)

        except Exception as e:
            self.logger.error(f"Error in cleanup_inactive_fruits: {e}")
            await ctx.send("❌ An error occurred during fruit cleanup.")
            
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def resetstats(self, ctx, member: discord.Member = None):
        """Reset all users' stats (Admin/Owner only)."""
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
    
        if member is None:  # Default to full server reset if no user is mentioned
            await ctx.send("⚠️ **Are you sure you want to reset ALL players' stats?** Type `confirm` to proceed.")
    
            def check(m):
                return m.author == ctx.author and m.content.lower() == "confirm"
    
            try:
                await self.bot.wait_for("message", check=check, timeout=15)
            except asyncio.TimeoutError:
                return await ctx.send("❌ **Global reset cancelled.**")
    
            all_members = await self.config.all_members(ctx.guild)
            for user_id in all_members:
                user = ctx.guild.get_member(int(user_id))  # Get the actual Discord member object
                if user:
                    await self.config.member(user).clear()
    
            # Reset the server-wide bounty list
            bounties = self.data_manager.load_bounties()
            for user_id in bounties:
                bounties[user_id] = {"amount": 0, "fruit": None}
            self.data_manager.save_bounties(bounties)
            
            await ctx.send("🔄 **All player stats, bounties, and titles have been reset!**")
            return
    
        # Reset a Single User
        await self.config.member(member).clear()
    
        # Reset the user's bounty inside the bounties file
        bounties = self.data_manager.load_bounties()
        if str(member.id) in bounties:
            bounties[str(member.id)]["amount"] = 0  # Set bounty to 0
            bounties[str(member.id)]["fruit"] = None  # Clear fruit
            self.data_manager.save_bounties(bounties)
    
        await ctx.send(f"🔄 **{member.display_name}'s stats, bounty, and titles have been reset!**")
        
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def granttitle(self, ctx, member: discord.Member, *, title: str):
        """Grant a title to a user (Admin/Owner only)."""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
        
        # Ensure the user has a bounty entry
        await self.data_manager.sync_user_data(member)
        
        # Get current titles
        current_titles = await self.config.member(member).titles()
        
        # Check if they already have this title
        if title in current_titles:
            return await ctx.send(f"⚠️ {member.display_name} already has the title `{title}`!")
        
        # Add the new title
        current_titles.append(title)
        await self.config.member(member).titles.set(current_titles)
        
        # Create response embed
        embed = discord.Embed(
            title="🏆 Title Granted",
            description=f"Granted the title `{title}` to **{member.display_name}**!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="All Titles",
            value="\n".join([f"• {t}" for t in current_titles]),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # DM the user
        try:
                user_embed = discord.Embed(
                    title="🎖️ New Title Awarded!",
                    description=f"You have been granted the title `{title}`!",
                    color=discord.Color.gold()
                )
                user_embed.add_field(
                    name="How to Equip",
                    value=f"Use `.equiptitle \"{title}\"` to equip your new title!",
                    inline=False
                )
                await member.send(embed=user_embed)
        except discord.Forbidden:
            # User might have DMs disabled
            pass

    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def betaover(self, ctx):
        """End the beta test (Admin/Owner only)."""
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")

        beta_active = await self.config.guild(ctx.guild).beta_active()
        
        if not beta_active:
            return await ctx.send("❌ Beta is already over!")
        
        await self.config.guild(ctx.guild).beta_active.set(False)
        await ctx.send("🚨 **The beta test is now officially over!**\nNo new players will receive the `BETA TESTER` title.")
