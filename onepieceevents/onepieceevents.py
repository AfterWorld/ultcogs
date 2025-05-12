# onepieceevents/onepieceevents.py
import asyncio
import discord
import datetime
import logging
from typing import Optional, Union, Dict, List
from datetime import datetime, timedelta

from redbot.core import commands, Config
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import pagify, box, humanize_list
from redbot.core.utils.predicates import MessagePredicate


class OnePieceEvents(commands.Cog):
    """A cog for managing One Piece related events in your server."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=8675309, force_registration=True
        )
        
        default_guild = {
            "events": {},  # event_id: {name, description, time, channel_id, role_id, participants, reminder_sent}
            "next_id": 1,
            "announcement_channel": None,  # Default to None, will use event creation channel
            "reminder_times": [30]  # Minutes before event to send reminders, default 30 mins
        }
        
        self.config.register_guild(**default_guild)
        self.event_check_task = self.bot.loop.create_task(self.check_events_loop())
        self.logger = logging.getLogger("red.onepieceevents")
        
        # One Piece specific event types
        self.event_types = [
            "Watch Party", 
            "Manga Discussion",
            "Theory Crafting",
            "Quiz Night",
            "Character Analysis",
            "Devil Fruit Discussion",
            "Bounty Predictions",
            "Cosplay Showcase",
            "AMV Sharing",
            "Episode Release",
            "Manga Chapter Release",
            "Other"
        ]
        
    def cog_unload(self):
        if self.event_check_task:
            self.event_check_task.cancel()
    
    @commands.group(name="events")
    @commands.guild_only()
    async def events(self, ctx):
        """Commands for managing One Piece events"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
            
    @events.command(name="create")
    @commands.mod_or_permissions(manage_events=True)
    async def events_create(self, ctx, event_type: str, name: str, time: str, *, description: str = ""):
        """Create a new One Piece event
        
        Parameters:
        - event_type: The type of event (Watch Party, Manga Discussion, etc.)
        - name: The name of the event
        - time: The time of the event in DD/MM/YYYY HH:MM format (24h)
        - description: Optional description of the event
        
        Example:
        [p]events create "Watch Party" "Whole Cake Island Arc" "15/05/2025 19:30" Join us as we watch episodes 783-800!
        """
        # Validate event type
        valid_types = [t.lower() for t in self.event_types]
        if event_type.lower() not in valid_types:
            type_list = "\n".join(self.event_types)
            return await ctx.send(f"Invalid event type. Please choose from:\n{box(type_list)}")
        
        # Parse the time
        try:
            event_time = datetime.strptime(time, "%d/%m/%Y %H:%M")
        except ValueError:
            return await ctx.send("Invalid time format. Please use DD/MM/YYYY HH:MM (24h)")
        
        if event_time < datetime.now():
            return await ctx.send("The event time can't be in the past!")
        
        # Ask for optional mention role
        await ctx.send("Would you like to ping a role for this event? (yes/no)")
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long to respond. No role will be pinged.")
        
        role_id = None
        if pred.result:
            await ctx.send("Please mention the role you'd like to ping")
            try:
                role_msg = await self.bot.wait_for(
                    "message", 
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel and len(m.role_mentions) > 0,
                    timeout=30
                )
                role_id = role_msg.role_mentions[0].id
            except asyncio.TimeoutError:
                await ctx.send("No role provided in time. No role will be pinged.")
        
        # Get the next event ID
        async with self.config.guild(ctx.guild).all() as guild_data:
            event_id = guild_data["next_id"]
            guild_data["next_id"] += 1
            
            # Create the event
            guild_data["events"][str(event_id)] = {
                "name": name,
                "type": event_type,
                "description": description,
                "time": event_time.timestamp(),
                "channel_id": ctx.channel.id,
                "role_id": role_id,
                "host_id": ctx.author.id,
                "participants": [],
                "reminder_sent": {},  # Changed to dict to track multiple reminder times
                "created_at": datetime.now().timestamp()
            }
        
        embed = await self._create_event_embed(ctx.guild, str(event_id))
        
        # Direct mention the role in the creation message if one was set
        content = ""
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                content = f"New event created! {role.mention}"
        
        msg = await ctx.send(content, embed=embed)
        
        # Add reaction for users to join
        await msg.add_reaction("🏴‍☠️")  # Pirate flag emoji
        
        # Store the message ID for later use
        async with self.config.guild(ctx.guild).all() as guild_data:
            guild_data["events"][str(event_id)]["message_id"] = msg.id
            
        await ctx.send(f"Event created with ID: {event_id}. Users can join by reacting with 🏴‍☠️ to the announcement message.")
    
    @events.command(name="list")
    async def events_list(self, ctx):
        """List all upcoming One Piece events"""
        guild_data = await self.config.guild(ctx.guild).all()
        events = guild_data.get("events", {})
        
        if not events:
            return await ctx.send("There are no upcoming events!")
        
        # Sort events by time
        sorted_events = sorted(
            events.items(), 
            key=lambda x: x[1]["time"]
        )
        
        embeds = []
        for event_id, event in sorted_events:
            if datetime.fromtimestamp(event["time"]) < datetime.now():
                continue  # Skip past events
            embed = await self._create_event_embed(ctx.guild, event_id)
            embeds.append(embed)
        
        if not embeds:
            return await ctx.send("There are no upcoming events!")
        
        await menu(ctx, embeds, DEFAULT_CONTROLS)
    
    @events.command(name="join")
    async def events_join(self, ctx, event_id: str):
        """Join an event
        
        Parameters:
        - event_id: The ID of the event to join
        """
        async with self.config.guild(ctx.guild).all() as guild_data:
            events = guild_data.get("events", {})
            if event_id not in events:
                return await ctx.send("Invalid event ID!")
            
            event = events[event_id]
            if ctx.author.id in event["participants"]:
                return await ctx.send("You've already joined this event!")
            
            event["participants"].append(ctx.author.id)
        
        await ctx.send(f"You've joined the event: **{events[event_id]['name']}**!")
        
    @events.command(name="leave")
    async def events_leave(self, ctx, event_id: str):
        """Leave an event
        
        Parameters:
        - event_id: The ID of the event to leave
        """
        async with self.config.guild(ctx.guild).all() as guild_data:
            events = guild_data.get("events", {})
            if event_id not in events:
                return await ctx.send("Invalid event ID!")
            
            event = events[event_id]
            if ctx.author.id not in event["participants"]:
                return await ctx.send("You haven't joined this event!")
            
            event["participants"].remove(ctx.author.id)
        
        await ctx.send(f"You've left the event: **{events[event_id]['name']}**!")
    
    @events.command(name="cancel")
    @commands.mod_or_permissions(manage_events=True)
    async def events_cancel(self, ctx, event_id: str):
        """Cancel an event
        
        Parameters:
        - event_id: The ID of the event to cancel
        """
        async with self.config.guild(ctx.guild).all() as guild_data:
            events = guild_data.get("events", {})
            if event_id not in events:
                return await ctx.send("Invalid event ID!")
            
            event = events[event_id]
            
            # Check if user is the host or has permissions
            if ctx.author.id != event["host_id"] and not await self.bot.is_mod(ctx.author):
                return await ctx.send("You can only cancel events that you've created!")
            
            # Get event details for notifications before removing
            event_details = event.copy()
            
            # Remove the event
            del events[event_id]
        
        await ctx.send(f"Event canceled: **{event_details['name']}**")
        
        # Notify participants
        await self._notify_participants(ctx.guild, event_details, f"The event **{event_details['name']}** has been canceled.")
    
    @events.command(name="info")
    async def events_info(self, ctx, event_id: str):
        """Get information about an event
        
        Parameters:
        - event_id: The ID of the event
        """
        guild_data = await self.config.guild(ctx.guild).all()
        events = guild_data.get("events", {})
        
        if event_id not in events:
            return await ctx.send("Invalid event ID!")
        
        embed = await self._create_event_embed(ctx.guild, event_id)
        await ctx.send(embed=embed)
    
    @events.command(name="edit")
    @commands.mod_or_permissions(manage_events=True)
    async def events_edit(self, ctx, event_id: str, field: str, *, new_value: str):
        """Edit an event
        
        Parameters:
        - event_id: The ID of the event to edit
        - field: The field to edit (name, type, description, time, role)
        - new_value: The new value for the field
        
        Example:
        [p]events edit 1 name New Event Name
        [p]events edit 1 time 20/05/2025 19:30
        [p]events edit 1 role @Nakama
        """
        async with self.config.guild(ctx.guild).all() as guild_data:
            events = guild_data.get("events", {})
            if event_id not in events:
                return await ctx.send("Invalid event ID!")
            
            event = events[event_id]
            
            # Check if user is the host or has permissions
            if ctx.author.id != event["host_id"] and not await self.bot.is_mod(ctx.author):
                return await ctx.send("You can only edit events that you've created!")
            
            field = field.lower()
            if field == "name":
                event["name"] = new_value
            elif field == "type":
                # Validate event type
                valid_types = [t.lower() for t in self.event_types]
                if new_value.lower() not in valid_types:
                    type_list = "\n".join(self.event_types)
                    return await ctx.send(f"Invalid event type. Please choose from:\n{box(type_list)}")
                event["type"] = new_value
            elif field == "description":
                event["description"] = new_value
            elif field == "time":
                try:
                    event_time = datetime.strptime(new_value, "%d/%m/%Y %H:%M")
                    if event_time < datetime.now():
                        return await ctx.send("The event time can't be in the past!")
                    event["time"] = event_time.timestamp()
                    # Reset reminder flags since time changed
                    event["reminder_sent"] = {}
                except ValueError:
                    return await ctx.send("Invalid time format. Please use DD/MM/YYYY HH:MM (24h)")
            elif field == "role":
                # Check if a role mention was provided
                if len(ctx.message.role_mentions) > 0:
                    event["role_id"] = ctx.message.role_mentions[0].id
                elif new_value.lower() == "none":
                    event["role_id"] = None
                else:
                    return await ctx.send("Please mention a role or use 'none' to remove the role ping.")
            else:
                return await ctx.send("Invalid field! Valid fields are: name, type, description, time, role")
        
        await ctx.send(f"Event updated: **{event['name']}**")
        
        # Update the event message if it exists
        if "message_id" in event:
            try:
                channel = ctx.guild.get_channel(event["channel_id"])
                if channel:
                    try:
                        message = await channel.fetch_message(event["message_id"])
                        updated_embed = await self._create_event_embed(ctx.guild, event_id)
                        await message.edit(embed=updated_embed)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        self.logger.warning(f"Could not update event message for event {event_id}")
            except Exception as e:
                self.logger.error(f"Error updating event message: {e}")
        
        # Notify participants of the change
        await self._notify_participants(ctx.guild, event, f"The event **{event['name']}** has been updated.")

    @events.group(name="config")
    @commands.admin_or_permissions(administrator=True)
    async def events_config(self, ctx):
        """Configure event settings for your server"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @events_config.command(name="channel")
    async def config_channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Set the default channel for event announcements
        
        If no channel is specified, event announcements will be sent in the same
        channel where the event is created.
        """
        if channel:
            # Test permissions
            if not channel.permissions_for(ctx.guild.me).send_messages:
                return await ctx.send(f"I don't have permission to send messages in {channel.mention}")
            
            await self.config.guild(ctx.guild).announcement_channel.set(channel.id)
            await ctx.send(f"Event announcements will now be sent in {channel.mention}.")
        else:
            await self.config.guild(ctx.guild).announcement_channel.set(None)
            await ctx.send("Event announcements will now be sent in the channel where events are created.")
    
    @events_config.command(name="reminders")
    async def config_reminders(self, ctx, *minutes: int):
        """Set when event reminders should be sent
        
        Provide one or more times (in minutes before event) when reminders should be sent.
        
        Examples:
        - `[p]events config reminders 30` - Send reminder 30 minutes before
        - `[p]events config reminders 60 30 10` - Send reminders 60, 30, and 10 minutes before
        - `[p]events config reminders` - Reset to default (30 minutes)
        """
        if not minutes:
            # Reset to default
            await self.config.guild(ctx.guild).reminder_times.set([30])
            return await ctx.send("Reset reminders to default (30 minutes before event).")
        
        # Validate minutes
        valid_minutes = []
        for m in minutes:
            if m <= 0:
                await ctx.send(f"Ignoring invalid time: {m} minutes (must be positive)")
            else:
                valid_minutes.append(m)
        
        if not valid_minutes:
            await ctx.send("No valid reminder times provided. Using default (30 minutes).")
            valid_minutes = [30]
        
        # Sort in descending order (largest first)
        valid_minutes.sort(reverse=True)
        
        await self.config.guild(ctx.guild).reminder_times.set(valid_minutes)
        await ctx.send(f"Event reminders will be sent {humanize_list([f'{m} minutes' for m in valid_minutes])} before events start.")

    @events.command(name="test")
    @commands.mod_or_permissions(manage_events=True)
    async def events_test(self, ctx, minutes: int = 5, *, role_mention: str = None):
        """Create a test event that will occur in the specified number of minutes
        
        This command is for testing event notifications to ensure they're working properly.
        
        Parameters:
        - minutes: How many minutes until the test event (default: 5)
        - role_mention: Optional role to ping (mention the role directly)
        
        Example:
        [p]events test 5 @Nakama
        """
        if minutes < 1:
            return await ctx.send("Test events must be at least 1 minute in the future.")
        
        # Calculate the event time
        event_time = datetime.now() + timedelta(minutes=minutes)
        
        # Process role mention if provided
        role_id = None
        if role_mention and ctx.message.role_mentions:
            role_id = ctx.message.role_mentions[0].id
        
        # Create a clear test event name
        test_name = f"Test Event ({ctx.author.display_name})"
        
        # Get the next event ID
        async with self.config.guild(ctx.guild).all() as guild_data:
            event_id = guild_data["next_id"]
            guild_data["next_id"] += 1
            
            # Create the event with shorter reminder times specifically for testing
            guild_data["events"][str(event_id)] = {
                "name": test_name,
                "type": "Other",
                "description": f"This is a test event created by {ctx.author.mention} that will trigger in {minutes} minutes.",
                "time": event_time.timestamp(),
                "channel_id": ctx.channel.id,
                "role_id": role_id,
                "host_id": ctx.author.id,
                "participants": [],
                "reminder_sent": {},
                "created_at": datetime.now().timestamp(),
                "is_test": True  # Flag to identify test events
            }
        
        # Create a special reminder time just for this test
        test_reminder_times = [max(1, minutes - 1)]  # 1 minute before if possible
        if minutes >= 3:
            test_reminder_times.append(2)  # Also add a 2-minute reminder if there's time
        
        # Save these reminder times temporarily
        original_reminder_times = await self.config.guild(ctx.guild).reminder_times()
        await self.config.guild(ctx.guild).reminder_times.set(test_reminder_times)
        
        # Create and send the event embed
        embed = await self._create_event_embed(ctx.guild, str(event_id))
        
        # Format the test event notification
        content = f"**TEST EVENT** created for {minutes} minutes from now"
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                content = f"{content} with {role.mention} ping"
        
        msg = await ctx.send(content, embed=embed)
        
        # Add reaction for users to join
        await msg.add_reaction("🏴‍☠️")
        
        # Store the message ID for later use
        async with self.config.guild(ctx.guild).all() as guild_data:
            guild_data["events"][str(event_id)]["message_id"] = msg.id
        
        await ctx.send(
            f"Test event created (ID: {event_id})!\n"
            f"• Will trigger in {minutes} minutes (at {event_time.strftime('%H:%M:%S')})\n"
            f"• Reminder will be sent {humanize_list([f'{m} min' for m in test_reminder_times])} before the event\n"
            f"• Once tested, test events will auto-delete after 10 minutes\n\n"
            f"Join the test event by reacting with 🏴‍☠️ to receive DM notifications."
        )
        
        # Schedule restoration of original reminder times
        self.bot.loop.create_task(self._restore_reminder_settings(ctx.guild, original_reminder_times, minutes + 10))

