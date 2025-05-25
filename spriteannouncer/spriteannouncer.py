import asyncio
import random
import aiohttp
import discord
import logging
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

log = logging.getLogger("red.ultcogs.spriteannouncer")

# GitHub API endpoints
GITHUB_REPO_OWNER = "AfterWorld"
GITHUB_REPO_NAME = "ultcogs"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/Character%20Sprite"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/Character%20Sprite/"

class SpriteAnnouncer(commands.Cog):
    """
    A topic/announcement cog that uses character sprites to create interactive discussions.
    
    This cog randomly selects character sprites and creates topic prompts or announcements
    for users to interact with.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=5626721548, force_registration=True
        )
        
        default_guild = {
            "enabled": False,
            "channel_id": None,
            "frequency": {
                "min_minutes": 60,
                "max_minutes": 240
            },
            "sprites_enabled": [],
            "topics": [],
            "announcements": [],
            "last_triggered": None,
            "next_trigger": None,
            "custom_sprites": {}
        }
        
        self.config.register_guild(**default_guild)
        self.sprite_cache = {}  # Cache for sprite URLs
        self.github_sprites_cache = []  # Cache for available sprites from GitHub
        self.github_sprites_last_updated = 0  # Timestamp of last GitHub API request
        self.task_cache = {}  # Track announcement tasks
        self.session = None  # Will be initialized in the background task
        self._initialization_task = None
        # These are fallback sprites in case GitHub fetch fails
        self.default_sprites = [
            "cat_sprite.png", 
            "dog_sprite.png", 
            "ghost_sprite.png", 
            "robot_sprite.png", 
            "slime_sprite.png"
        ]
        
        # Start initialization in background
        self._initialization_task = self.bot.loop.create_task(self._initialize_when_ready())
    
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        # Cancel initialization task if still running
        if self._initialization_task and not self._initialization_task.done():
            self._initialization_task.cancel()
            
        # Cancel all announcement tasks
        for guild_id in self.task_cache:
            task = self.task_cache[guild_id]
            if task and not task.done():
                task.cancel()
                
        # Close aiohttp session if it exists
        if self.session and not self.session.closed:
            self.bot.loop.create_task(self.session.close())
    
    async def _initialize_when_ready(self):
        """Initialize the cog when the bot is ready."""
        try:
            await self.bot.wait_until_red_ready()
            
            # Initialize aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Fetch available sprites from GitHub
            await self.refresh_github_sprites()
            
            # Start announcement tasks for enabled guilds
            for guild in self.bot.guilds:
                guild_data = await self.config.guild(guild).all()
                if guild_data["enabled"] and guild_data["channel_id"]:
                    self._schedule_next_announcement(guild)
                    
            log.info("SpriteAnnouncer initialization completed successfully")
            
        except asyncio.CancelledError:
            # Cog was unloaded during initialization
            if self.session and not self.session.closed:
                await self.session.close()
            raise
        except Exception as e:
            log.error(f"Error during SpriteAnnouncer initialization: {str(e)}", exc_info=e)
            # Clean up session if initialization failed
            if self.session and not self.session.closed:
                await self.session.close()
    
    async def refresh_github_sprites(self):
        """Fetch the list of available sprites from GitHub repository."""
        if not self.session:
            log.warning("HTTP session not initialized yet, skipping GitHub sprite refresh")
            return self.github_sprites_cache
            
        current_time = datetime.now().timestamp()
        # Only refresh if it's been more than 1 hour since last refresh
        if current_time - self.github_sprites_last_updated < 3600 and self.github_sprites_cache:
            return self.github_sprites_cache
            
        try:
            async with self.session.get(GITHUB_API_BASE) as response:
                if response.status == 200:
                    data = await response.json()
                    # Filter for PNG files
                    sprite_files = [item["name"] for item in data if item["name"].lower().endswith(".png")]
                    if sprite_files:
                        self.github_sprites_cache = sprite_files
                        self.github_sprites_last_updated = current_time
                        log.info(f"Refreshed GitHub sprites: found {len(sprite_files)} sprite files")
                    else:
                        log.warning("No PNG sprite files found in GitHub repository")
                else:
                    log.error(f"Failed to fetch sprites from GitHub: Status {response.status}")
        except Exception as e:
            log.error(f"Error refreshing GitHub sprites: {str(e)}", exc_info=e)
            
        return self.github_sprites_cache
    
    def _schedule_next_announcement(self, guild):
        """Schedule the next announcement for a guild."""
        # Cancel any existing task
        if guild.id in self.task_cache:
            task = self.task_cache[guild.id]
            if task and not task.done():
                task.cancel()
        
        # Create and store the new task
        task = self.bot.loop.create_task(self._timed_announcement_task(guild))
        self.task_cache[guild.id] = task
    
    async def _timed_announcement_task(self, guild):
        """Background task to handle timed announcements."""
        try:
            while True:
                guild_data = await self.config.guild(guild).all()
                
                if not guild_data["enabled"] or not guild_data["channel_id"]:
                    break
                
                channel = guild.get_channel(guild_data["channel_id"])
                if not channel:
                    await self.config.guild(guild).enabled.set(False)
                    log.warning(f"Disabled sprite announcer for guild {guild.id} due to missing channel")
                    break
                
                # Calculate next trigger time
                now = datetime.now()
                next_trigger = guild_data["next_trigger"]
                
                if next_trigger is None:
                    # Calculate random time for next trigger
                    min_minutes = guild_data["frequency"]["min_minutes"]
                    max_minutes = guild_data["frequency"]["max_minutes"]
                    delay_minutes = random.randint(min_minutes, max_minutes)
                    next_time = now + timedelta(minutes=delay_minutes)
                    
                    # Save next trigger time
                    await self.config.guild(guild).next_trigger.set(next_time.timestamp())
                    await asyncio.sleep(delay_minutes * 60)
                else:
                    next_time = datetime.fromtimestamp(next_trigger)
                    if now < next_time:
                        # Wait until next trigger time
                        wait_seconds = (next_time - now).total_seconds()
                        await asyncio.sleep(wait_seconds)
                
                # Trigger announcement
                await self._send_random_announcement(guild)
                
                # Reset next trigger time for a new random delay
                await self.config.guild(guild).next_trigger.set(None)
                await self.config.guild(guild).last_triggered.set(datetime.now().timestamp())
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Error in announcement task for guild {guild.id}", exc_info=e)
    
    async def _get_sprite_url(self, sprite_name):
        """Get the URL for a sprite, either from the default repo or custom sprites."""
        if not self.session:
            log.warning("HTTP session not initialized yet")
            return None
            
        # Check if it's a full URL already
        if sprite_name.startswith(("http://", "https://")):
            return sprite_name
            
        # Check if we have this URL cached
        if sprite_name in self.sprite_cache:
            return self.sprite_cache[sprite_name]
            
        # Otherwise, construct the URL to the raw GitHub content
        url = f"{GITHUB_RAW_BASE}{sprite_name}"
        
        # Verify the URL is valid by making a HEAD request
        try:
            async with self.session.head(url) as response:
                if response.status == 200:
                    self.sprite_cache[sprite_name] = url
                    return url
                else:
                    log.warning(f"Sprite {sprite_name} not found at {url}, status: {response.status}")
        except Exception as e:
            log.error(f"Error checking sprite URL {url}: {str(e)}")
            
        # If we get here, the URL wasn't valid
        return None
    
    async def _send_random_announcement(self, guild):
        """Send a random announcement in the guild's designated channel."""
        guild_data = await self.config.guild(guild).all()
        
        # Get available sprites - first check if we need to refresh from GitHub
        if not self.github_sprites_cache:
            await self.refresh_github_sprites()
            
        # Get enabled sprites from config
        enabled_sprites = guild_data["sprites_enabled"]
        
        # If user has specific sprites enabled, use those
        if enabled_sprites:
            sprites = enabled_sprites
        # Otherwise use all available sprites from GitHub
        elif self.github_sprites_cache:
            sprites = self.github_sprites_cache
        # Fall back to default sprites if GitHub fetch failed
        else:
            sprites = self.default_sprites
            
        # Get available topics/announcements
        topics = guild_data["topics"]
        announcements = guild_data["announcements"]
        
        channel = guild.get_channel(guild_data["channel_id"])
        if not channel:
            return
            
        # Select a random sprite and topic/announcement
        sprite = random.choice(sprites)
        
        # Determine if we're using a topic or announcement
        if random.random() < 0.5 and topics:  # 50% chance for topic if available
            content_type = "topic"
            content = random.choice(topics)
            title = "Let's discuss..."
        elif announcements:
            content_type = "announcement"
            content = random.choice(announcements)
            title = "Announcement!"
        else:
            # Default topic if nothing is configured
            content_type = "topic"
            content = "What's on your mind today?"
            title = "Let's chat!"
        
        # Get sprite URL
        sprite_url = await self._get_sprite_url(sprite)
        
        # If sprite URL is None (not found), try using a default sprite
        if sprite_url is None:
            log.warning(f"Could not find sprite {sprite}, using default sprite instead")
            if self.github_sprites_cache:
                sprite = random.choice(self.github_sprites_cache)
            else:
                sprite = random.choice(self.default_sprites)
            sprite_url = await self._get_sprite_url(sprite)
            
            # If still None, give up
            if sprite_url is None:
                log.error("Could not find any valid sprite URL")
                return
        
        # Create embed
        embed = discord.Embed(
            title=title,
            description=content,
            color=discord.Color.random()
        )
        
        # Add timestamp and sprite character name
        character_name = os.path.splitext(os.path.basename(sprite))[0]
        embed.set_footer(text=f"Character: {character_name}")
        embed.timestamp = datetime.now()
        
        # Add sprite image
        embed.set_thumbnail(url=sprite_url)
        
        # Create buttons for interaction
        view = discord.ui.View()

        # Add a button to get a new topic
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="New Topic (Admin Only)",  # Updated label to indicate admin-only
            custom_id="sprite_announcer:new_topic"
        ))

        # Add a button to show character info
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Character Info",
            custom_id="sprite_announcer:character_info"
        ))
              
        try:
            await channel.send(embed=embed, view=view)
            log.info(f"Sent announcement with sprite {sprite} in guild {guild.id}")
        except Exception as e:
            log.error(f"Error sending announcement: {str(e)}", exc_info=e)
        
    @commands.group(name="spriteannouncer", aliases=["sa"])
    @checks.admin_or_permissions(manage_guild=True)
    async def spriteannouncer(self, ctx):
        """Commands to configure the Sprite Announcer cog."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            
    @spriteannouncer.command(name="toggle")
    async def spriteannouncer_toggle(self, ctx, enabled: bool = None):
        """Enable or disable the sprite announcer.
        
        If no parameter is provided, the current status will be shown.
        """
        current = await self.config.guild(ctx.guild).enabled()
        
        if enabled is None:
            status = "enabled" if current else "disabled"
            await ctx.send(f"The sprite announcer is currently {status}.")
            return
            
        if enabled == current:
            status = "already enabled" if enabled else "already disabled"
            await ctx.send(f"The sprite announcer is {status}.")
            return
            
        await self.config.guild(ctx.guild).enabled.set(enabled)
        
        if enabled:
            # Check if a channel is set
            channel_id = await self.config.guild(ctx.guild).channel_id()
            if not channel_id:
                await ctx.send("Sprite announcer enabled, but no channel is set. "
                              f"Please set a channel with `{ctx.prefix}spriteannouncer channel #your-channel`")
            else:
                # Reset the next trigger time
                await self.config.guild(ctx.guild).next_trigger.set(None)
                # Start the announcement task
                self._schedule_next_announcement(ctx.guild)
                await ctx.send("Sprite announcer enabled! A new topic will appear at a random time.")
        else:
            # Cancel any existing task
            if ctx.guild.id in self.task_cache:
                task = self.task_cache[ctx.guild.id]
                if task and not task.done():
                    task.cancel()
                del self.task_cache[ctx.guild.id]
            await ctx.send("Sprite announcer disabled.")
    
    @spriteannouncer.command(name="channel")
    async def spriteannouncer_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for sprite announcements.
        
        If no channel is provided, the current channel will be shown.
        """
        if channel is None:
            channel_id = await self.config.guild(ctx.guild).channel_id()
            if channel_id:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    await ctx.send(f"The sprite announcer channel is currently {channel.mention}.")
                else:
                    await ctx.send("The sprite announcer channel is set, but the channel no longer exists.")
            else:
                await ctx.send("No sprite announcer channel is set.")
            return
            
        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.send(f"Sprite announcer channel set to {channel.mention}.")
        
        # If enabled, restart the announcer task
        if await self.config.guild(ctx.guild).enabled():
            await self.config.guild(ctx.guild).next_trigger.set(None)
            self._schedule_next_announcement(ctx.guild)
    
    @spriteannouncer.command(name="frequency")
    async def spriteannouncer_frequency(self, ctx, min_minutes: int = None, max_minutes: int = None):
        """Set the frequency range for announcements.
        
        Parameters:
        - min_minutes: Minimum minutes between announcements
        - max_minutes: Maximum minutes between announcements
        
        If no parameters are provided, the current settings will be shown.
        """
        current = await self.config.guild(ctx.guild).frequency()
        
        if min_minutes is None or max_minutes is None:
            await ctx.send(f"Current frequency settings:\n"
                           f"- Minimum minutes: {current['min_minutes']}\n"
                           f"- Maximum minutes: {current['max_minutes']}")
            return
            
        if min_minutes < 1:
            await ctx.send("Minimum minutes must be at least 1.")
            return
            
        if max_minutes < min_minutes:
            await ctx.send("Maximum minutes must be greater than or equal to minimum minutes.")
            return
            
        await self.config.guild(ctx.guild).frequency.set({
            "min_minutes": min_minutes,
            "max_minutes": max_minutes
        })
        
        await ctx.send(f"Frequency set to random intervals between {min_minutes} and {max_minutes} minutes.")
        
        # If enabled, restart the announcer task
        if await self.config.guild(ctx.guild).enabled():
            await self.config.guild(ctx.guild).next_trigger.set(None)
            self._schedule_next_announcement(ctx.guild)
    
    @spriteannouncer.group(name="sprites")
    async def spriteannouncer_sprites(self, ctx):
        """Manage sprite characters for announcements."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @spriteannouncer_sprites.command(name="list")
    async def sprites_list(self, ctx):
        """List all available sprite characters."""
        # Refresh GitHub sprites first
        await self.refresh_github_sprites()
        
        guild_data = await self.config.guild(ctx.guild).all()
        enabled_sprites = guild_data["sprites_enabled"]
        
        # Show special message if GitHub fetch succeeded but no sprites are enabled
        if self.github_sprites_cache and not enabled_sprites:
            message = "# Sprite Characters\n\n"
            message += "**Available from GitHub:**\n"
            
            for sprite in self.github_sprites_cache:
                sprite_name = os.path.splitext(os.path.basename(sprite))[0]
                message += f"- {sprite_name}\n"
                
            message += "\nNo sprites are currently enabled. Using all available sprites."
            
        # Show enabled sprites if any
        elif enabled_sprites:
            message = f"# Sprite Characters ({len(enabled_sprites)} enabled)\n\n"
            message += "**Enabled Sprites:**\n"
            
            for sprite in enabled_sprites:
                sprite_name = os.path.splitext(os.path.basename(sprite))[0]
                message += f"- {sprite_name}\n"
                
            # Also show available sprites if any
            if self.github_sprites_cache:
                message += "\n**Other Available Sprites:**\n"
                for sprite in self.github_sprites_cache:
                    if sprite not in enabled_sprites:
                        sprite_name = os.path.splitext(os.path.basename(sprite))[0]
                        message += f"- {sprite_name}\n"
                        
        # Fall back to defaults if GitHub fetch failed
        else:
            message = "# Sprite Characters (using defaults)\n\n"
            for sprite in self.default_sprites:
                sprite_name = os.path.splitext(os.path.basename(sprite))[0]
                message += f"- {sprite_name}\n"
                
            message += "\n**Note:** Could not fetch sprites from GitHub. Using default list."
            
        for page in pagify(message):
            await ctx.send(box(page, lang="md"))
    
    @spriteannouncer_sprites.command(name="add")
    async def sprites_add(self, ctx, sprite_name: str):
        """Add a sprite to the enabled list.
        
        This can be a sprite name from GitHub or a full URL to a custom sprite.
        """
        # Refresh GitHub sprites first
        await self.refresh_github_sprites()
        
        # Validate the sprite name if it's not a URL
        if not sprite_name.startswith(("http://", "https://")):
            # Check if the sprite exists in GitHub
            if self.github_sprites_cache and sprite_name not in self.github_sprites_cache:
                # Check if they forgot to add .png extension
                if sprite_name + ".png" in self.github_sprites_cache:
                    sprite_name = sprite_name + ".png"
                else:
                    await ctx.send(f"Sprite '{sprite_name}' not found in your GitHub repository. Available sprites: {', '.join(self.github_sprites_cache)}")
                    return
        
        async with self.config.guild(ctx.guild).sprites_enabled() as sprites:
            if sprite_name in sprites:
                await ctx.send(f"Sprite {sprite_name} is already enabled.")
                return
                
            sprites.append(sprite_name)
            
        # Test fetching the sprite to verify it exists
        sprite_url = await self._get_sprite_url(sprite_name)
        if sprite_url:
            await ctx.send(f"Added sprite {sprite_name} to the enabled list.")
        else:
            # Remove it if we couldn't fetch it
            async with self.config.guild(ctx.guild).sprites_enabled() as sprites:
                if sprite_name in sprites:
                    sprites.remove(sprite_name)
            await ctx.send(f"Could not fetch sprite {sprite_name}. Please check that it exists in your GitHub repository.")
    
    @spriteannouncer_sprites.command(name="remove")
    async def sprites_remove(self, ctx, sprite_name: str):
        """Remove a sprite from the enabled list."""
        async with self.config.guild(ctx.guild).sprites_enabled() as sprites:
            if sprite_name not in sprites:
                await ctx.send(f"Sprite {sprite_name} is not in the enabled list.")
                return
                
            sprites.remove(sprite_name)
            
        await ctx.send(f"Removed sprite {sprite_name} from the enabled list.")
    
    @spriteannouncer_sprites.command(name="reset")
    async def sprites_reset(self, ctx):
        """Reset to use all available sprites from GitHub."""
        await self.config.guild(ctx.guild).sprites_enabled.set([])
        # Refresh the GitHub sprites
        await self.refresh_github_sprites()
        
        if self.github_sprites_cache:
            await ctx.send(f"Reset to use all sprites from GitHub. Found {len(self.github_sprites_cache)} sprites.")
        else:
            await ctx.send("Could not fetch sprites from GitHub. Will use default sprites.")
            
    @spriteannouncer_sprites.command(name="refresh")
    async def sprites_refresh(self, ctx):
        """Manually refresh the list of available sprites from GitHub."""
        await ctx.send("Refreshing sprites from GitHub repository...")
        
        # Force a refresh by clearing the cache
        self.github_sprites_last_updated = 0
        self.github_sprites_cache = []
        
        # Refresh from GitHub
        await self.refresh_github_sprites()
        
        if self.github_sprites_cache:
            sprite_list = ", ".join(self.github_sprites_cache)
            await ctx.send(f"Found {len(self.github_sprites_cache)} sprites: {sprite_list}")
        else:
            await ctx.send("Could not fetch sprites from GitHub. Check your repository or try again later.")
    
    @spriteannouncer.group(name="topics")
    async def spriteannouncer_topics(self, ctx):
        """Manage discussion topics for the sprite announcer."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @spriteannouncer_topics.command(name="list")
    async def topics_list(self, ctx):
        """List all configured discussion topics."""
        topics = await self.config.guild(ctx.guild).topics()
        
        if not topics:
            await ctx.send("No discussion topics have been configured.")
            return
            
        message = "# Discussion Topics\n"
        for i, topic in enumerate(topics, 1):
            message += f"{i}. {topic}\n"
            
        for page in pagify(message):
            await ctx.send(box(page, lang="md"))
    
    @spriteannouncer_topics.command(name="bulk")
    async def topics_bulk_add(self, ctx, *, topics_text: str):
        """Add multiple topics at once.
        
        Each topic should be on a new line. You can copy-paste a list of topics.
        
        Example:
        ```
        [p]spriteannouncer topics bulk What's your favorite game?
        If you could travel anywhere, where would you go?
        What's something new you learned recently?
        ```
        """
        # Split the text by newlines and filter out empty lines
        topic_lines = [line.strip() for line in topics_text.split('\n') if line.strip()]
        
        if not topic_lines:
            await ctx.send("No valid topics found. Please provide at least one topic.")
            return
            
        # Add topics to config
        added_count = 0
        existing_count = 0
        async with self.config.guild(ctx.guild).topics() as topics:
            for topic in topic_lines:
                if topic in topics:
                    existing_count += 1
                else:
                    topics.append(topic)
                    added_count += 1
                    
        # Build response message
        msg = f"Added {added_count} new topics."
        if existing_count:
            msg += f" Skipped {existing_count} topics that already existed."
            
        await ctx.send(msg)
    
    @spriteannouncer_topics.command(name="remove")
    async def topics_remove(self, ctx, index: int):
        """Remove a discussion topic by its index number."""
        async with self.config.guild(ctx.guild).topics() as topics:
            if not topics or index <= 0 or index > len(topics):
                await ctx.send("Invalid topic index.")
                return
                
            removed = topics.pop(index - 1)
            
        await ctx.send(f"Removed topic: {removed}")
    
    @spriteannouncer.group(name="announcements")
    async def spriteannouncer_announcements(self, ctx):
        """Manage announcements for the sprite announcer."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @spriteannouncer_announcements.command(name="list")
    async def announcements_list(self, ctx):
        """List all configured announcements."""
        announcements = await self.config.guild(ctx.guild).announcements()
        
        if not announcements:
            await ctx.send("No announcements have been configured.")
            return
            
        message = "# Announcements\n"
        for i, announcement in enumerate(announcements, 1):
            message += f"{i}. {announcement}\n"
            
        for page in pagify(message):
            await ctx.send(box(page, lang="md"))
    
    @spriteannouncer_announcements.command(name="add")
    async def announcements_add(self, ctx, *, announcement: str):
        """Add a new announcement."""
        async with self.config.guild(ctx.guild).announcements() as announcements:
            announcements.append(announcement)
            
        await ctx.send(f"Added new announcement: {announcement}")
        
    @spriteannouncer_announcements.command(name="bulk")
    async def announcements_bulk_add(self, ctx, *, announcements_text: str):
        """Add multiple announcements at once.
        
        Each announcement should be on a new line. You can copy-paste a list of announcements.
        
        Example:
        ```
        [p]spriteannouncer announcements bulk Welcome to our movie night!
        Don't forget to check out our new server rules.
        The server will be getting an update this weekend.
        ```
        """
        # Split the text by newlines and filter out empty lines
        announcement_lines = [line.strip() for line in announcements_text.split('\n') if line.strip()]
        
        if not announcement_lines:
            await ctx.send("No valid announcements found. Please provide at least one announcement.")
            return
            
        # Add announcements to config
        added_count = 0
        existing_count = 0
        async with self.config.guild(ctx.guild).announcements() as announcements:
            for announcement in announcement_lines:
                if announcement in announcements:
                    existing_count += 1
                else:
                    announcements.append(announcement)
                    added_count += 1
                    
        # Build response message
        msg = f"Added {added_count} new announcements."
        if existing_count:
            msg += f" Skipped {existing_count} announcements that already existed."
            
        await ctx.send(msg)
    
    @spriteannouncer_announcements.command(name="remove")
    async def announcements_remove(self, ctx, index: int):
        """Remove an announcement by its index number."""
        async with self.config.guild(ctx.guild).announcements() as announcements:
            if not announcements or index <= 0 or index > len(announcements):
                await ctx.send("Invalid announcement index.")
                return
                
            removed = announcements.pop(index - 1)
            
        await ctx.send(f"Removed announcement: {removed}")
    
    @spriteannouncer.command(name="trigger")
    async def spriteannouncer_trigger(self, ctx):
        """Manually trigger a sprite announcement."""
        if not await self.config.guild(ctx.guild).enabled():
            await ctx.send("The sprite announcer is currently disabled.")
            return
            
        await self._send_random_announcement(ctx.guild)
        await ctx.send("Sprite announcement triggered manually.")
        
    @spriteannouncer.command(name="import")
    async def spriteannouncer_import(self, ctx):
        """Import topics and announcements from an attached text file.
        
        Attach a text file with the following format:
        
        ```
        [TOPICS]
        Topic 1
        Topic 2
        Topic 3
        
        [ANNOUNCEMENTS]
        Announcement 1
        Announcement 2
        Announcement 3
        ```
        
        The cog will parse the file and add all topics and announcements.
        """
        if not ctx.message.attachments:
            await ctx.send("Please attach a text file with topics and announcements.")
            return
            
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.txt'):
            await ctx.send("Please attach a text file (.txt).")
            return
            
        try:
            content = await attachment.read()
            text = content.decode('utf-8')
        except Exception as e:
            await ctx.send(f"Error reading the file: {str(e)}")
            return
            
        # Parse the file content
        mode = None
        topics = []
        announcements = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.upper() == '[TOPICS]':
                mode = 'topics'
            elif line.upper() == '[ANNOUNCEMENTS]':
                mode = 'announcements'
            elif mode == 'topics':
                topics.append(line)
            elif mode == 'announcements':
                announcements.append(line)
                
        # Add topics to config
        topics_added = 0
        announcements_added = 0
        
        if topics:
            async with self.config.guild(ctx.guild).topics() as existing_topics:
                for topic in topics:
                    if topic not in existing_topics:
                        existing_topics.append(topic)
                        topics_added += 1
                        
        if announcements:
            async with self.config.guild(ctx.guild).announcements() as existing_announcements:
                for announcement in announcements:
                    if announcement not in existing_announcements:
                        existing_announcements.append(announcement)
                        announcements_added += 1
                        
        # Build response message
        msg = f"Import complete: Added {topics_added} topics and {announcements_added} announcements."
        await ctx.send(msg)
    
    @spriteannouncer.command(name="status")
    async def spriteannouncer_status(self, ctx):
        """Show the current status of the sprite announcer."""
        guild_data = await self.config.guild(ctx.guild).all()
        
        enabled = guild_data["enabled"]
        channel_id = guild_data["channel_id"]
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        
        frequency = guild_data["frequency"]
        min_minutes = frequency["min_minutes"]
        max_minutes = frequency["max_minutes"]
        
        last_triggered = guild_data["last_triggered"]
        next_trigger = guild_data["next_trigger"]
        
        topics_count = len(guild_data["topics"])
        announcements_count = len(guild_data["announcements"])
        
        # Get sprite counts
        enabled_sprites = guild_data["sprites_enabled"]
        github_sprites = len(self.github_sprites_cache)
        
        if enabled_sprites:
            sprite_status = f"{len(enabled_sprites)} enabled"
        elif github_sprites:
            sprite_status = f"Using all {github_sprites} from GitHub"
        else:
            sprite_status = f"Using {len(self.default_sprites)} defaults"
            
        embed = discord.Embed(
            title="Sprite Announcer Status",
            color=discord.Color.blue() if enabled else discord.Color.red()
        )
        
        embed.add_field(name="Status", value="Enabled" if enabled else "Disabled", inline=True)
        embed.add_field(name="Channel", value=channel.mention if channel else "Not set", inline=True)
        embed.add_field(name="Frequency", value=f"{min_minutes}-{max_minutes} minutes", inline=True)
        
        embed.add_field(name="Sprites", value=sprite_status, inline=True)
        embed.add_field(name="Topics", value=str(topics_count), inline=True)
        embed.add_field(name="Announcements", value=str(announcements_count), inline=True)
        
        # Add GitHub repository info
        embed.add_field(
            name="GitHub Repository",
            value=f"[{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}](https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/tree/main/Character%20Sprite)",
            inline=False
        )
        
        # Add initialization status
        if self._initialization_task:
            if self._initialization_task.done():
                if self._initialization_task.exception():
                    init_status = "❌ Failed"
                else:
                    init_status = "✅ Complete"
            else:
                init_status = "⏳ In Progress"
        else:
            init_status = "❓ Unknown"
            
        embed.add_field(name="Initialization", value=init_status, inline=True)
        
        if last_triggered:
            last_time = datetime.fromtimestamp(last_triggered)
            embed.add_field(
                name="Last Triggered",
                value=f"<t:{int(last_triggered)}:R>",
                inline=True
            )
        
        if next_trigger:
            next_time = datetime.fromtimestamp(next_trigger)
            embed.add_field(
                name="Next Trigger",
                value=f"<t:{int(next_trigger)}:R>",
                inline=True
            )
        
        # Add a thumbnail of a random sprite if available
        if self.github_sprites_cache:
            random_sprite = random.choice(self.github_sprites_cache)
            sprite_url = await self._get_sprite_url(random_sprite)
            if sprite_url:
                embed.set_thumbnail(url=sprite_url)
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions."""
        if not interaction.data or "custom_id" not in interaction.data:
            return
            
        custom_id = interaction.data["custom_id"]
        
        if not custom_id.startswith("sprite_announcer:"):
            return
            
        action = custom_id.split(":", 1)[1]
        
        if action == "new_topic":
            # Check if the user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Sorry, only administrators can generate new topics.", ephemeral=True)
                return
                
            await interaction.response.defer(thinking=True)
            await self._send_random_announcement(interaction.guild)
            await interaction.followup.send("Generated a new topic!", ephemeral=True)
            
        elif action == "character_info":
            # This part remains unchanged - all users can view character info
            # Try to extract character name from the original message
            if not interaction.message or not interaction.message.embeds:
                await interaction.response.send_message("Unable to find character information.", ephemeral=True)
                return
                
            embed = interaction.message.embeds[0]
            footer_text = embed.footer.text if embed.footer else ""
            
            character_name = None
            if footer_text and footer_text.startswith("Character: "):
                character_name = footer_text[11:]
                
            if not character_name:
                await interaction.response.send_message("Character information not available.", ephemeral=True)
                return
                
            # Generate character info
            info_embed = discord.Embed(
                title=f"About {character_name}",
                description=f"This is {character_name}, one of the sprite characters who helps facilitate discussions!",
                color=discord.Color.gold()
            )
            
            # Use the same thumbnail from the original message
            if embed.thumbnail:
                info_embed.set_thumbnail(url=embed.thumbnail.url)
                
            # Add some randomized character traits
            personalities = ["Cheerful", "Thoughtful", "Curious", "Energetic", "Calm", "Witty", "Friendly", "Mysterious"]
            hobbies = ["Reading", "Gaming", "Hiking", "Art", "Music", "Cooking", "Exploring", "Collecting"]
            
            info_embed.add_field(name="Personality", value=random.choice(personalities), inline=True)
            info_embed.add_field(name="Favorite Activity", value=random.choice(hobbies), inline=True)
            
            await interaction.response.send_message(embed=info_embed, ephemeral=True)
