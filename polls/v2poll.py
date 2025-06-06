import discord
import asyncio
import aiohttp
import random
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import json

from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import humanize_list, box


# GitHub API endpoints for character sprites
GITHUB_REPO_OWNER = "AfterWorld"
GITHUB_REPO_NAME = "ultcogs"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/Character%20Sprite"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/Character%20Sprite/"

# Component V2 flag
IS_COMPONENTS_V2 = 1 << 15


class V2Poll(commands.Cog):
    """Create interactive polls using Discord Components V2 with character sprites."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=953439127, force_registration=True)
        
        default_guild = {
            "polls": {},  # poll_id: {options, votes, end_time, etc.}
            "settings": {
                "default_duration": 60,  # Default poll duration in minutes
                "use_sprites": True      # Whether to use character sprites by default
            }
        }
        
        # Global settings for sprite cache
        self.config.register_global(cached_sprites=[])
        self.config.register_guild(**default_guild)
        self.active_polls: Dict[int, asyncio.Task] = {}  # message_id: task
        self.sprite_cache: Dict[str, str] = {}  # filename: url
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        """Clean up running tasks when the cog is unloaded."""
        for task in self.active_polls.values():
            task.cancel()
        
        # Close the aiohttp session
        asyncio.create_task(self.session.close())

    async def fetch_available_sprites(self, force_refresh: bool = False) -> List[Dict[str, str]]:
        """Fetch available sprites from GitHub repository."""
        # Use global scope for sprite caching
        cached_sprites = await self.config.cached_sprites()
        
        # Use cached sprites if available and not forcing refresh
        if cached_sprites and not force_refresh:
            return cached_sprites
            
        try:
            async with self.session.get(GITHUB_API_BASE) as response:
                if response.status == 200:
                    content = await response.json()
                    sprites = []
                    for item in content:
                        if item["type"] == "file" and item["name"].lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                            sprite_info = {
                                "name": item["name"],
                                "url": GITHUB_RAW_BASE + item["name"],
                                "display_name": item["name"].split(".")[0].replace("_", " ")
                            }
                            sprites.append(sprite_info)
                            self.sprite_cache[item["name"]] = sprite_info["url"]
                    
                    # Cache the sprites
                    if sprites:
                        await self.config.cached_sprites.set(sprites)
                    
                    return sprites
                else:
                    return []
        except Exception as e:
            print(f"Error fetching sprites: {e}")
            return cached_sprites or []

    async def get_sprite_url(self, sprite_name: str) -> Optional[str]:
        """Get the URL for a sprite by name."""
        # Check cache first
        if sprite_name and sprite_name in self.sprite_cache:
            return self.sprite_cache[sprite_name]
            
        # Try to find in cached sprites
        sprites = await self.fetch_available_sprites()
        for sprite in sprites:
            if sprite["name"] == sprite_name:
                self.sprite_cache[sprite_name] = sprite["url"]
                return sprite["url"]
                
        return None

    async def get_random_sprites(self, count: int = 4) -> List[Dict[str, str]]:
        """Get a random selection of sprites."""
        sprites = await self.fetch_available_sprites()
        if not sprites:
            return []
            
        if len(sprites) <= count:
            return sprites
            
        return random.sample(sprites, count)

    def create_poll_components(self, options: List[str]) -> List[Dict]:
        """Create Components V2 for a poll."""
        components = []
        
        # Group vote buttons into action rows (max 5 buttons per row)
        for i in range(0, len(options), 5):
            buttons = []
            for j, option in enumerate(options[i:i+5], i):
                buttons.append({
                    "type": 2,  # Button type
                    "style": 1,  # Primary style
                    "label": f"Vote for {option}",
                    "custom_id": f"vote_{j}"
                })
            
            # Add action row with buttons
            components.append({
                "type": 1,  # Action row
                "components": buttons
            })
        
        return components

    def create_sprite_select_menu(self, options: List[str], sprites: List[Dict[str, str]]) -> Dict:
        """Create a select menu for sprite options."""
        select_options = []
        
        for i, (option, sprite) in enumerate(zip(options, sprites)):
            # Create option with emoji if applicable
            option_data = {
                "label": option,
                "value": f"vote_{i}",
                "description": f"Vote for {option}"
            }
            
            # TODO: Add custom emojis for sprites if possible
            
            select_options.append(option_data)
        
        return {
            "type": 3,  # Select Menu
            "custom_id": "sprite_vote",
            "placeholder": "Select your favorite",
            "options": select_options
        }

    @commands.group()
    @commands.guild_only()
    async def poll(self, ctx: commands.Context):
        """Commands for creating and managing interactive polls with sprites."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @poll.command(name="create")
    @commands.guild_only()
    async def poll_create(self, ctx: commands.Context, title: str, duration: Optional[int] = None, *options):
        """Create a new poll with interactive voting components.
        
        Examples:
        - [p]poll create "Favorite character?" 30 Mario Luigi Peach Bowser
        - [p]poll create "Best game?" 60 "Super Mario" "Zelda" "Pokemon" "Final Fantasy"
        
        Arguments:
        - title: The title/question for the poll
        - duration: Optional duration in minutes (default: 60)
        - options: The voting options (at least 2, maximum 10)
        """
        if not options or len(options) < 2:
            return await ctx.send("You need to provide at least 2 options for the poll.")
        
        if len(options) > 10:
            return await ctx.send("You can only have up to 10 options in a poll.")
            
        # Get default duration if not specified
        if duration is None:
            guild_settings = await self.config.guild(ctx.guild).settings()
            duration = guild_settings["default_duration"]
        
        # Calculate end time
        end_time = datetime.utcnow() + timedelta(minutes=duration)
        end_timestamp = int(end_time.timestamp())
        
        try:
            # Fetch sprites for the poll
            all_sprites = await self.fetch_available_sprites()
            
            # Try to match options with sprite names
            option_sprites = []
            for option in options:
                found = False
                for sprite in all_sprites:
                    # Check for exact match or if option is in sprite name (case insensitive)
                    if option.lower() == sprite["display_name"].lower() or option.lower() in sprite["name"].lower():
                        option_sprites.append(sprite)
                        found = True
                        break
                
                if not found:
                    # Add a placeholder for options without matching sprites
                    option_sprites.append({
                        "name": None,
                        "url": None,
                        "display_name": option
                    })
            
            # Create a standard Discord view with buttons first as fallback
            view = discord.ui.View()
            
            # Add vote buttons for each option
            for i, option in enumerate(options):
                # Create a vote button for this option
                vote_button = discord.ui.Button(
                    label=f"Vote for {option}", 
                    custom_id=f"vote_{i}", 
                    style=discord.ButtonStyle.primary
                )
                view.add_item(vote_button)
            
            # Create an embed with sprite images
            embed = discord.Embed(
                title=f"📊 {title}",
                description=f"Poll ends: <t:{end_timestamp}:R>",
                color=discord.Color.blue()
            )
            
            # Add sprites first as a grid at the top if available
            sprite_showcase = ""
            sprite_urls = []
            for i, sprite in enumerate(option_sprites):
                if sprite["url"]:
                    sprite_showcase += f"[{options[i]}]({sprite['url']}) • "
                    sprite_urls.append(sprite["url"])
            
            if sprite_showcase:
                embed.description = f"Poll ends: <t:{end_timestamp}:R>\n\n{sprite_showcase[:-3]}"
            
            # Add all options in a single field for compact display
            options_text = ""
            for i, option in enumerate(options):
                options_text += f"**{i+1}. {option}** - 0 votes\n"
            
            embed.add_field(
                name="Options",
                value=options_text,
                inline=False
            )
            
            # Add a random sprite as thumbnail if available
            if sprite_urls:
                embed.set_thumbnail(url=random.choice(sprite_urls))
            
            # Create Components V2 formatted components
            components = self.create_poll_components(options)
            
            # Try to send with Components V2 first via HTTP
            try:
                # Use webhook execution to send the message with Components V2
                webhook = await ctx.channel.create_webhook(name="PollBot")
                poll_message = await webhook.send(
                    embed=embed,
                    wait=True,
                    username=ctx.me.display_name,
                    avatar_url=ctx.me.display_avatar.url,
                    allowed_mentions=discord.AllowedMentions.none(),
                    flags=IS_COMPONENTS_V2,
                    components=components
                )
                await webhook.delete()
            except Exception as e:
                # Fallback to standard view if Components V2 fails
                print(f"Components V2 failed: {e}, using standard view instead")
                
                # Create a standard Discord select menu
                view = discord.ui.View()
                select = discord.ui.Select(
                    placeholder="Choose your favorite option",
                    custom_id="sprite_vote"
                )
                
                # Add options to the select menu
                for i, option in enumerate(options):
                    select.add_option(
                        label=option,
                        value=f"vote_{i}",
                        description=f"Vote for {option}"
                    )
                
                view.add_item(select)
                poll_message = await ctx.send(embed=embed, view=view)
            
            # Register the poll in the config
            async with self.config.guild(ctx.guild).polls() as polls:
                poll_data = {
                    "title": title,
                    "options": list(options),
                    "option_sprites": [sprite["name"] for sprite in option_sprites],
                    "votes": {str(i): [] for i in range(len(options))},
                    "end_time": end_timestamp,
                    "channel_id": ctx.channel.id,
                    "author_id": ctx.author.id,
                    "message_id": poll_message.id,
                    "is_dropdown": True
                }
                polls[str(poll_message.id)] = poll_data
            
            # Start the poll end timer
            self.active_polls[poll_message.id] = asyncio.create_task(
                self._end_poll_timer(ctx.guild.id, poll_message.id, duration * 60)
            )
                
        except Exception as e:
            await ctx.send(f"Error creating dropdown poll: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle interactions for polls."""
        if not interaction.data:
            return
            
        # Handle both button votes and dropdown select votes
        custom_id = interaction.data.get('custom_id', '')
        is_vote = custom_id.startswith('vote_')
        is_dropdown = custom_id == 'sprite_vote'
        
        if not (is_vote or is_dropdown):
            return

        try:
            # Get the message id
            message_id = interaction.message.id
            guild_id = interaction.guild.id
            
            # Get poll data
            all_polls = await self.config.guild(interaction.guild).polls()
            if str(message_id) not in all_polls:
                return
                
            poll_data = all_polls[str(message_id)]
            
            # Get the option index from the custom_id
            if is_vote:
                option_index = int(custom_id.split('_')[1])
            elif is_dropdown:
                # For dropdown, get the selected value
                values = interaction.data.get('values', [])
                if not values:
                    return
                    
                option_value = values[0]
                if not option_value.startswith('vote_'):
                    return
                    
                option_index = int(option_value.split('_')[1])
            else:
                return
            
            # Update the vote in the config
            async with self.config.guild(interaction.guild).polls() as polls:
                if str(message_id) not in polls:
                    return
                    
                poll_data = polls[str(message_id)]
                
                # Remove user from any existing votes
                for opt_idx in poll_data["votes"].keys():
                    if interaction.user.id in poll_data["votes"][opt_idx]:
                        poll_data["votes"][opt_idx].remove(interaction.user.id)
                
                # Add user to the selected option
                poll_data["votes"][str(option_index)].append(interaction.user.id)
                
                # Update the poll data
                polls[str(message_id)] = poll_data
            
            # Update the vote counters
            vote_counts = {}
            for opt_idx, voters in poll_data["votes"].items():
                vote_counts[int(opt_idx)] = len(voters)
            
            # Create a new updated embed with current vote counts
            updated_embed = discord.Embed(
                title=f"📊 {poll_data['title']}",
                description=f"Poll ends: <t:{poll_data['end_time']}:R>",
                color=discord.Color.blue()
            )
            
            # Create a layout that shows all sprites inline with their options
            options = poll_data["options"]
            
            # Add sprites first as a grid at the top
            sprite_names = poll_data.get("option_sprites", [])
            sprite_urls = []
            for i, sprite_name in enumerate(sprite_names):
                if sprite_name:
                    url = await self.get_sprite_url(sprite_name)
                    if url:
                        sprite_urls.append((i, options[i], url))
            
            if sprite_urls:
                # Create sprite showcase
                sprite_showcase = ""
                for i, option, url in sprite_urls:
                    sprite_showcase += f"[{option}]({url}) • "
                
                if sprite_showcase:
                    updated_embed.description = f"Poll ends: <t:{poll_data['end_time']}:R>\n\n{sprite_showcase[:-3]}"
            
            # Add all options in a single field for compact display
            options_text = ""
            for i, option in enumerate(poll_data["options"]):
                votes = vote_counts.get(i, 0)
                options_text += f"**{i+1}. {option}** - {votes} votes\n"
            
            updated_embed.add_field(
                name="Options",
                value=options_text,
                inline=False
            )
            
            # Add a random sprite as thumbnail if available
            if sprite_urls:
                updated_embed.set_thumbnail(url=random.choice(sprite_urls)[2])
            
            # Try to update with V2 components
            try:
                # Get the original components and update them
                await interaction.message.edit(embed=updated_embed)
            except Exception as e:
                print(f"Error updating poll message: {e}")
            
            # Acknowledge the interaction
            await interaction.response.send_message(
                f"Your vote for '{poll_data['options'][option_index]}' has been recorded!", 
                ephemeral=True
            )
        except Exception as e:
            print(f"Error handling interaction: {e}")
            # Try to acknowledge the interaction even if there was an error
            try:
                await interaction.response.send_message(
                    "There was an error processing your vote. Please try again.",
                    ephemeral=True
                )
            except:
                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Handle poll message deletion."""
        # Check if this message was a poll
        guild = message.guild
        if not guild:
            return
            
        polls = await self.config.guild(guild).polls()
        
        if str(message.id) in polls:
            # Cancel the timer task if it exists
            if message.id in self.active_polls:
                self.active_polls[message.id].cancel()
                del self.active_polls[message.id]
                
            # Remove the poll from the config
            async with self.config.guild(guild).polls() as polls_config:
                if str(message.id) in polls_config:
                    del polls_config[str(message.id)]

    @poll.command(name="sprite")
    @commands.guild_only()
    async def poll_sprite(self, ctx: commands.Context, title: str, duration: Optional[int] = None):
        """Create a poll using random character sprites as options.
        
        Examples:
        - [p]poll sprite "Which character is best?" 30
        - [p]poll sprite "Vote for your favorite!" 
        
        Arguments:
        - title: The title/question for the poll
        - duration: Optional duration in minutes (default: 60)
        """
        # Get random sprites
        sprites = await self.get_random_sprites(count=4)
        
        if not sprites:
            return await ctx.send("No character sprites found! Please try again later.")
        
        # Use sprite display names as options
        options = [sprite["display_name"] for sprite in sprites]
        
        # Call the regular poll create command
        await self.poll_create(ctx, title, duration, *options)

    async def _end_poll_timer(self, guild_id: int, message_id: int, duration: int):
        """Timer to end the poll after the specified duration."""
        try:
            await asyncio.sleep(duration)
            
            # Get the poll data
            all_polls = await self.config.guild_from_id(guild_id).polls()
            if str(message_id) not in all_polls:
                return
                
            poll_data = all_polls[str(message_id)]
            
            # Get the channel and message
            channel = self.bot.get_channel(poll_data["channel_id"])
            if not channel:
                return
                
            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                # Message was deleted
                async with self.config.guild_from_id(guild_id).polls() as polls:
                    if str(message_id) in polls:
                        del polls[str(message_id)]
                return
            
            # Create results embed
            embed = discord.Embed(
                title=f"📊 Poll Results: {poll_data['title']}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # Count votes
            vote_counts = {}
            total_votes = 0
            for option_idx, voters in poll_data["votes"].items():
                vote_counts[int(option_idx)] = len(voters)
                total_votes += len(voters)
            
            # Find winner(s)
            if total_votes > 0:
                max_votes = max(vote_counts.values())
                winners = [
                    poll_data["options"][idx] 
                    for idx, votes in vote_counts.items() 
                    if votes == max_votes
                ]
                
                # Add sprites first as a grid at the top
                sprite_showcase = ""
                sprite_urls = []
                options = poll_data["options"]
                sprite_names = poll_data.get("option_sprites", [])
                
                for i, sprite_name in enumerate(sprite_names):
                    if sprite_name:
                        url = await self.get_sprite_url(sprite_name)
                        if url:
                            sprite_showcase += f"[{options[i]}]({url}) • "
                            sprite_urls.append((i, options[i], url))
                
                if sprite_showcase:
                    embed.description = f"{sprite_showcase[:-3]}\n\n"
                
                # Add results
                results_text = ""
                for i, option in enumerate(poll_data["options"]):
                    votes = vote_counts.get(i, 0)
                    percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
                    bar = "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
                    is_winner = option in winners
                    
                    results_text += f"**{i+1}.** **{option}**" + (" 👑" if is_winner else "") + "\n"
                    results_text += f"{bar} {votes} votes ({percentage:.1f}%)\n\n"
                
                embed.add_field(
                    name="Results",
                    value=results_text,
                    inline=False
                )
                
                if len(winners) == 1:
                    if embed.description:
                        embed.description = f"**Winner: {winners[0]}** with {max_votes} votes!\n\n" + embed.description
                    else:
                        embed.description = f"**Winner: {winners[0]}** with {max_votes} votes!"
                    
                    # Add winner sprite as thumbnail if available
                    winner_idx = poll_data["options"].index(winners[0])
                    winner_sprite = poll_data.get("option_sprites", [])[winner_idx] if winner_idx < len(poll_data.get("option_sprites", [])) else None
                    if winner_sprite:
                        winner_url = await self.get_sprite_url(winner_sprite)
                        if winner_url:
                            embed.set_thumbnail(url=winner_url)
                else:
                    if embed.description:
                        embed.description = f"**Tie between: {humanize_list(winners)}** with {max_votes} votes each!\n\n" + embed.description
                    else:
                        embed.description = f"**Tie between: {humanize_list(winners)}** with {max_votes} votes each!"
                
                embed.set_footer(text=f"Total votes: {total_votes}")
            else:
                embed.description = "No votes were cast in this poll."
            
            # Remove the poll from the active polls and config
            async with self.config.guild_from_id(guild_id).polls() as polls_config:
                if str(message_id) in polls_config:
                    del polls_config[str(message_id)]
            
            # Send results and update the original message
            await channel.send(
                f"The poll **{poll_data['title']}** has ended!",
                embed=embed
            )
            
            # Try to disable the buttons on the original message
            try:
                # Create a disabled view
                disabled_view = discord.ui.View()
                for i, option in enumerate(poll_data["options"]):
                    # Add disabled buttons
                    disabled_button = discord.ui.Button(
                        label=f"Vote for {option}",
                        custom_id=f"vote_{i}",
                        style=discord.ButtonStyle.primary,
                        disabled=True
                    )
                    disabled_view.add_item(disabled_button)
                
                # Update the embed to show it's ended
                ended_embed = discord.Embed(
                    title=f"📊 {poll_data['title']} (ENDED)",
                    description="This poll has ended. See results above.",
                    color=discord.Color.grey()
                )
                
                try:
                    # Try to update with V2 components first
                    webhook = await channel.create_webhook(name="PollBot")
                    disabled_components = []
                    for i in range(0, len(poll_data["options"]), 5):
                        buttons = []
                        for j, option in enumerate(poll_data["options"][i:i+5], i):
                            buttons.append({
                                "type": 2,  # Button type
                                "style": 1,  # Primary style
                                "label": f"Vote for {option}",
                                "custom_id": f"vote_{j}",
                                "disabled": True
                            })
                        
                        disabled_components.append({
                            "type": 1,  # Action row
                            "components": buttons
                        })
                    
                    await message.edit(
                        embed=ended_embed,
                        flags=IS_COMPONENTS_V2,
                        components=disabled_components
                    )
                    await webhook.delete()
                except Exception:
                    # Fallback to standard view
                    await message.edit(embed=ended_embed, view=disabled_view)
                
            except discord.HTTPException:
                # If we can't edit the message, just ignore
                pass
                
        except asyncio.CancelledError:
            # Task was cancelled
            pass
        except Exception as e:
            # Log any errors
            print(f"Error in poll end timer: {e}")
        finally:
            # Remove from active polls
            if message_id in self.active_polls:
                del self.active_polls[message_id]

    @poll.command(name="list")
    @commands.guild_only()
    async def poll_list(self, ctx: commands.Context):
        """List all active polls in this server."""
        polls = await self.config.guild(ctx.guild).polls()
        
        if not polls:
            return await ctx.send("There are no active polls in this server.")
            
        embed = discord.Embed(
            title="Active Polls",
            color=discord.Color.blue(),
            description=f"There are {len(polls)} active polls in this server."
        )
        
        for poll_id, poll_data in polls.items():
            end_time = poll_data["end_time"]
            total_votes = sum(len(voters) for voters in poll_data["votes"].values())
            
            embed.add_field(
                name=poll_data["title"],
                value=(
                    f"Options: {len(poll_data['options'])}\n"
                    f"Votes: {total_votes}\n"
                    f"Ends: <t:{end_time}:R>\n"
                    f"[Jump to Poll](https://discord.com/channels/{ctx.guild.id}/{poll_data['channel_id']}/{poll_id})"
                ),
                inline=True
            )
            
        await ctx.send(embed=embed)

    @poll.command(name="end")
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    async def poll_end(self, ctx: commands.Context, message_id: int):
        """End a poll early.
        
        Arguments:
        - message_id: The ID of the poll message
        """
        polls = await self.config.guild(ctx.guild).polls()
        
        if str(message_id) not in polls:
            return await ctx.send("No active poll found with that message ID.")
            
        # Cancel the timer task
        if message_id in self.active_polls:
            self.active_polls[message_id].cancel()
            del self.active_polls[message_id]
            
        # Trigger poll end manually
        await self._end_poll_timer(ctx.guild.id, message_id, 0)
        
        await ctx.send("Poll ended successfully.")

    @poll.group(name="settings")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def poll_settings(self, ctx: commands.Context):
        """Configure poll settings."""
        if ctx.invoked_subcommand is None:
            settings = await self.config.guild(ctx.guild).settings()
            
            embed = discord.Embed(
                title="Poll Settings",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Default Duration",
                value=f"{settings['default_duration']} minutes"
            )
            
            embed.add_field(
                name="Use Character Sprites",
                value="Enabled" if settings.get('use_sprites', True) else "Disabled"
            )
            
            await ctx.send(embed=embed)

    @poll_settings.command(name="duration")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def poll_settings_duration(self, ctx: commands.Context, minutes: int):
        """Set the default poll duration.
        
        Arguments:
        - minutes: Default duration in minutes (must be between 1 and 10080)
        """
        if minutes < 1 or minutes > 10080:  # 10080 minutes = 1 week
            return await ctx.send("Default duration must be between 1 minute and 1 week (10080 minutes).")
            
        await self.config.guild(ctx.guild).settings.default_duration.set(minutes)
        await ctx.send(f"Default poll duration set to {minutes} minutes.")

    @poll_settings.command(name="sprites")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def poll_settings_sprites(self, ctx: commands.Context, enabled: bool = None):
        """Toggle the use of character sprites in polls.
        
        Arguments:
        - enabled: Set to True to enable sprites, False to disable
        """
        if enabled is None:
            # Toggle current setting
            current = await self.config.guild(ctx.guild).settings.use_sprites()
            enabled = not current
            
        await self.config.guild(ctx.guild).settings.use_sprites.set(enabled)
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"Character sprites in polls are now {status}.")

    @poll.command(name="sprites")
    @commands.guild_only()
    async def poll_sprites(self, ctx: commands.Context, force_refresh: bool = False):
        """List all available character sprites for polls.
        
        Arguments:
        - force_refresh: Set to True to force refresh the sprite cache
        """
        # Fetch available sprites
        sprites = await self.fetch_available_sprites(force_refresh=force_refresh)
        
        if not sprites:
            return await ctx.send("No character sprites are available.")
            
        # Create an embed to display sprites
        embed = discord.Embed(
            title="Available Character Sprites",
            color=discord.Color.blue(),
            description=f"There are {len(sprites)} sprites available for polls."
        )
        
        # Add up to 25 sprites (Discord embed field limit)
        for i, sprite in enumerate(sprites[:25]):
            embed.add_field(
                name=sprite["display_name"],
                value=f"[View]({sprite['url']})",
                inline=True
            )
            
        # Set a random sprite as the thumbnail
        if sprites:
            embed.set_thumbnail(url=random.choice(sprites)["url"])
            
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def spritepoll(self, ctx: commands.Context, title: str, *options):
        """Create a sprite-based poll with the specified options.
        
        If options are provided, it will try to match them with sprites.
        If no options are provided, it will use random sprites.
        
        Examples:
        - [p]spritepoll "Best character?" Mario Luigi Peach
        - [p]spritepoll "Who would win?" 
        
        Arguments:
        - title: The title/question for the poll
        - options: Optional. The character names to use as options
        """
        # Get default duration
        duration = await self.config.guild(ctx.guild).settings.default_duration()
        
        if options:
            # Pass to the main poll creation command
            await self.poll_create(ctx, title, duration, *options)
        else:
            # Use random sprites
            await self.poll_sprite(ctx, title, duration)

    @poll.command(name="dropdown")
    @commands.guild_only()
    async def poll_dropdown(self, ctx: commands.Context, title: str, duration: Optional[int] = None, *options):
        """Create a poll with a dropdown menu for voting.
        
        Examples:
        - [p]poll dropdown "Which element is your favorite?" 30 Fire Water Earth Air
        - [p]poll dropdown "Best Pokemon type?" 60 "Normal" "Fire" "Water" "Grass"
        
        Arguments:
        - title: The title/question for the poll
        - duration: Optional duration in minutes (default: 60)
        - options: The voting options (at least 2, maximum 25)
        """
        if not options or len(options) < 2:
            return await ctx.send("You need to provide at least 2 options for the poll.")
        
        if len(options) > 25:
            return await ctx.send("You can only have up to 25 options in a dropdown poll.")
            
        # Get default duration if not specified
        if duration is None:
            guild_settings = await self.config.guild(ctx.guild).settings()
            duration = guild_settings["default_duration"]
        
        # Calculate end time
        end_time = datetime.utcnow() + timedelta(minutes=duration)
        end_timestamp = int(end_time.timestamp())
        
        try:
            # Fetch sprites for the poll
            all_sprites = await self.fetch_available_sprites()
            
            # Try to match options with sprite names
            option_sprites = []
            for option in options:
                found = False
                for sprite in all_sprites:
                    # Check for exact match or if option is in sprite name (case insensitive)
                    if option.lower() == sprite["display_name"].lower() or option.lower() in sprite["name"].lower():
                        option_sprites.append(sprite)
                        found = True
                        break
                
                if not found:
                    # Add a placeholder for options without matching sprites
                    option_sprites.append({
                        "name": None,
                        "url": None,
                        "display_name": option
                    })
            
            # Create an embed with sprite images
            embed = discord.Embed(
                title=f"📊 {title}",
                description=f"Poll ends: <t:{end_timestamp}:R>",
                color=discord.Color.blue()
            )
            
            # Add sprites first as a grid at the top if available
            sprite_showcase = ""
            sprite_urls = []
            for i, sprite in enumerate(option_sprites):
                if sprite["url"]:
                    sprite_showcase += f"[{options[i]}]({sprite['url']}) • "
                    sprite_urls.append(sprite["url"])
            
            if sprite_showcase:
                embed.description = f"Poll ends: <t:{end_timestamp}:R>\n\n{sprite_showcase[:-3]}"
            
            # Add all options in a single field for compact display
            options_text = ""
            for i, option in enumerate(options):
                options_text += f"**{i+1}. {option}** - 0 votes\n"
            
            embed.add_field(
                name="Options",
                value=options_text,
                inline=False
            )
            
            # Add a random sprite as thumbnail if available
            if sprite_urls:
                embed.set_thumbnail(url=random.choice(sprite_urls))
            
            # Create select menu options
            select_options = []
            for i, option in enumerate(options):
                option_data = {
                    "label": option,
                    "value": f"vote_{i}",
                    "description": f"Vote for {option}"
                }
                select_options.append(option_data)
            
            # Create select menu component
            select_menu = {
                "type": 3,  # Select Menu
                "custom_id": "sprite_vote",
                "placeholder": "Choose your favorite option",
                "options": select_options
            }
            
            # Create Components V2 formatted components with select menu
            components = [{
                "type": 1,  # Action row
                "components": [select_menu]
            }]
            
            try:
                # Use webhook execution to send the message with Components V2
                webhook = await ctx.channel.create_webhook(name="PollBot")
                poll_message = await webhook.send(
                    embed=embed,
                    wait=True,
                    username=ctx.me.display_name,
                    avatar_url=ctx.me.display_avatar.url,
                    allowed_mentions=discord.AllowedMentions.none(),
                    flags=IS_COMPONENTS_V2,
                    components=components
                )
                await webhook.delete()
            except Exception as e:
                # Fallback to standard view if Components V2 fails
                print(f"Components V2 failed: {e}, using standard view instead")
                
                # Create a standard Discord select menu
                view = discord.ui.View()
                select = discord.ui.Select(
                    placeholder="Choose your favorite option",
                    custom_id="sprite_vote"
                )
                
                # Add options to the select menu
                for i, option in enumerate(options):
                    select.add_option(
                        label=option,
                        value=f"vote_{i}",
                        description=f"Vote for {option}"
                    )
                
                view.add_item(select)
                poll_message = await ctx.send(embed=embed, view=view)
            
            # Register the poll in the config
            async with self.config.guild(ctx.guild).polls() as polls:
                poll_data = {
                    "title": title,
                    "options": list(options),
                    "option_sprites": [sprite["name"] for sprite in option_sprites],
                    "votes": {str(i): [] for i in range(len(options))},
                    "end_time": end_timestamp,
                    "channel_id": ctx.channel.id,
                    "author_id": ctx.author.id,
                    "message_id": poll_message.id,
                    "is_dropdown": True
                }
                polls[str(poll_message.id)] = poll_data
            
            # Start the poll end timer
            self.active_polls[poll_message.id] = asyncio.create_task(
                self._end_poll_timer(ctx.guild.id, poll_message.id, duration * 60)
            )
                
        except Exception as e:
            await ctx.send(f"Error creating dropdown poll: {e}")

async def setup(bot):
    await bot.add_cog(V2Poll(bot))