async def _restore_reminder_settings(self, guild, original_settings, delay_minutes):
    """Restore original reminder settings after a test"""
    await asyncio.sleep(delay_minutes * 60)
    await self.config.guild(guild).reminder_times.set(original_settings)
    
    # Clean up any test events that are still in the database
    async with self.config.guild(guild).all() as guild_data:
        # Find and remove any test events
        events_to_remove = []
        for event_id, event in guild_data["events"].items():
            if event.get("is_test", False):
                events_to_remove.append(event_id)
        
        # Remove the test events
        for event_id in events_to_remove:
            if event_id in guild_data["events"]:
                del guild_data["events"][event_id]
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reactions to event messages for joining"""
        if payload.user_id == self.bot.user.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        # Check if this is a reaction to an event message
        guild_data = await self.config.guild(guild).all()
        events = guild_data.get("events", {})
        
        for event_id, event in events.items():
            if event.get("message_id") == payload.message_id and str(payload.emoji) == "🏴‍☠️":
                # User is joining the event
                async with self.config.guild(guild).all() as updated_data:
                    if event_id in updated_data["events"]:  # Make sure event still exists
                        updated_event = updated_data["events"][event_id]
                        if payload.user_id not in updated_event["participants"]:
                            updated_event["participants"].append(payload.user_id)
                            
                            # Optionally, send a DM confirmation
                            try:
                                user = guild.get_member(payload.user_id)
                                if user:
                                    event_time = datetime.fromtimestamp(updated_event["time"])
                                    await user.send(
                                        f"You've joined the One Piece event: **{updated_event['name']}**\n"
                                        f"Event time: <t:{int(updated_event['time'])}:F>"
                                    )
                            except (discord.Forbidden, discord.HTTPException):
                                pass  # Couldn't DM
                break
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reactions to event messages for leaving"""
        if payload.user_id == self.bot.user.id:
            return
        
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        # Check if this is a reaction to an event message
        guild_data = await self.config.guild(guild).all()
        events = guild_data.get("events", {})
        
        for event_id, event in events.items():
            if event.get("message_id") == payload.message_id and str(payload.emoji) == "🏴‍☠️":
                # User is leaving the event
                async with self.config.guild(guild).all() as updated_data:
                    if event_id in updated_data["events"]:  # Make sure event still exists
                        updated_event = updated_data["events"][event_id]
                        if payload.user_id in updated_event["participants"]:
                            updated_event["participants"].remove(payload.user_id)
                            
                            # Optionally, send a DM confirmation
                            try:
                                user = guild.get_member(payload.user_id)
                                if user:
                                    await user.send(f"You've left the One Piece event: **{updated_event['name']}**")
                            except (discord.Forbidden, discord.HTTPException):
                                pass  # Couldn't DM
                break
    
    async def check_events_loop(self):
        """Loop to check for upcoming events and send reminders"""
        await self.bot.wait_until_ready()
        while self.bot is not None:
            try:
                await self._check_events()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in events loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _check_events(self):
        """Check all events and send reminders as needed"""
        for guild in self.bot.guilds:
            if await self.bot.cog_disabled_in_guild(self, guild):
                continue
                
            guild_data = await self.config.guild(guild).all()
            events = guild_data.get("events", {})
            
            for event_id, event in list(events.items()):
                event_time = datetime.fromtimestamp(event["time"])
                now = datetime.now()
                
                # Handle test events with custom reminder times if needed
                reminder_times = guild_data.get("reminder_times", [30])  # Default reminder times
                
                # For test events, use more frequent checks
                if event.get("is_test", False):
                    # For test events, check every remaining minute too
                    minutes_until = max(0, int((event_time - now).total_seconds() / 60))
                    if minutes_until <= 5:  # Only for the last 5 minutes
                        # Add every minute as a reminder time
                        for i in range(1, minutes_until + 1):
                            if i not in reminder_times:
                                reminder_times.append(i)
                
                if now > event_time:
                    # Event has passed, check if it's time to clean up
                    if now > event_time + timedelta(hours=1) or (event.get("is_test", False) and now > event_time + timedelta(minutes=10)):
                        # Clean up past event - clean up test events more quickly
                        async with self.config.guild(guild).all() as updated_data:
                            if event_id in updated_data["events"]:
                                del updated_data["events"][event_id]
                    continue
                
                # Check reminders for each reminder time
                for minutes in reminder_times:
                    reminder_key = f"reminder_{minutes}"
                    
                    # If this reminder hasn't been sent and it's time to send it
                    if (reminder_key not in event.get("reminder_sent", {}) or not event["reminder_sent"].get(reminder_key, False)) and \
                       event_time - now <= timedelta(minutes=minutes) and \
                       event_time > now:
                        
                        # Send the reminder
                        sent = await self._send_reminder(guild, event_id, event, minutes)
                        
                        if sent:
                            # Mark reminder as sent
                            async with self.config.guild(guild).all() as updated_data:
                                if event_id in updated_data["events"]:
                                    if "reminder_sent" not in updated_data["events"][event_id]:
                                        updated_data["events"][event_id]["reminder_sent"] = {}
                                    updated_data["events"][event_id]["reminder_sent"][reminder_key] = True
    
    async def _send_reminder(self, guild, event_id, event, minutes_before):
        """Send a reminder for an upcoming event"""
        try:
            channel = guild.get_channel(event["channel_id"])
            if not channel:
                # Try the default announcement channel if set
                announcement_channel_id = await self.config.guild(guild).announcement_channel()
                if announcement_channel_id:
                    channel = guild.get_channel(announcement_channel_id)
            
            if not channel:
                self.logger.warning(f"Could not find channel for event {event_id} in guild {guild.id}")
                return False
            
            embed = await self._create_event_embed(guild, event_id)
            
            # Add the reminder message
            minutes_left = int((datetime.fromtimestamp(event["time"]) - datetime.now()).total_seconds() / 60)
            time_str = f"{minutes_left} minutes" if minutes_left != 1 else "1 minute"
            
            if minutes_left <= 0:
                reminder_msg = f"⏰ **EVENT STARTING NOW** ⏰\n**{event['name']}** is starting now!"
            else:
                reminder_msg = f"⏰ **EVENT REMINDER** ⏰\n**{event['name']}** is starting in approximately {time_str}!"
            
            # Create a different message for the actual event start
            if minutes_left <= 1:
                embed.set_author(name="📣 EVENT STARTING NOW 📣")
                embed.color = discord.Color.red()  # Make it stand out
            
            # Create content with role ping if applicable
            content = reminder_msg
            if event["role_id"]:
                role = guild.get_role(event["role_id"])
                if role:
                    content = f"{role.mention}\n{reminder_msg}"
            
            # Send the reminder
            message = await channel.send(content, embed=embed)
            
            # If this is the start reminder, add the reaction
            if minutes_left <= 1:
                await message.add_reaction("🏴‍☠️")
            
            # Also send DMs to participants
            if minutes_left <= 1:
                notification_msg = f"⏰ The event **{event['name']}** is starting now!"
            else:
                notification_msg = f"⏰ Reminder: The event **{event['name']}** is starting in approximately {time_str}!"
                
            await self._notify_participants(guild, event, notification_msg)
            
            return True
        except Exception as e:
            self.logger.error(f"Error sending event reminder: {e}", exc_info=True)
            return False
    
    async def _notify_participants(self, guild, event, message):
        """Send a DM to all participants of an event"""
        for user_id in event["participants"]:
            user = guild.get_member(user_id)
            if user:
                try:
                    embed = discord.Embed(
                        title=f"One Piece Event: {event['name']}",
                        description=message,
                        color=discord.Color.blue()
                    )
                    
                    # Add event time to the notification
                    if "time" in event:
                        embed.add_field(
                            name="Event Time", 
                            value=f"<t:{int(event['time'])}:F>", 
                            inline=False
                        )
                        
                    # Add a footer with the event type
                    if "type" in event:
                        embed.set_footer(text=f"Event Type: {event['type']}")
                    
                    await user.send(embed=embed)
                except (discord.Forbidden, discord.HTTPException) as e:
                    self.logger.warning(f"Could not send DM to user {user_id}: {e}")
    
    async def _create_event_embed(self, guild, event_id):
        """Create an embed for an event"""
        guild_data = await self.config.guild(guild).all()
        events = guild_data.get("events", {})
        
        if event_id not in events:
            return None
        
        event = events[event_id]
        event_time = datetime.fromtimestamp(event["time"])
        
        # Get the host name
        host = guild.get_member(event["host_id"])
        host_name = host.display_name if host else "Unknown"
        
        # Create participant list
        participant_count = len(event["participants"])
        participant_names = []
        for user_id in event["participants"]:
            member = guild.get_member(user_id)
            if member:
                participant_names.append(member.display_name)
        
        # Determine the event color based on type
        colors = {
            "watch party": discord.Color.blue(),
            "manga discussion": discord.Color.red(),
            "theory crafting": discord.Color.purple(),
            "quiz night": discord.Color.gold(),
            "character analysis": discord.Color.green(),
            "devil fruit discussion": discord.Color.orange(),
            "bounty predictions": discord.Color.from_rgb(165, 42, 42),  # Brown
            "cosplay showcase": discord.Color.magenta(),
            "amv sharing": discord.Color.teal(),
            "episode release": discord.Color.blue(),
            "manga chapter release": discord.Color.dark_red(),
            "other": discord.Color.light_grey()
        }
        
        color = colors.get(event["type"].lower(), discord.Color.default())
        
        # Create the embed
        embed = discord.Embed(
            title=f"📅 {event['name']}",
            description=event["description"] or "No description provided.",
            color=color,
            timestamp=event_time
        )
        
        # Add fields
        embed.add_field(name="Event ID", value=event_id, inline=True)
        embed.add_field(name="Type", value=event["type"], inline=True)
        embed.add_field(name="Time", value=f"<t:{int(event['time'])}:F>", inline=False)
        embed.add_field(name="Host", value=host_name, inline=True)
        
        # Add role information if available
        if event["role_id"]:
            role = guild.get_role(event["role_id"])
            if role:
                embed.add_field(name="Ping Role", value=role.mention, inline=True)
        
        if participant_count > 0:
            participants_text = f"{participant_count} {'person' if participant_count == 1 else 'people'} attending"
            if participant_names:
                participants_preview = participant_names[:5]
                remaining = participant_count - len(participants_preview)
                if remaining > 0:
                    participants_text += f"\n{humanize_list(participants_preview)} and {remaining} more"
                else:
                    participants_text += f"\n{humanize_list(participants_preview)}"
            embed.add_field(name="Participants", value=participants_text, inline=False)
        else:
            embed.add_field(name="Participants", value="No participants yet. Be the first to join!", inline=False)
        
        # Figure out the time remaining
        now = datetime.now()
        if event_time > now:
            time_until = event_time - now
            days = time_until.days
            hours, remainder = divmod(time_until.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            time_str = ""
            if days > 0:
                time_str += f"{days} {'day' if days == 1 else 'days'}, "
            if hours > 0 or days > 0:
                time_str += f"{hours} {'hour' if hours == 1 else 'hours'}, "
            time_str += f"{minutes} {'minute' if minutes == 1 else 'minutes'}"
            
            embed.add_field(name="Time Until Event", value=time_str, inline=False)
        
        # Add footer
        embed.set_footer(text=f"React with 🏴‍☠️ to join | ID: {event_id}")
        
        # Add One Piece themed thumbnail based on event type
        thumbnails = {
            "watch party": "https://i.imgur.com/pbVXkY0.jpeg",  # TV
            "manga discussion": "https://i.imgur.com/uFrvXbS.png",  # Manga panel
            "theory crafting": "https://media1.tenor.com/m/gD9lMFUMUUIAAAAd/luffy-one-piece.gif",  # Luffy thinking
            "quiz night": "https://upload.wikimedia.org/wikipedia/commons/5/5a/Black_question_mark.png",  # Question mark
            "character analysis": "https://i.ytimg.com/vi/ewu9PE1xOM0/maxresdefault.jpg",  # Character lineup
            "devil fruit discussion": "https://media1.tenor.com/m/6yjxOCSrfQYAAAAd/gomu-gomu-no-mi.gif",  # Devil fruit
            "bounty predictions": "https://media1.tenor.com/m/9scKYAkUeY0AAAAC/brook.gif",  # Wanted poster
            "cosplay showcase": "https://media1.tenor.com/m/pI82pBBUI5MAAAAC/deadpool-joke.gif",  # Cosplay
            "amv sharing": "https://media1.tenor.com/m/xU5o4oSq-aIAAAAC/cop-watch-camera-man.gif",  # Video camera
            "episode release": "https://media1.tenor.com/m/6J6UfzLqvRAAAAAC/one-piece-killer.gif",  # Episode screenshot
            "manga chapter release": "https://static.wikia.nocookie.net/onepiece/images/c/c6/Volume_100.png/revision/latest?cb=20210903160940",  # Manga cover
            "other": "https://www.pngall.com/wp-content/uploads/13/One-Piece-Logo-PNG-Photo.png"  # One Piece logo
        }
        
        thumbnail_url = thumbnails.get(event["type"].lower(), "https://i.imgur.com/q4JDmZl.png")
        embed.set_thumbnail(url=thumbnail_url)
        
        return embed
