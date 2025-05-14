import asyncio
import logging
import discord
from typing import Dict, Optional, List, Union
from datetime import datetime, timedelta

from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import menu

log = logging.getLogger("red.consecutivefilter")

class ConsecutiveFilter(commands.Cog):
    """
    Filter consecutive messages from the same user in specific channels.
    
    This cog helps maintain orderly advertising channels by preventing users
    from posting multiple messages in a row.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=56456546546, force_registration=True)
        
        default_guild = {
            "enabled": False,
            "filtered_channels": [],
            "notification_channel": None,
            "mod_bypass": True,
            "bot_bypass": True,
            "cooldown_minutes": 0,  # 0 means must have another user post in between
            "message_count": 2,  # How many consecutive messages before action is taken
            "delete_message": "Your message was removed because you're not allowed to post consecutive messages in this channel.",
            "delete_notification": "{member} attempted to post multiple consecutive messages in {channel}."
        }
        
        self.config.register_guild(**default_guild)
        # Maintain a simple cache of last message authors per channel
        self.last_message_cache: Dict[int, Dict[int, List[Dict]]] = {}
        
    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        pass
        
    async def initialize(self):
        """Initialize the cog by loading data and setting up channels"""
        log.info("ConsecutiveFilter is initializing...")
        # We need to load the cache from all configured guilds
        for guild in self.bot.guilds:
            self.last_message_cache[guild.id] = {}
            try:
                guild_data = await self.config.guild(guild).all()
                for channel_id in guild_data.get("filtered_channels", []):
                    # Initialize empty list for each filtered channel
                    self.last_message_cache[guild.id][channel_id] = []
                    
                    # Seed the cache with some recent messages
                    channel = guild.get_channel(channel_id)
                    if channel:
                        try:
                            # Get the most recent messages in the channel to initiate our cache
                            async for message in channel.history(limit=20):
                                if not message.author.bot or not guild_data.get("bot_bypass", True):
                                    self.last_message_cache[guild.id][channel_id].append({
                                        "author_id": message.author.id,
                                        "timestamp": message.created_at,
                                        "message_id": message.id,
                                        "content": message.content[:100]  # Store a preview of content for debugging
                                    })
                        except (discord.Forbidden, discord.HTTPException) as e:
                            log.warning(f"Could not retrieve message history for channel {channel_id} in guild {guild.id}: {e}")
            except Exception as e:
                log.error(f"Error initializing ConsecutiveFilter for guild {guild.id}: {e}", exc_info=True)
        
        log.info("ConsecutiveFilter initialized successfully.")

    def cog_unload(self):
        """Clean up on cog unload"""
        log.info("ConsecutiveFilter is being unloaded...")
        # Nothing to clean up here, but good practice to include this method
        
    @commands.group(name="consecutivefilter", aliases=["cf"])
    @checks.admin_or_permissions(manage_guild=True)
    async def consecutivefilter(self, ctx: commands.Context):
        """Manage settings for the consecutive message filter."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            
    @consecutivefilter.command(name="toggle")
    async def toggle_filter(self, ctx: commands.Context, state: bool = None):
        """
        Toggle the consecutive message filter on or off.
        
        If state is not provided, the current state will be toggled.
        """
        current = await self.config.guild(ctx.guild).enabled()
        if state is None:
            state = not current
            
        await self.config.guild(ctx.guild).enabled.set(state)
        
        if state:
            await ctx.send("Consecutive message filtering is now **enabled**.")
        else:
            await ctx.send("Consecutive message filtering is now **disabled**.")
    
    @consecutivefilter.command(name="addchannel")
    async def add_channel(self, ctx: commands.Context, *channels: discord.TextChannel):
        """
        Add one or more channels to the filtered channels list.
        
        Messages in these channels will be monitored for consecutive posting.
        """
        if not channels:
            return await ctx.send("Please provide at least one channel to add to the filter.")
            
        async with self.config.guild(ctx.guild).filtered_channels() as filtered_channels:
            added = []
            already_added = []
            
            for channel in channels:
                if channel.id in filtered_channels:
                    already_added.append(channel.mention)
                else:
                    filtered_channels.append(channel.id)
                    added.append(channel.mention)
                    
                    # Initialize the cache for this channel
                    if ctx.guild.id not in self.last_message_cache:
                        self.last_message_cache[ctx.guild.id] = {}
                    self.last_message_cache[ctx.guild.id][channel.id] = []
            
            message = ""
            if added:
                message += f"The following channels have been added to the filter: {', '.join(added)}\n"
            if already_added:
                message += f"The following channels were already filtered: {', '.join(already_added)}"
                
            if message:
                await ctx.send(message)
            else:
                await ctx.send("No channels were added to the filter.")
    
    @consecutivefilter.command(name="removechannel")
    async def remove_channel(self, ctx: commands.Context, *channels: discord.TextChannel):
        """
        Remove one or more channels from the filtered channels list.
        
        Messages in these channels will no longer be monitored.
        """
        if not channels:
            return await ctx.send("Please provide at least one channel to remove from the filter.")
            
        async with self.config.guild(ctx.guild).filtered_channels() as filtered_channels:
            removed = []
            not_filtered = []
            
            for channel in channels:
                if channel.id in filtered_channels:
                    filtered_channels.remove(channel.id)
                    removed.append(channel.mention)
                    
                    # Remove from cache
                    if ctx.guild.id in self.last_message_cache and channel.id in self.last_message_cache[ctx.guild.id]:
                        del self.last_message_cache[ctx.guild.id][channel.id]
                else:
                    not_filtered.append(channel.mention)
            
            message = ""
            if removed:
                message += f"The following channels have been removed from the filter: {', '.join(removed)}\n"
            if not_filtered:
                message += f"The following channels were not being filtered: {', '.join(not_filtered)}"
                
            if message:
                await ctx.send(message)
            else:
                await ctx.send("No channels were removed from the filter.")
    
    @consecutivefilter.command(name="notificationchannel", aliases=["notification", "alerts"])
    async def set_notification_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Set a channel where notifications will be sent when messages are filtered.
        
        If no channel is provided, notifications will be disabled.
        """
        if channel:
            await self.config.guild(ctx.guild).notification_channel.set(channel.id)
            await ctx.send(f"Notifications will now be sent to {channel.mention}.")
        else:
            await self.config.guild(ctx.guild).notification_channel.set(None)
            await ctx.send("Notification channel has been disabled.")
    
    @consecutivefilter.command(name="cooldown")
    async def set_cooldown(self, ctx: commands.Context, minutes: int):
        """
        Set the cooldown time between messages from the same user.
        
        Set to 0 to require another user to post in between (default).
        Otherwise, specify the number of minutes a user must wait before posting again.
        """
        if minutes < 0:
            return await ctx.send("Cooldown must be 0 or a positive number of minutes.")
            
        await self.config.guild(ctx.guild).cooldown_minutes.set(minutes)
        
        if minutes == 0:
            await ctx.send("Cooldown set to 0. Users will need to wait for another user to post before posting again.")
        else:
            await ctx.send(f"Cooldown set to {minutes} minute{'s' if minutes != 1 else ''}. Users will need to wait this long before posting again.")
    
    @consecutivefilter.command(name="messagecount")
    async def set_message_count(self, ctx: commands.Context, count: int):
        """
        Set how many consecutive messages from the same user will trigger the filter.
        
        Default is 2 (the second consecutive message will be removed).
        """
        if count < 2:
            return await ctx.send("Message count must be at least 2.")
            
        await self.config.guild(ctx.guild).message_count.set(count)
        await ctx.send(f"Message count set to {count}. The filter will trigger on the {count}th consecutive message.")
    
    @consecutivefilter.command(name="modbypass")
    async def toggle_mod_bypass(self, ctx: commands.Context, state: bool = None):
        """
        Toggle whether moderators can bypass the filter.
        
        Default is True (moderators can post consecutive messages).
        """
        current = await self.config.guild(ctx.guild).mod_bypass()
        if state is None:
            state = not current
            
        await self.config.guild(ctx.guild).mod_bypass.set(state)
        
        if state:
            await ctx.send("Moderators can now bypass the consecutive message filter.")
        else:
            await ctx.send("Moderators can no longer bypass the consecutive message filter.")
    
    @consecutivefilter.command(name="botbypass")
    async def toggle_bot_bypass(self, ctx: commands.Context, state: bool = None):
        """
        Toggle whether bots can bypass the filter.
        
        Default is True (bots can post consecutive messages).
        """
        current = await self.config.guild(ctx.guild).bot_bypass()
        if state is None:
            state = not current
            
        await self.config.guild(ctx.guild).bot_bypass.set(state)
        
        if state:
            await ctx.send("Bots can now bypass the consecutive message filter.")
        else:
            await ctx.send("Bots can no longer bypass the consecutive message filter.")
    
    @consecutivefilter.command(name="deletemessage")
    async def set_delete_message(self, ctx: commands.Context, *, message: str = None):
        """
        Set the message sent to users when their message is deleted.
        
        Leave blank to show the current message.
        Set to 'default' to reset to the default message.
        """
        if message is None:
            current = await self.config.guild(ctx.guild).delete_message()
            await ctx.send(f"Current delete message:\n{box(current)}")
            return
            
        if message.lower() == "default":
            default = self.config.defaults["GUILD"]["delete_message"]
            await self.config.guild(ctx.guild).delete_message.set(default)
            await ctx.send(f"Delete message reset to default:\n{box(default)}")
            return
            
        await self.config.guild(ctx.guild).delete_message.set(message)
        await ctx.send(f"Delete message updated to:\n{box(message)}")
    
    @consecutivefilter.command(name="notificationmessage", aliases=["notifymessage"])
    async def set_notification_message(self, ctx: commands.Context, *, message: str = None):
        """
        Set the notification message sent to the notification channel.
        
        Available placeholders: {member}, {channel}, {guild}, {message}
        
        Leave blank to show the current message.
        Set to 'default' to reset to the default message.
        """
        if message is None:
            current = await self.config.guild(ctx.guild).delete_notification()
            await ctx.send(f"Current notification message:\n{box(current)}")
            return
            
        if message.lower() == "default":
            default = self.config.defaults["GUILD"]["delete_notification"]
            await self.config.guild(ctx.guild).delete_notification.set(default)
            await ctx.send(f"Notification message reset to default:\n{box(default)}")
            return
            
        await self.config.guild(ctx.guild).delete_notification.set(message)
        await ctx.send(f"Notification message updated to:\n{box(message)}")
    
    @consecutivefilter.command(name="settings")
    async def show_settings(self, ctx: commands.Context):
        """Display the current settings for the consecutive message filter."""
        settings = await self.config.guild(ctx.guild).all()
        
        # Get channel mentions instead of IDs
        filtered_channels = []
        for channel_id in settings["filtered_channels"]:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                filtered_channels.append(channel.mention)
            else:
                filtered_channels.append(f"<#{channel_id}> (not found)")
                
        if settings["notification_channel"]:
            channel = ctx.guild.get_channel(settings["notification_channel"])
            notification_channel = channel.mention if channel else f"<#{settings['notification_channel']}> (not found)"
        else:
            notification_channel = "None"
            
        cooldown = f"{settings['cooldown_minutes']} minute{'s' if settings['cooldown_minutes'] != 1 else ''}" if settings["cooldown_minutes"] > 0 else "Another user must post in between"
            
        embed = discord.Embed(
            title="Consecutive Message Filter Settings",
            color=await ctx.embed_colour(),
            description=f"**Enabled:** {settings['enabled']}"
        )
        
        embed.add_field(name="Filtered Channels", value=", ".join(filtered_channels) if filtered_channels else "None", inline=False)
        embed.add_field(name="Notification Channel", value=notification_channel, inline=True)
        embed.add_field(name="Message Count", value=settings["message_count"], inline=True)
        embed.add_field(name="Cooldown", value=cooldown, inline=True)
        embed.add_field(name="Mod Bypass", value=settings["mod_bypass"], inline=True)
        embed.add_field(name="Bot Bypass", value=settings["bot_bypass"], inline=True)
        
        embed.add_field(name="Delete Message", value=settings["delete_message"], inline=False)
        embed.add_field(name="Notification Message", value=settings["delete_notification"], inline=False)
        
        await ctx.send(embed=embed)
    
    @consecutivefilter.command(name="debug")
    @checks.is_owner()
    async def debug_cache(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Debug command to show the current message cache for a channel.
        
        This is an owner-only command to help diagnose issues with the filter.
        """
        channel = channel or ctx.channel
        
        if ctx.guild.id not in self.last_message_cache or channel.id not in self.last_message_cache[ctx.guild.id]:
            return await ctx.send("No cache found for this channel.")
            
        cache = self.last_message_cache[ctx.guild.id][channel.id]
        if not cache:
            return await ctx.send("Cache is empty for this channel.")
            
        # Format cache entries
        formatted = []
        for i, entry in enumerate(cache):
            user = ctx.guild.get_member(entry["author_id"])
            username = user.display_name if user else f"User ID: {entry['author_id']}"
            time_str = discord.utils.format_dt(entry["timestamp"], style='R')
            content = entry.get("content", "<No content stored>")
            formatted.append(f"{i+1}. {username} ({time_str}): {content}")
            
        # Send as pages
        pages = []
        for page in pagify("\n".join(formatted), delims=["\n"], page_length=1900):
            pages.append(box(page))
            
        if len(pages) == 1:
            await ctx.send(pages[0])
        else:
            await menu(ctx, pages, {"⏪": menu.prev_page, "⏩": menu.next_page})
    
    @consecutivefilter.command(name="clearcache")
    @checks.is_owner()
    async def clear_cache(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Clear the message cache for a channel.
        
        This is an owner-only command to help reset the filter if it's not working correctly.
        """
        channel = channel or ctx.channel
        
        if ctx.guild.id in self.last_message_cache and channel.id in self.last_message_cache[ctx.guild.id]:
            self.last_message_cache[ctx.guild.id][channel.id] = []
            await ctx.send(f"Cache cleared for {channel.mention}.")
        else:
            await ctx.send("No cache exists for this channel.")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Clean up the cache when a message is deleted."""
        if not message.guild:
            return
            
        if message.guild.id in self.last_message_cache and message.channel.id in self.last_message_cache[message.guild.id]:
            # Remove the message from our cache
            cache = self.last_message_cache[message.guild.id][message.channel.id]
            self.last_message_cache[message.guild.id][message.channel.id] = [
                msg for msg in cache if msg["message_id"] != message.id
            ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Check each message to see if it violates the consecutive message filter."""
        # Skip private messages
        if not message.guild:
            return
            
        # Check if cog is disabled in the guild
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
            
        # Skip if filter is not enabled in this guild
        guild_settings = await self.config.guild(message.guild).all()
        if not guild_settings["enabled"]:
            return
            
        # Check if this is a filtered channel
        if message.channel.id not in guild_settings["filtered_channels"]:
            return
            
        # Skip if this is a command
        try:
            context = await self.bot.get_context(message)
            if context.valid or await self.bot.is_command(message):
                return
        except Exception:
            # If there's any error checking for commands, err on the side of caution
            log.warning("Error checking if message is a command, continuing with filter check", exc_info=True)
            
        # Skip if bot bypass is enabled and this is a bot
        if guild_settings["bot_bypass"] and message.author.bot:
            return
            
        # Skip if mod bypass is enabled and author is a mod
        if guild_settings["mod_bypass"]:
            try:
                if await self.bot.is_mod(message.author):
                    return
            except Exception:
                log.warning(f"Error checking mod status for {message.author}", exc_info=True)
            
        # Initialize cache if needed
        if message.guild.id not in self.last_message_cache:
            self.last_message_cache[message.guild.id] = {}
        if message.channel.id not in self.last_message_cache[message.guild.id]:
            self.last_message_cache[message.guild.id][message.channel.id] = []
        
        # IMPORTANT: We must check BEFORE we add this message to the cache
        # since we're determining if THIS message should be filtered

        # Check if we should filter this message
        should_filter = False
        consecutive_count = 0
        
        if guild_settings["cooldown_minutes"] > 0:
            # Time-based cooldown
            consecutive_msgs = []
            for msg in reversed(self.last_message_cache[message.guild.id][message.channel.id]):
                if msg["author_id"] == message.author.id:
                    consecutive_msgs.append(msg)
                else:
                    break
                    
            if consecutive_msgs:
                last_message_time = consecutive_msgs[0]["timestamp"]
                cooldown_delta = timedelta(minutes=guild_settings["cooldown_minutes"])
                if (message.created_at - last_message_time) < cooldown_delta:
                    consecutive_count = len(consecutive_msgs) + 1  # +1 for current message
        else:
            # Message-based cooldown (another user must post in between)
            # Count consecutive messages from the same author
            for msg in reversed(self.last_message_cache[message.guild.id][message.channel.id]):
                if msg["author_id"] == message.author.id:
                    consecutive_count += 1
                else:
                    break
                    
            # Include the current message in the count
            consecutive_count += 1
            
        # Debug log
        log.debug(f"Message from {message.author} in {message.channel.name}: consecutive count = {consecutive_count}, threshold = {guild_settings['message_count']}")
            
        # Determine if we should filter based on the message count threshold
        if consecutive_count >= guild_settings["message_count"]:
            should_filter = True
        
        # Add this message to the cache regardless if we'll filter it or not
        # (This ensures we still count filtered messages)
        self.last_message_cache[message.guild.id][message.channel.id].append({
            "author_id": message.author.id,
            "timestamp": message.created_at,
            "message_id": message.id,
            "content": message.content[:100]  # Store a preview of content for debugging
        })
        
        # Trim cache to last 50 messages
        if len(self.last_message_cache[message.guild.id][message.channel.id]) > 50:
            self.last_message_cache[message.guild.id][message.channel.id] = self.last_message_cache[message.guild.id][message.channel.id][-50:]
        
        # If filtering is needed, delete the message and notify
        if should_filter:
            try:
                # Delete the message
                await message.delete()
                log.info(f"Deleted consecutive message from {message.author} (ID: {message.author.id}) in {message.guild.name}, channel {message.channel.name}")
                
                # Notify the user
                try:
                    dm_message = guild_settings["delete_message"]
                    await message.author.send(dm_message)
                except (discord.Forbidden, discord.HTTPException) as e:
                    # Unable to DM the user, try to send in channel
                    log.warning(f"Could not DM {message.author} about their deleted message: {e}")
                    try:
                        temp_msg = await message.channel.send(
                            f"{message.author.mention} {guild_settings['delete_message']}",
                            delete_after=10
                        )
                    except (discord.Forbidden, discord.HTTPException) as e:
                        log.warning(f"Could not notify {message.author} in channel about their deleted message: {e}")
                
                # Send notification to mod channel if configured
                if guild_settings["notification_channel"]:
                    notification_channel = message.guild.get_channel(guild_settings["notification_channel"])
                    if notification_channel:
                        try:
                            # Format content safely
                            content = message.content if message.content else "<No text content>"
                            if len(content) > 1000:
                                content = f"{content[:997]}..."
                            
                            notification_message = guild_settings["delete_notification"]
                            formatted_message = notification_message.format(
                                member=message.author.mention,
                                channel=message.channel.mention,
                                guild=message.guild.name,
                                message=content
                            )
                            await notification_channel.send(formatted_message)
                        except Exception as e:
                            log.error(f"Failed to send notification for filtered message: {e}", exc_info=True)
            except discord.NotFound:
                log.warning(f"Tried to delete message from {message.author.id} but it was already gone")
            except (discord.Forbidden, discord.HTTPException) as e:
                log.error(f"Failed to delete consecutive message: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize the cache for a new guild."""
        self.last_message_cache[guild.id] = {}
        
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Clean up when the bot leaves a guild."""
        if guild.id in self.last_message_cache:
            del self.last_message_cache[guild.id]
