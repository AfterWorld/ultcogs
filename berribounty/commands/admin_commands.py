"""Admin commands for the One Piece bot."""

import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from typing import Union, Optional
from ..ui.admin_view import AdminControlPanelView
from ..validators import validate_berries_amount, validate_admin_give_amount
from ..formatters import format_berries

class AdminCommands:
    """Admin command handlers."""
    
    def __init__(self, bot: Red, config: Config, player_manager):
        self.bot = bot
        self.config = config
        self.player_manager = player_manager
    
    async def admin_panel(self, ctx: commands.Context):
        """Open the admin control panel."""
        view = AdminControlPanelView(self.bot, self.config, self.player_manager)
        embed = discord.Embed(
            title="🏴‍☠️ One Piece Admin Panel",
            description="Select an option to manage the bot:",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📊 Available Actions",
            value=(
                "• View server statistics\n"
                "• Manage players\n"
                "• Control economy\n"
                "• Configure settings"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed, view=view)
    
    async def set_channel(self, ctx: commands.Context, channel_type: str, 
                         channel: Optional[discord.TextChannel] = None):
        """Set bot channels for announcements."""
        valid_types = {
            "battle": "battle_channel",
            "announcement": "announcement_channel",
            "log": "log_channel"
        }
        
        if channel_type.lower() not in valid_types:
            await ctx.send(f"❌ Invalid channel type! Valid types: {', '.join(valid_types.keys())}")
            return
        
        config_key = valid_types[channel_type.lower()]
        
        if channel is None:
            # Clear the channel setting
            await self.config.guild(ctx.guild).set_raw(config_key, value=None)
            await ctx.send(f"✅ Cleared {channel_type} channel setting.")
        else:
            # Set the channel
            await self.config.guild(ctx.guild).set_raw(config_key, value=channel.id)
            await ctx.send(f"✅ Set {channel_type} channel to {channel.mention}")
    
    async def maintenance(self, ctx: commands.Context, enabled: Optional[bool] = None):
        """Toggle or set maintenance mode."""
        current = await self.config.guild(ctx.guild).maintenance_mode()
        
        if enabled is None:
            # Toggle current state
            new_state = not current
        else:
            new_state = enabled
        
        await self.config.guild(ctx.guild).maintenance_mode.set(new_state)
        
        status = "🔴 **ENABLED**" if new_state else "🟢 **DISABLED**"
        embed = discord.Embed(
            title="🔧 Maintenance Mode",
            description=f"Maintenance mode is now {status}",
            color=discord.Color.red() if new_state else discord.Color.green()
        )
        
        if new_state:
            embed.add_field(
                name="ℹ️ Effect",
                value="All non-admin commands are now disabled for regular users.",
                inline=False
            )
        else:
            embed.add_field(
                name="ℹ️ Effect", 
                value="All commands are now available to users.",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    async def give_item(self, ctx: commands.Context, member: discord.Member, 
                       item_type: str, amount: int):
        """Give items to a player (admin only)."""
        # Validate item type and amount
        is_valid, error = validate_admin_give_amount(item_type, amount)
        if not is_valid:
            await ctx.send(f"❌ {error}")
            return
        
        # Get or create player
        player = await self.player_manager.get_or_create_player(member)
        
        try:
            if item_type == "berries":
                # Give berries
                if amount > 0:
                    player.add_berries(amount)
                    action = "gave"
                    color = discord.Color.green()
                else:
                    player.remove_berries(abs(amount))
                    action = "removed"
                    color = discord.Color.red()
                
                embed = discord.Embed(
                    title="💰 Berries Modified",
                    description=f"Successfully {action} {format_berries(abs(amount))} {'to' if amount > 0 else 'from'} {member.display_name}",
                    color=color
                )
                embed.add_field(name="New Balance", value=format_berries(player.berries), inline=True)
            
            elif item_type == "wins":
                # Give wins
                player.wins += amount
                await self.player_manager.save_player(player)
                
                embed = discord.Embed(
                    title="🏆 Wins Added",
                    description=f"Added {amount} wins to {member.display_name}",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Total Wins", value=str(player.wins), inline=True)
            
            elif item_type == "losses":
                # Give losses
                player.losses += amount
                await self.player_manager.save_player(player)
                
                embed = discord.Embed(
                    title="💀 Losses Added",
                    description=f"Added {amount} losses to {member.display_name}",
                    color=discord.Color.red()
                )
                embed.add_field(name="Total Losses", value=str(player.losses), inline=True)
            
            # Add admin info
            embed.add_field(name="👤 Admin", value=ctx.author.mention, inline=True)
            embed.timestamp = ctx.message.created_at
            
            await ctx.send(embed=embed)
            
            # Log the action
            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            if log_channel_id:
                log_channel = ctx.guild.get_channel(log_channel_id)
                if log_channel:
                    log_embed = discord.Embed(
                        title="📝 Admin Action Log",
                        description=f"{ctx.author.mention} gave {amount} {item_type} to {member.mention}",
                        color=discord.Color.blue()
                    )
                    await log_channel.send(embed=log_embed)
        
        except Exception as e:
            await ctx.send(f"❌ Error giving {item_type}: {str(e)}")
    
    async def reset_player(self, ctx: commands.Context, member: discord.Member, 
                          confirm: bool = False):
        """Reset a player's data (admin only)."""
        if not confirm:
            embed = discord.Embed(
                title="⚠️ Confirm Player Reset",
                description=(
                    f"Are you sure you want to reset all data for {member.display_name}?\n\n"
                    "**This will delete:**\n"
                    "• All berries\n"
                    "• Battle record\n"
                    "• Devil fruit\n"
                    "• Achievements\n"
                    "• Statistics\n\n"
                    "**This action cannot be undone!**"
                ),
                color=discord.Color.red()
            )
            embed.add_field(
                name="To confirm, run:",
                value=f"`{ctx.prefix}opset reset {member.mention} yes`",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # Reset player data
        try:
            await self.player_manager.reset_player(member)
            
            embed = discord.Embed(
                title="✅ Player Reset Complete",
                description=f"All data for {member.display_name} has been reset.",
                color=discord.Color.green()
            )
            embed.add_field(name="👤 Admin", value=ctx.author.mention, inline=True)
            embed.timestamp = ctx.message.created_at
            
            await ctx.send(embed=embed)
            
            # Log the action
            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            if log_channel_id:
                log_channel = ctx.guild.get_channel(log_channel_id)
                if log_channel:
                    log_embed = discord.Embed(
                        title="📝 Admin Action Log",
                        description=f"{ctx.author.mention} reset all data for {member.mention}",
                        color=discord.Color.orange()
                    )
                    await log_channel.send(embed=log_embed)
        
        except Exception as e:
            await ctx.send(f"❌ Error resetting player: {str(e)}")
    
    async def server_stats(self, ctx: commands.Context):
        """Show detailed server statistics."""
        guild_data = await self.config.guild(ctx.guild).all()
        players = guild_data.get("players", {})
        
        if not players:
            await ctx.send("❌ No players found in this server!")
            return
        
        # Calculate statistics
        total_players = len(players)
        total_berries = sum(player.get("berries", 0) for player in players.values())
        total_bank_berries = sum(player.get("bank_berries", 0) for player in players.values())
        total_battles = sum(
            player.get("wins", 0) + player.get("losses", 0) 
            for player in players.values()
        )
        total_wins = sum(player.get("wins", 0) for player in players.values())
        total_losses = sum(player.get("losses", 0) for player in players.values())
        
        # Devil fruit statistics
        fruit_owners = sum(1 for player in players.values() if player.get("devil_fruit"))
        
        # Active players (fought at least one battle)
        active_players = sum(
            1 for player in players.values() 
            if player.get("wins", 0) > 0 or player.get("losses", 0) > 0
        )
        
        embed = discord.Embed(
            title=f"📊 {ctx.guild.name} Statistics",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="👥 Players",
            value=(
                f"Total: {total_players:,}\n"
                f"Active: {active_players:,}\n"
                f"Activity Rate: {active_players/total_players*100:.1f}%"
            ),
            inline=True
        )
        
        embed.add_field(
            name="💰 Economy",
            value=(
                f"Circulation: {format_berries(total_berries)}\n"
                f"In Banks: {format_berries(total_bank_berries)}\n"
                f"Global Bank: {format_berries(guild_data.get('global_bank', 0))}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⚔️ Battles",
            value=(
                f"Total: {total_battles:,}\n"
                f"Wins: {total_wins:,}\n"
                f"Losses: {total_losses:,}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🍎 Devil Fruits",
            value=(
                f"Owners: {fruit_owners}\n"
                f"Ownership Rate: {fruit_owners/total_players*100:.1f}%"
            ),
            inline=True
        )
        embed.add_field(
            name="⚙️ Settings",
            value=(
                f"Maintenance: {'🔴 On' if guild_data.get('maintenance_mode') else '🟢 Off'}\n"
                f"Battle Channel: {'Set' if guild_data.get('battle_channel') else 'Not Set'}\n"
                f"Announcement Channel: {'Set' if guild_data.get('announcement_channel') else 'Not Set'}"
            ),
            inline=True
        )

        # Add timestamp
        embed.timestamp = ctx.message.created_at
        embed.set_footer(text="Statistics generated")

        await ctx.send(embed=embed)

async def backup_data(self, ctx: commands.Context):
       """Create a backup of server data."""
       try:
           # Get all guild data
           guild_data = await self.config.guild(ctx.guild).all()
           
           # Create backup info
           backup_info = {
               "guild_id": ctx.guild.id,
               "guild_name": ctx.guild.name,
               "backup_date": ctx.message.created_at.isoformat(),
               "player_count": len(guild_data.get("players", {})),
               "total_berries": sum(
                   player.get("berries", 0) for player in guild_data.get("players", {}).values()
               )
           }
           
           embed = discord.Embed(
               title="💾 Data Backup Created",
               description="Server data has been backed up successfully.",
               color=discord.Color.green()
           )
           
           embed.add_field(name="Players Backed Up", value=str(backup_info["player_count"]), inline=True)
           embed.add_field(name="Total Berries", value=format_berries(backup_info["total_berries"]), inline=True)
           embed.add_field(name="Backup Date", value=backup_info["backup_date"][:10], inline=True)
           
           embed.add_field(
               name="ℹ️ Note",
               value="Data backup is stored automatically. Contact bot owner for restoration if needed.",
               inline=False
           )
           
           await ctx.send(embed=embed)
           
       except Exception as e:
           await ctx.send(f"❌ Error creating backup: {str(e)}")
   
async def purge_inactive(self, ctx: commands.Context, days: int = 30, confirm: bool = False):
       """Purge inactive players' data."""
       if not confirm:
           embed = discord.Embed(
               title="⚠️ Confirm Inactive Player Purge",
               description=(
                   f"This will remove all players who have been inactive for more than {days} days.\n\n"
                   "**Players to be purged:**\n"
                   "• No activity in the last {days} days\n"
                   "• Less than 1000 berries\n"
                   "• No devil fruit\n"
                   "• Less than 5 total battles\n\n"
                   "**This action cannot be undone!**"
               ),
               color=discord.Color.red()
           )
           embed.add_field(
               name="To confirm, run:",
               value=f"`{ctx.prefix}opset purge {days} yes`",
               inline=False
           )
           await ctx.send(embed=embed)
           return
       
       try:
           # Get guild data
           guild_data = await self.config.guild(ctx.guild).all()
           players = guild_data.get("players", {})
           
           # Find inactive players
           import time
           current_time = time.time()
           cutoff_time = current_time - (days * 24 * 60 * 60)
           
           inactive_players = []
           for user_id, player_data in players.items():
               last_active = player_data.get("last_active", 0)
               berries = player_data.get("berries", 0)
               devil_fruit = player_data.get("devil_fruit")
               total_battles = player_data.get("wins", 0) + player_data.get("losses", 0)
               
               # Check if player meets purge criteria
               if (last_active < cutoff_time and 
                   berries < 1000 and 
                   not devil_fruit and 
                   total_battles < 5):
                   inactive_players.append(user_id)
           
           # Remove inactive players
           if inactive_players:
               async with self.config.guild(ctx.guild).players() as players_data:
                   for user_id in inactive_players:
                       del players_data[user_id]
               
               embed = discord.Embed(
                   title="🗑️ Inactive Players Purged",
                   description=f"Removed {len(inactive_players)} inactive players.",
                   color=discord.Color.orange()
               )
               embed.add_field(name="Days Inactive", value=str(days), inline=True)
               embed.add_field(name="Players Removed", value=str(len(inactive_players)), inline=True)
           else:
               embed = discord.Embed(
                   title="✅ No Players to Purge",
                   description="No players met the purge criteria.",
                   color=discord.Color.green()
               )
           
           await ctx.send(embed=embed)
           
       except Exception as e:
           await ctx.send(f"❌ Error purging inactive players: {str(e)}")
   
async def event_create(self, ctx: commands.Context, event_type: str, *, details: str):
       """Create a server event."""
       valid_events = ["battle_tournament", "berri_rain", "devil_fruit_hunt", "double_rewards"]
       
       if event_type not in valid_events:
           await ctx.send(f"❌ Invalid event type! Valid types: {', '.join(valid_events)}")
           return
       
       # Create event data
       event_data = {
           "type": event_type,
           "details": details,
           "created_by": ctx.author.id,
           "created_at": ctx.message.created_at.isoformat(),
           "active": True
       }
       
       # Save event
       async with self.config.guild(ctx.guild).event_data() as events:
           events[event_type] = event_data
       
       embed = discord.Embed(
           title="🎉 Event Created!",
           description=f"**{event_type.replace('_', ' ').title()}** has been activated!",
           color=discord.Color.purple()
       )
       
       embed.add_field(name="Details", value=details, inline=False)
       embed.add_field(name="Created By", value=ctx.author.mention, inline=True)
       embed.add_field(name="Status", value="🟢 Active", inline=True)
       
       await ctx.send(embed=embed)
       
       # Announce event if announcement channel is set
       announcement_channel_id = await self.config.guild(ctx.guild).announcement_channel()
       if announcement_channel_id:
           announcement_channel = ctx.guild.get_channel(announcement_channel_id)
           if announcement_channel:
               announcement_embed = discord.Embed(
                   title="🎊 New Event Announced!",
                   description=f"**{event_type.replace('_', ' ').title()}** is now active!",
                   color=discord.Color.gold()
               )
               announcement_embed.add_field(name="Details", value=details, inline=False)
               await announcement_channel.send(embed=announcement_embed)
   
async def event_end(self, ctx: commands.Context, event_type: str):
       """End a server event."""
       guild_data = await self.config.guild(ctx.guild).all()
       events = guild_data.get("event_data", {})
       
       if event_type not in events:
           await ctx.send(f"❌ No active event of type '{event_type}' found!")
           return
       
       # End the event
       async with self.config.guild(ctx.guild).event_data() as event_data:
           event_data[event_type]["active"] = False
           event_data[event_type]["ended_at"] = ctx.message.created_at.isoformat()
           event_data[event_type]["ended_by"] = ctx.author.id
       
       embed = discord.Embed(
           title="🏁 Event Ended",
           description=f"**{event_type.replace('_', ' ').title()}** has been deactivated.",
           color=discord.Color.red()
       )
       
       embed.add_field(name="Ended By", value=ctx.author.mention, inline=True)
       embed.add_field(name="Status", value="🔴 Inactive", inline=True)
       
       await ctx.send(embed=embed)