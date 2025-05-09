import discord
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import humanize_list, box


class V2Poll(commands.Cog):
    """Create interactive polls using Discord Components V2."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=953439127, force_registration=True)
        
        default_guild = {
            "polls": {},  # poll_id: {options, votes, end_time, etc.}
            "settings": {"default_duration": 60}  # Default poll duration in minutes
        }
        
        self.config.register_guild(**default_guild)
        self.active_polls: Dict[int, asyncio.Task] = {}  # message_id: task

    def cog_unload(self):
        """Clean up running tasks when the cog is unloaded."""
        for task in self.active_polls.values():
            task.cancel()

    @commands.group()
    @commands.guild_only()
    async def poll(self, ctx: commands.Context):
        """Commands for creating and managing interactive polls."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @poll.command(name="create")
    @commands.guild_only()
    async def poll_create(self, ctx: commands.Context, title: str, duration: Optional[int] = None, *options):
        """Create a new poll with interactive voting buttons.
        
        Examples:
        - [p]poll create "Favorite color?" 30 Red Blue Green
        - [p]poll create "Best movie?" 60 "The Matrix" "Star Wars" "Inception"
        
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
            duration = await self.config.guild(ctx.guild).settings.default_duration()
        
        # Calculate end time
        end_time = datetime.utcnow() + timedelta(minutes=duration)
        end_timestamp = int(end_time.timestamp())
        
        try:
            # Try to create a Components V2 poll
            # Create a LayoutView for the poll
            layout_view = discord.ui.LayoutView()
            
            # Add the title as a TextDisplay component
            title_text = discord.ui.TextDisplay(f"📊 **{title}**")
            layout_view.add_item(title_text)
            
            # Add duration info
            duration_text = discord.ui.TextDisplay(
                f"Poll ends: <t:{end_timestamp}:R>"
            )
            layout_view.add_item(duration_text)
            
            # Set up a container for options and vote buttons
            class PollContainer(discord.ui.Container):
                def __init__(self, options):
                    super().__init__()
                    self.options = options
                    
                    # Create option sections with vote buttons
                    for i, option in enumerate(options):
                        # Create vote button
                        vote_button = discord.ui.Button(
                            label=f"Vote", 
                            custom_id=f"vote_{i}", 
                            style=discord.ButtonStyle.primary
                        )
                        
                        # Create a section with the button as accessory
                        option_text = discord.ui.TextDisplay(f"{i+1}. {option}")
                        # Create section with accessory provided as a keyword argument
                        section = discord.ui.Section(accessory=vote_button)
                        section.add_item(option_text)
                        
                        # Add the section to the container
                        self.add_item(section)
            
            # Create the container with options
            options_container = PollContainer(options)
            
            # Create vote counters display
            vote_counters = discord.ui.TextDisplay(
                "\n".join([f"{i+1}. {option}: 0 votes" for i, option in enumerate(options)])
            )
            
            # Add components to the layout
            layout_view.add_item(options_container)
            layout_view.add_item(vote_counters)
            
            # Send the poll message
            poll_message = await ctx.send(view=layout_view)
            
            # Register the poll in the config
            async with self.config.guild(ctx.guild).polls() as polls:
                poll_data = {
                    "title": title,
                    "options": list(options),
                    "votes": {str(i): [] for i in range(len(options))},
                    "end_time": end_timestamp,
                    "channel_id": ctx.channel.id,
                    "author_id": ctx.author.id,
                    "message_id": poll_message.id
                }
                polls[str(poll_message.id)] = poll_data
            
            # Start the poll end timer
            self.active_polls[poll_message.id] = asyncio.create_task(
                self._end_poll_timer(ctx.guild.id, poll_message.id, duration * 60)
            )
            
            # Set up interaction handler for vote buttons
            @self.bot.listen('on_interaction')
            async def on_poll_vote(interaction: discord.Interaction):
                # Check if this is a vote interaction for our poll
                if (interaction.message.id != poll_message.id or 
                    not interaction.data.get('custom_id', '').startswith('vote_')):
                    return
                    
                # Get the option index from the custom_id
                option_index = int(interaction.data['custom_id'].split('_')[1])
                
                # Update the vote in the config
                async with self.config.guild(ctx.guild).polls() as polls:
                    if str(poll_message.id) not in polls:
                        return
                        
                    poll_data = polls[str(poll_message.id)]
                    
                    # Remove user from any existing votes
                    for opt_idx in poll_data["votes"].keys():
                        if interaction.user.id in poll_data["votes"][opt_idx]:
                            poll_data["votes"][opt_idx].remove(interaction.user.id)
                    
                    # Add user to the selected option
                    poll_data["votes"][str(option_index)].append(interaction.user.id)
                    
                    # Update the poll data
                    polls[str(poll_message.id)] = poll_data
                
                # Update the vote counters
                vote_counts = "\n".join([
                    f"{i+1}. {option}: {len(poll_data['votes'][str(i)])} votes" 
                    for i, option in enumerate(poll_data["options"])
                ])
                
                # Update the message with new vote counts
                # Since Components V2 doesn't allow editing individual components yet,
                # we need to recreate the entire view
                new_layout_view = discord.ui.LayoutView()
                new_layout_view.add_item(title_text)
                new_layout_view.add_item(duration_text)
                new_layout_view.add_item(options_container)
                new_layout_view.add_item(discord.ui.TextDisplay(vote_counts))
                
                await interaction.message.edit(view=new_layout_view)
                
                # Acknowledge the interaction
                await interaction.response.send_message(
                    f"Your vote for '{poll_data['options'][option_index]}' has been recorded!", 
                    ephemeral=True
                )
                
        except (AttributeError, ImportError):
            # Fallback for older Discord.py versions without Components V2 support
            await ctx.send(
                "This cog requires Discord.py with Components V2 support, which your bot "
                "doesn't currently have. Please update to use this feature."
            )

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
                
                # Add results to embed
                for i, option in enumerate(poll_data["options"]):
                    votes = vote_counts.get(i, 0)
                    percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
                    bar = "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
                    embed.add_field(
                        name=f"{i+1}. {option}",
                        value=f"{bar} {votes} votes ({percentage:.1f}%)",
                        inline=False
                    )
                
                if len(winners) == 1:
                    embed.description = f"**Winner: {winners[0]}** with {max_votes} votes!"
                else:
                    embed.description = f"**Tie between: {humanize_list(winners)}** with {max_votes} votes each!"
                
                embed.set_footer(text=f"Total votes: {total_votes}")
            else:
                embed.description = "No votes were cast in this poll."
            
            # Remove the poll from the active polls and config
            async with self.config.guild_from_id(guild_id).polls() as polls:
                if str(message_id) in polls:
                    del polls[str(message_id)]
            
            # Send results and update the original message
            await channel.send(
                f"The poll **{poll_data['title']}** has ended!",
                embed=embed
            )
            
            # Try to disable the buttons on the original message
            try:
                # Create a new view with disabled buttons
                layout_view = discord.ui.LayoutView()
                
                # Add poll ended text
                layout_view.add_item(discord.ui.TextDisplay(
                    f"📊 **{poll_data['title']}**\n\n**This poll has ended. See results above.**"
                ))
                
                await message.edit(view=layout_view)
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

    @commands.command()
    @commands.guild_only()
    async def quickpoll(self, ctx: commands.Context, title: str, *options):
        """Create a quick poll with default duration.
        
        Examples:
        - [p]quickpoll "Favorite color?" Red Blue Green
        - [p]quickpoll "Best movie?" "The Matrix" "Star Wars" "Inception"
        
        Arguments:
        - title: The title/question for the poll
        - options: The voting options (at least 2, maximum 10)
        """
        # Get default duration
        duration = await self.config.guild(ctx.guild).settings.default_duration()
        
        # Pass to the main poll creation command
        await ctx.invoke(self.poll_create, title=title, duration=duration, *options)

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

async def setup(bot):
    await bot.add_cog(V2Poll(bot))
