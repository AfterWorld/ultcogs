# onepiece_events/onepiece_events.py
import asyncio
import discord
import datetime
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
        }
        
        self.config.register_guild(**default_guild)
        self.event_check_task = self.bot.loop.create_task(self.check_events_loop())
        
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
                "reminder_sent": False
            }
        
        embed = await self._create_event_embed(ctx.guild, str(event_id))
        msg = await ctx.send("Event created!", embed=embed)
        
        # Add reaction for users to join
        await msg.add_reaction("🏴‍☠️")  # Pirate flag emoji
        
        # Store the message ID for later use
        async with self.config.guild(ctx.guild).all() as guild_data:
            guild_data["events"][str(event_id)]["message_id"] = msg.id
    
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
            
            # Remove the event
            del events[event_id]
        
        await ctx.send(f"Event canceled: **{event['name']}**")
        
        # Notify participants
        await self._notify_participants(ctx.guild, event, f"The event **{event['name']}** has been canceled.")
    
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
        - field: The field to edit (name, type, description, time)
        - new_value: The new value for the field
        
        Example:
        [p]events edit 1 name New Event Name
        [p]events edit 1 time 20/05/2025 19:30
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
                except ValueError:
                    return await ctx.send("Invalid time format. Please use DD/MM/YYYY HH:MM (24h)")
            else:
                return await ctx.send("Invalid field! Valid fields are: name, type, description, time")
        
        await ctx.send(f"Event updated: **{event['name']}**")
        
        # Notify participants of the change
        await self._notify_participants(ctx.guild, event, f"The event **{event['name']}** has been updated.")
    
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
                    updated_event = updated_data["events"][event_id]
                    if payload.user_id not in updated_event["participants"]:
                        updated_event["participants"].append(payload.user_id)
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
                    updated_event = updated_data["events"][event_id]
                    if payload.user_id in updated_event["participants"]:
                        updated_event["participants"].remove(payload.user_id)
                break
    
    async def check_events_loop(self):
        """Loop to check for upcoming events and send reminders"""
        await self.bot.wait_until_ready()
        while self.bot is not None:
            try:
                await self._check_events()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Error in events loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_events(self):
        """Check all events and send reminders as needed"""
        for guild in self.bot.guilds:
            guild_data = await self.config.guild(guild).all()
            events = guild_data.get("events", {})
            
            for event_id, event in list(events.items()):
                event_time = datetime.fromtimestamp(event["time"])
                now = datetime.now()
                
                # Send a reminder 30 minutes before the event
                if not event["reminder_sent"] and event_time - now <= timedelta(minutes=30) and event_time > now:
                    await self._send_reminder(guild, event_id, event)
                    async with self.config.guild(guild).all() as updated_data:
                        updated_data["events"][event_id]["reminder_sent"] = True
                
                # Clean up past events (1 hour after they're done)
                if event_time + timedelta(hours=1) < now:
                    async with self.config.guild(guild).all() as updated_data:
                        if event_id in updated_data["events"]:
                            del updated_data["events"][event_id]
    
    async def _send_reminder(self, guild, event_id, event):
        """Send a reminder for an upcoming event"""
        channel = guild.get_channel(event["channel_id"])
        if not channel:
            return
        
        embed = await self._create_event_embed(guild, event_id)
        
        # Add the reminder message
        minutes_left = int((datetime.fromtimestamp(event["time"]) - datetime.now()).total_seconds() / 60)
        reminder_msg = f"⏰ **EVENT REMINDER** ⏰\nThe event is starting in approximately {minutes_left} minutes!"
        
        # Ping role if set
        content = reminder_msg
        if event["role_id"]:
            role = guild.get_role(event["role_id"])
            if role:
                content = f"{role.mention}\n{reminder_msg}"
        
        await channel.send(content, embed=embed)
        
        # Also send DMs to participants
        await self._notify_participants(guild, event, f"⏰ Reminder: The event **{event['name']}** is starting in approximately {minutes_left} minutes!")
    
    async def _notify_participants(self, guild, event, message):
        """Send a DM to all participants of an event"""
        for user_id in event["participants"]:
            user = guild.get_member(user_id)
            if user:
                try:
                    await user.send(message)
                except discord.Forbidden:
                    pass  # Can't send DM
    
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
            "watch party": "https://i.imgur.com/JfkJyLf.png",  # TV
            "manga discussion": "https://i.imgur.com/hLkWPLS.png",  # Manga panel
            "theory crafting": "https://i.imgur.com/QJcyO1K.png",  # Luffy thinking
            "quiz night": "https://i.imgur.com/jzEfRE9.png",  # Question mark
            "character analysis": "https://i.imgur.com/iBT1rhR.png",  # Character lineup
            "devil fruit discussion": "https://i.imgur.com/1KRgQ0i.png",  # Devil fruit
            "bounty predictions": "https://i.imgur.com/pTpnz7G.png",  # Wanted poster
            "cosplay showcase": "https://i.imgur.com/Jj9jWVX.png",  # Cosplay
            "amv sharing": "https://i.imgur.com/PnUTHtv.png",  # Video camera
            "episode release": "https://i.imgur.com/Qj0mSOg.png",  # Episode screenshot
            "manga chapter release": "https://i.imgur.com/n2MtHNe.png",  # Manga cover
            "other": "https://i.imgur.com/q4JDmZl.png"  # One Piece logo
        }
        
        thumbnail_url = thumbnails.get(event["type"].lower(), "https://i.imgur.com/q4JDmZl.png")
        embed.set_thumbnail(url=thumbnail_url)
        
        return embed
