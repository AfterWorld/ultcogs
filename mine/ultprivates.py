import discord
from redbot.core import commands, checks, Config
import asyncio
import json
import re

class UltPrivates(commands.Cog):
    """Special commands for VIP users with multiple fun entrance effects."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=161183456896876544)
        
        default_guild = {
            "authorized_users": [161183456896876544],
            "entrance_delay": 3.5,
            "custom_entrances": {},     # Old structure - kept for backward compatibility
            "trigger_phrases": {},      # Old structure - kept for backward compatibility
            "embed_settings": {},       # Old structure - kept for backward compatibility
            "user_entrances": {},       # New structure to hold multiple entrances per user
            "default_entrance_id": {},  # Store which entrance is the default for each user
            "migration_completed": False # Flag to track if data migration has happened
        }
        
        self.config.register_guild(**default_guild)
        
    async def migrate_old_data(self, guild):
        """Migrate data from old format to new format."""
        # Check if migration has already been completed
        if await self.config.guild(guild).migration_completed():
            return
            
        # Get old data
        custom_entrances = await self.config.guild(guild).custom_entrances()
        trigger_phrases = await self.config.guild(guild).trigger_phrases()
        embed_settings = await self.config.guild(guild).embed_settings()
        
        # Initialize new data structure
        user_entrances = await self.config.guild(guild).user_entrances()
        default_entrance_id = await self.config.guild(guild).default_entrance_id()
        
        # Migrate each user's data
        for user_id, messages in custom_entrances.items():
            # Skip if user already has entrances in the new format
            if user_id in user_entrances:
                continue
                
            # Initialize user in new format
            if user_id not in user_entrances:
                user_entrances[user_id] = {}
                
            # Create default entrance with old data
            user_entrances[user_id]["default"] = {
                "messages": messages,
                "trigger_phrases": trigger_phrases.get(user_id, []),
                "embed_settings": embed_settings.get(user_id, {
                    "title": "👑 A Top Panda Has Arrived! 👑",
                    "color": discord.Color.gold().value,
                    "footer": "All hail the wisdom of the ages!",
                    "thumbnail": None,
                    "image": None
                })
            }
            
            # Set as default entrance
            default_entrance_id[user_id] = "default"
        
        # Save new data
        await self.config.guild(guild).user_entrances.set(user_entrances)
        await self.config.guild(guild).default_entrance_id.set(default_entrance_id)
        
        # Mark migration as completed
        await self.config.guild(guild).migration_completed.set(True)
        
    async def is_authorized(self, guild_id, user_id):
        """Check if a user is authorized to use these commands."""
        if user_id == self.bot.owner_id:
            return True
            
        auth_users = await self.config.guild(self.bot.get_guild(guild_id)).authorized_users()
        return user_id in auth_users
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for trigger phrases in messages."""
        # Ignore bot messages or DMs
        if message.author.bot or not message.guild:
            return
        
        # Ensure old data is migrated
        await self.migrate_old_data(message.guild)
        
        # Check authorization first
        if not await self.is_authorized(message.guild.id, message.author.id):
            return
            
        content = message.content.lower()
        user_id_str = str(message.author.id)
        
        # Check for skadoosh
        if "skadoosh" in content:
            await self.skadoosh(message)
            return
            
        # Check for default entrance phrase
        if "i have arrived" in content:
            # Get default entrance ID for this user
            default_ids = await self.config.guild(message.guild).default_entrance_id()
            default_entrance_id = default_ids.get(user_id_str, "default")
            
            await self.grand_entrance(message, entrance_id=default_entrance_id)
            return
        
        # Check for all user entrances and their trigger phrases
        user_entrances = await self.config.guild(message.guild).user_entrances()
        
        if user_id_str in user_entrances:
            entrances = user_entrances[user_id_str]
            
            # Check each entrance's trigger phrases
            for entrance_id, entrance_data in entrances.items():
                trigger_phrases = entrance_data.get("trigger_phrases", [])
                
                for phrase in trigger_phrases:
                    if phrase.lower() in content:
                        await self.grand_entrance(message, entrance_id=entrance_id)
                        return

    async def skadoosh(self, message):
        """
        Delete recent messages and play the Skadoosh gif from Kung Fu Panda.
        This creates a dramatic effect of "removing" previous messages.
        """
        try:
            # Delete the triggering message
            await message.delete()
            
            # Delete the last 5 messages from the user
            def is_user(m):
                return m.author == message.author
            
            deleted = await message.channel.purge(limit=5, check=is_user)
            
            # Send the GIF
            gif_url = "https://media1.tenor.com/m/GXRZ4wDvg_8AAAAd/kung-fu-panda-skadoosh.gif"
            await message.channel.send(gif_url)
            
        except discord.Forbidden:
            await message.channel.send("I need proper permissions to delete messages!")
        except Exception as e:
            await message.channel.send(f"Error executing skadoosh: {str(e)}")
    
    async def grand_entrance(self, message, entrance_id="default"):
        """
        Make a grand entrance announcement with cycling messages.
        Creates a dramatic effect for VIP users entering a channel.
        
        Parameters:
        message (discord.Message): The message that triggered the entrance
        entrance_id (str): The ID of the specific entrance to use
        """
        try:
            # Delete the triggering message
            await message.delete()
            
            # Get user entrances
            user_entrances = await self.config.guild(message.guild).user_entrances()
            user_id_str = str(message.author.id)
            
            # Default entrance messages and settings if nothing custom is set
            entrance_messages = [
                "🌟 Silence, mortals! A Panda has graced this chat with their presence! 🌟",
                "⚡️ Tremble, for the wisdom of the ages has entered the server! ⚡️",
                "🌪 The winds of change blow as a Top Panda steps into our midst! 🌪",
                "🔥 Behold! The very foundation of the World Government now walks among us! 🔥",
                "🌊 As the tides are governed by the moon, so too is this server now under the watchful eye of the main Panda! 🌊"
            ]
            
            # Default embed settings
            embed_title = "👑 A Top Panda Has Arrived! 👑"
            embed_color = discord.Color.gold()
            embed_footer = "All hail the wisdom of the ages!"
            embed_image = None
            embed_thumbnail = None
            
            # Get custom entrance if available
            if user_id_str in user_entrances:
                user_entrance_data = user_entrances[user_id_str]
                
                # If the specified entrance_id exists for this user, use it
                if entrance_id in user_entrance_data:
                    entrance_data = user_entrance_data[entrance_id]
                    
                    # Get entrance messages for this specific entrance
                    entrance_messages = entrance_data.get("messages", entrance_messages)
                    
                    # Get embed settings for this specific entrance
                    embed_settings = entrance_data.get("embed_settings", {})
                    embed_title = embed_settings.get("title", embed_title)
                    embed_color = discord.Color(embed_settings.get("color", embed_color.value))
                    embed_footer = embed_settings.get("footer", embed_footer)
                    embed_image = embed_settings.get("image", embed_image)
                    embed_thumbnail = embed_settings.get("thumbnail", embed_thumbnail)
            
            # Safely get avatar URL if it exists
            if not embed_thumbnail and message.author.avatar:
                embed_thumbnail = message.author.avatar.url
            
            # Get entrance delay
            delay = await self.config.guild(message.guild).entrance_delay()
            
            # Create initial embed
            embed = discord.Embed(
                title=embed_title,
                description=entrance_messages[0],
                color=embed_color
            )
            
            # Add thumbnail if available
            if embed_thumbnail:
                embed.set_thumbnail(url=embed_thumbnail)
                
            # Add image if available
            if embed_image:
                embed.set_image(url=embed_image)
                
            embed.set_footer(text=embed_footer)
            
            # Send initial message
            entrance_msg = await message.channel.send(embed=embed)
            
            # Cycle through entrance messages with improved timing
            for msg in entrance_messages[1:]:
                await asyncio.sleep(delay)  # Use configured delay
                embed.description = msg
                await entrance_msg.edit(embed=embed)
                
        except discord.Forbidden:
            await message.channel.send("I need proper permissions to manage messages!")
        except Exception as e:
            await message.channel.send(f"Error executing grand entrance: {str(e)}")

    @commands.command(name="setdelay")
    async def set_entrance_delay(self, ctx, seconds: float):
        """
        Set the delay between entrance messages.
        
        Usage:
        [p]setdelay 3.5
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        if seconds < 1.0 or seconds > 10.0:
            return await ctx.send("Delay must be between 1 and 10 seconds.")
            
        await self.config.guild(ctx.guild).entrance_delay.set(seconds)
        await ctx.send(f"Entrance message delay set to {seconds} seconds.")
        
    @commands.command(name="addauth")
    async def add_authorized_user(self, ctx, user_id: int):
        """
        Add a user to the authorized users list.
        Only the bot owner or authorized users can use this command.
        
        Usage:
        [p]addauth 123456789012345678
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        auth_users = await self.config.guild(ctx.guild).authorized_users()
        if user_id in auth_users:
            return await ctx.send("This user is already authorized.")
            
        auth_users.append(user_id)
        await self.config.guild(ctx.guild).authorized_users.set(auth_users)
        await ctx.send(f"User ID {user_id} added to authorized users.")
        
    @commands.command(name="removeauth")
    async def remove_authorized_user(self, ctx, user_id: int):
        """
        Remove a user from the authorized users list.
        Only the bot owner or authorized users can use this command.
        
        Usage:
        [p]removeauth 123456789012345678
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        auth_users = await self.config.guild(ctx.guild).authorized_users()
        if user_id not in auth_users:
            return await ctx.send("This user is not in the authorized list.")
            
        auth_users.remove(user_id)
        await self.config.guild(ctx.guild).authorized_users.set(auth_users)
        await ctx.send(f"User ID {user_id} removed from authorized users.")
    
    @commands.command(name="listauth")
    async def list_authorized(self, ctx):
        """List all authorized users."""
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        auth_users = await self.config.guild(ctx.guild).authorized_users()
        
        if not auth_users:
            return await ctx.send("No authorized users found.")
            
        user_list = "\n".join([f"• <@{user_id}> (`{user_id}`)" for user_id in auth_users])
        
        embed = discord.Embed(
            title="Authorized Users",
            description=user_list,
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="createentrance")
    async def create_entrance(self, ctx, entrance_name: str, *, messages=None):
        """
        Create a new entrance with a custom name.
        Separate messages with | character.
        
        Usage:
        [p]createentrance royal First message! | Second message! | Final message!
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
        
        # Ensure old data is migrated
        await self.migrate_old_data(ctx.guild)
        
        user_id_str = str(ctx.author.id)
        
        # Check if this user already has the maximum number of entrances
        user_entrances = await self.config.guild(ctx.guild).user_entrances()
        
        # Initialize user entrances if not exists
        if user_id_str not in user_entrances:
            user_entrances[user_id_str] = {}
        
        # Check entrance limit (max 5 entrances per user)
        if len(user_entrances[user_id_str]) >= 5 and entrance_name not in user_entrances[user_id_str]:
            return await ctx.send("You've reached the maximum limit of 5 entrances. Delete one before creating more.")
        
        # Validate entrance name (alphanumeric with no spaces)
        if not re.match(r'^[a-zA-Z0-9_-]+$', entrance_name):
            return await ctx.send("Entrance name must be alphanumeric with no spaces. You can use underscores and hyphens.")
            
        # If no messages provided, show current messages for this entrance
        if messages is None:
            if entrance_name in user_entrances[user_id_str]:
                entrance_data = user_entrances[user_id_str][entrance_name]
                msg_list = entrance_data.get("messages", [])
                formatted_msgs = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(msg_list)])
                return await ctx.send(f"Current messages for entrance '{entrance_name}':\n{formatted_msgs}")
            else:
                return await ctx.send(f"No entrance with name '{entrance_name}' exists.")
        
        # Parse messages (split by |)
        msg_list = [msg.strip() for msg in messages.split("|")]
        
        if len(msg_list) < 2:
            return await ctx.send("Please provide at least 2 messages separated by | character.")
        
        # Create or update the entrance
        if entrance_name not in user_entrances[user_id_str]:
            # Create new entrance with default settings
            user_entrances[user_id_str][entrance_name] = {
                "messages": msg_list,
                "trigger_phrases": [],
                "embed_settings": {
                    "title": "👑 A Top Panda Has Arrived! 👑",
                    "color": discord.Color.gold().value,
                    "footer": "All hail the wisdom of the ages!",
                    "thumbnail": None,
                    "image": None
                }
            }
        else:
            # Update existing entrance's messages
            user_entrances[user_id_str][entrance_name]["messages"] = msg_list
        
        # Save to config
        await self.config.guild(ctx.guild).user_entrances.set(user_entrances)
        
        # If this is the user's first entrance, set it as default
        default_ids = await self.config.guild(ctx.guild).default_entrance_id()
        if user_id_str not in default_ids:
            default_ids[user_id_str] = entrance_name
            await self.config.guild(ctx.guild).default_entrance_id.set(default_ids)
            await ctx.send(f"Entrance '{entrance_name}' created and set as your default!")
        else:
            await ctx.send(f"Entrance '{entrance_name}' has been created/updated!")
    
    @commands.command(name="deleteentrance")
    async def delete_entrance(self, ctx, entrance_name: str):
        """
        Delete a custom entrance.
        
        Usage:
        [p]deleteentrance royal
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
        
        # Ensure old data is migrated
        await self.migrate_old_data(ctx.guild)
        
        user_id_str = str(ctx.author.id)
        user_entrances = await self.config.guild(ctx.guild).user_entrances()
        
        # Check if user has any entrances
        if user_id_str not in user_entrances:
            return await ctx.send("You don't have any custom entrances.")
        
        # Check if the specified entrance exists
        if entrance_name not in user_entrances[user_id_str]:
            return await ctx.send(f"No entrance named '{entrance_name}' found.")
        
        # Delete the entrance
        del user_entrances[user_id_str][entrance_name]
        
        # If this was the default entrance, reset default if other entrances exist
        default_ids = await self.config.guild(ctx.guild).default_entrance_id()
        if default_ids.get(user_id_str) == entrance_name:
            # If user has other entrances, set the first one as default
            if user_entrances[user_id_str]:
                new_default = list(user_entrances[user_id_str].keys())[0]
                default_ids[user_id_str] = new_default
                await ctx.send(f"Your default entrance was deleted. '{new_default}' is now your default entrance.")
            else:
                # No entrances left, remove default setting
                del default_ids[user_id_str]
                await ctx.send("Your default entrance was deleted. You have no more custom entrances.")
            
            await self.config.guild(ctx.guild).default_entrance_id.set(default_ids)
        else:
            await ctx.send(f"Entrance '{entrance_name}' has been deleted.")
        
        # Save changes
        await self.config.guild(ctx.guild).user_entrances.set(user_entrances)
    
    @commands.command(name="listentrances")
    async def list_entrances(self, ctx):
        """
        List all your custom entrances.
        
        Usage:
        [p]listentrances
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
        
        # Ensure old data is migrated
        await self.migrate_old_data(ctx.guild)
        
        user_id_str = str(ctx.author.id)
        user_entrances = await self.config.guild(ctx.guild).user_entrances()
        default_ids = await self.config.guild(ctx.guild).default_entrance_id()
        
        # Check if user has any entrances
        if user_id_str not in user_entrances or not user_entrances[user_id_str]:
            return await ctx.send("You don't have any custom entrances.")
        
        default_entrance = default_ids.get(user_id_str, None)
        
        # Create embed to display entrances
        embed = discord.Embed(
            title="Your Custom Entrances",
            description=f"You have {len(user_entrances[user_id_str])}/5 entrances configured.",
            color=discord.Color.blue()
        )
        
        for entrance_name, entrance_data in user_entrances[user_id_str].items():
            # Mark default entrance with a star
            name_display = f"⭐ {entrance_name}" if entrance_name == default_entrance else entrance_name
            
            # Get message count and trigger phrases
            msg_count = len(entrance_data.get("messages", []))
            trigger_count = len(entrance_data.get("trigger_phrases", []))
            
            value = f"Messages: {msg_count}\nTrigger phrases: {trigger_count}"
            if entrance_name == default_entrance:
                value += "\n**This is your default entrance**"
                
            embed.add_field(name=name_display, value=value, inline=False)
        
        # Add help text
        embed.set_footer(text="Use [p]entranceinfo [name] to see details for a specific entrance")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="entranceinfo")
    async def entrance_info(self, ctx, entrance_name: str):
        """
        Show detailed information about a specific entrance.
        
        Usage:
        [p]entranceinfo royal
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
        
        # Ensure old data is migrated
        await self.migrate_old_data(ctx.guild)
        
        user_id_str = str(ctx.author.id)
        user_entrances = await self.config.guild(ctx.guild).user_entrances()
        
        # Check if this entrance exists
        if (user_id_str not in user_entrances or 
            entrance_name not in user_entrances[user_id_str]):
            return await ctx.send(f"No entrance named '{entrance_name}' found.")
        
        entrance_data = user_entrances[user_id_str][entrance_name]
        
        # Create embed with entrance details
        embed = discord.Embed(
            title=f"Entrance: {entrance_name}",
            color=discord.Color.blue()
        )
        
        # Messages
        messages = entrance_data.get("messages", [])
        message_text = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(messages)])
        embed.add_field(name="Messages", value=message_text or "No messages set", inline=False)
        
        # Trigger phrases
        triggers = entrance_data.get("trigger_phrases", [])
        trigger_text = "\n".join([f"• {trigger}" for trigger in triggers]) if triggers else "No trigger phrases set"
        embed.add_field(name="Trigger Phrases", value=trigger_text, inline=False)
        
        # Embed settings
        embed_settings = entrance_data.get("embed_settings", {})
        
        settings_text = []
        if "title" in embed_settings:
            settings_text.append(f"Title: {embed_settings['title']}")
        
        if "color" in embed_settings:
            color_hex = f"#{embed_settings['color']:06x}"
            settings_text.append(f"Color: {color_hex}")
            
        if "footer" in embed_settings:
            settings_text.append(f"Footer: {embed_settings['footer']}")
            
        if "thumbnail" in embed_settings and embed_settings["thumbnail"]:
            settings_text.append(f"Thumbnail: Set")
            
        if "image" in embed_settings and embed_settings["image"]:
            settings_text.append(f"Image: Set")
            
        embed.add_field(
            name="Embed Settings", 
            value="\n".join(settings_text) or "Default settings", 
            inline=False
        )
        
        # Show if this is the default entrance
        default_ids = await self.config.guild(ctx.guild).default_entrance_id()
        if default_ids.get(user_id_str) == entrance_name:
            embed.add_field(name="Default", value="✅ This is your default entrance", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="setdefault")
    async def set_default_entrance(self, ctx, entrance_name: str):
        """
        Set a specific entrance as your default.
        
        Usage:
        [p]setdefault royal
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
        
        # Ensure old data is migrated
        await self.migrate_old_data(ctx.guild)
        
        user_id_str = str(ctx.author.id)
        user_entrances = await self.config.guild(ctx.guild).user_entrances()
        
        # Check if this entrance exists
        if (user_id_str not in user_entrances or 
            entrance_name not in user_entrances[user_id_str]):
            return await ctx.send(f"No entrance named '{entrance_name}' found.")
        
        # Set as default
        default_ids = await self.config.guild(ctx.guild).default_entrance_id()
        default_ids[user_id_str] = entrance_name
        await self.config.guild(ctx.guild).default_entrance_id.set(default_ids)
        
        await ctx.send(f"'{entrance_name}' is now your default entrance!")

    @commands.command(name="settriggers")
    async def set_entrance_triggers(self, ctx, entrance_name: str, *, phrases=None):
        """
        Set trigger phrases for a specific entrance.
        Separate phrases with | character.
        
        Usage:
        [p]settriggers royal The king is here | All hail the king | Bow to royalty
        [p]settriggers royal - Shows current triggers
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
        
        # Ensure old data is migrated
        await self.migrate_old_data(ctx.guild)
        
        user_id_str = str(ctx.author.id)
        user_entrances = await self.config.guild(ctx.guild).user_entrances()
        
        # Check if this entrance exists
        if (user_id_str not in user_entrances or 
            entrance_name not in user_entrances[user_id_str]):
            return await ctx.send(f"No entrance named '{entrance_name}' found.")
        
        # If no phrases provided, show current phrases
        if phrases is None:
            trigger_phrases = user_entrances[user_id_str][entrance_name].get("trigger_phrases", [])
            
            if trigger_phrases:
                formatted_phrases = "\n".join([f"{i+1}. {phrase}" for i, phrase in enumerate(trigger_phrases)])
                return await ctx.send(f"Current trigger phrases for '{entrance_name}':\n{formatted_phrases}")
            else:
                return await ctx.send(f"No trigger phrases set for '{entrance_name}'.")
        
        # Parse phrases (split by |)
        phrase_list = [phrase.strip() for phrase in phrases.split("|")]
        
        if len(phrase_list) < 1:
            return await ctx.send("Please provide at least 1 trigger phrase.")
        
        # Check for trigger phrase conflicts with other entrances
        has_conflicts = False
        conflict_phrases = []
        
        for phrase in phrase_list:
            phrase_lower = phrase.lower()
            
            # Check against other entrances for this user
            for other_entrance, entrance_data in user_entrances[user_id_str].items():
                if other_entrance == entrance_name:
                    continue  # Skip the current entrance
                    
                other_triggers = [t.lower() for t in entrance_data.get("trigger_phrases", [])]
                
                if phrase_lower in other_triggers:
                    has_conflicts = True
                    conflict_phrases.append(f"'{phrase}' conflicts with entrance '{other_entrance}'")
        
        if has_conflicts:
            conflict_msg = "\n".join(conflict_phrases)
            return await ctx.send(f"Trigger phrase conflicts detected:\n{conflict_msg}\n\nPlease resolve conflicts and try again.")
            
        # Save trigger phrases
        user_entrances[user_id_str][entrance_name]["trigger_phrases"] = phrase_list
        await self.config.guild(ctx.guild).user_entrances.set(user_entrances)
        
        await ctx.send(f"Trigger phrases for '{entrance_name}' have been updated!")

    @commands.command(name="setembed")
    async def set_embed_style(self, ctx, entrance_name: str, setting=None, *, value=None):
        """
        Customize the embed for a specific entrance.
        
        Settings:
        - title: Set the embed title
        - color: Set the embed color (hex code)
        - footer: Set the embed footer text
        - thumbnail: Set the thumbnail image URL
        - image: Set the main image URL
        - reset: Reset to defaults
        
        Usage:
        [p]setembed royal title My Royal Entrance
        [p]setembed royal color #FF5733
        [p]setembed royal footer Bow before me!
        [p]setembed royal thumbnail https://example.com/image.png
        [p]setembed royal image https://example.com/banner.gif
        [p]setembed royal reset
        [p]setembed royal - Shows current settings
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
        
        # Ensure old data is migrated
        await self.migrate_old_data(ctx.guild)
        
        user_id_str = str(ctx.author.id)
        user_entrances = await self.config.guild(ctx.guild).user_entrances()
        
        # Check if this entrance exists
        if (user_id_str not in user_entrances or 
            entrance_name not in user_entrances[user_id_str]):
            return await ctx.send(f"No entrance named '{entrance_name}' found.")
        
        # Ensure embed_settings exists
        if "embed_settings" not in user_entrances[user_id_str][entrance_name]:
            user_entrances[user_id_str][entrance_name]["embed_settings"] = {
                "title": "👑 A Top Panda Has Arrived! 👑",
                "color": discord.Color.gold().value,
                "footer": "All hail the wisdom of the ages!",
                "thumbnail": None,
                "image": None
            }
        
        # If no setting provided, show current settings
        if setting is None:
            settings = user_entrances[user_id_str][entrance_name]["embed_settings"]
            embed = discord.Embed(
                title=f"Embed Settings for '{entrance_name}'",
                color=discord.Color.blue()
            )
            
            color_hex = f"#{settings.get('color', 0):06x}"
            
            embed.add_field(name="Title", value=settings.get("title", "Default"), inline=False)
            embed.add_field(name="Color", value=color_hex, inline=True)
            embed.add_field(name="Footer", value=settings.get("footer", "Default"), inline=True)
            
            thumbnail = settings.get("thumbnail", "None")
            if thumbnail and thumbnail != "None":
                embed.add_field(name="Thumbnail", value=f"[Link]({thumbnail})", inline=False)
                embed.set_thumbnail(url=thumbnail)
            else:
                embed.add_field(name="Thumbnail", value="None (will use your avatar)", inline=False)
            
            image = settings.get("image", "None")
            if image and image != "None":
                embed.add_field(name="Image", value=f"[Link]({image})", inline=False)
                embed.set_image(url=image)
            else:
                embed.add_field(name="Image", value="None", inline=False)
                
            return await ctx.send(embed=embed)
        
        # Reset settings
        if setting.lower() == "reset":
            user_entrances[user_id_str][entrance_name]["embed_settings"] = {
                "title": "👑 A Top Panda Has Arrived! 👑",
                "color": discord.Color.gold().value,
                "footer": "All hail the wisdom of the ages!",
                "thumbnail": None,
                "image": None
            }
            await self.config.guild(ctx.guild).user_entrances.set(user_entrances)
            return await ctx.send(f"Embed settings for '{entrance_name}' have been reset to defaults.")
        
        # Ensure value is provided for other settings
        if value is None:
            return await ctx.send("Please provide a value for this setting.")
        
        # Update the setting
        if setting.lower() == "title":
            user_entrances[user_id_str][entrance_name]["embed_settings"]["title"] = value
            await ctx.send(f"Embed title for '{entrance_name}' set to: {value}")
            
        elif setting.lower() == "footer":
            user_entrances[user_id_str][entrance_name]["embed_settings"]["footer"] = value
            await ctx.send(f"Embed footer for '{entrance_name}' set to: {value}")
            
        elif setting.lower() == "color":
            # Parse color hex
            if value.startswith("#"):
                value = value[1:]
                
            try:
                color_value = int(value, 16)
                user_entrances[user_id_str][entrance_name]["embed_settings"]["color"] = color_value
                await ctx.send(f"Embed color for '{entrance_name}' set to: #{value}")
            except ValueError:
                return await ctx.send("Invalid color hex code. Use format: #FF5733")
                
        elif setting.lower() == "thumbnail":
            # Validate URL
            if value.lower() == "none":
                user_entrances[user_id_str][entrance_name]["embed_settings"]["thumbnail"] = None
                await ctx.send(f"Thumbnail for '{entrance_name}' removed. Your avatar will be used instead.")
            elif url_pattern := re.match(r'https?://\S+\.(jpg|jpeg|png|gif|webp)', value, re.IGNORECASE):
                user_entrances[user_id_str][entrance_name]["embed_settings"]["thumbnail"] = value
                await ctx.send(f"Embed thumbnail for '{entrance_name}' set to: {value}")
            else:
                return await ctx.send("Invalid image URL. Must be a direct link to an image (jpg, png, gif, etc).")
                
        elif setting.lower() == "image":
            # Validate URL
            if value.lower() == "none":
                user_entrances[user_id_str][entrance_name]["embed_settings"]["image"] = None
                await ctx.send(f"Main image for '{entrance_name}' removed.")
            elif url_pattern := re.match(r'https?://\S+\.(jpg|jpeg|png|gif|webp)', value, re.IGNORECASE):
                user_entrances[user_id_str][entrance_name]["embed_settings"]["image"] = value
                await ctx.send(f"Embed main image for '{entrance_name}' set to: {value}")
            else:
                return await ctx.send("Invalid image URL. Must be a direct link to an image (jpg, png, gif, etc).")
                
        else:
            return await ctx.send(f"Unknown setting: {setting}. Valid settings are: title, color, footer, thumbnail, image, reset")
        
        # Save updated settings
        await self.config.guild(ctx.guild).user_entrances.set(user_entrances)
    
    # Explicit command versions
    @commands.command(name="skadoosh")
    async def cmd_skadoosh(self, ctx):
        """Execute the skadoosh effect (explicit command version)."""
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        await self.skadoosh(ctx.message)
        
    @commands.command(name="entrance")
    async def cmd_entrance(self, ctx, entrance_name: str = None):
        """
        Execute a specific entrance effect.
        
        Usage:
        [p]entrance royal - Execute the 'royal' entrance
        [p]entrance - Execute your default entrance
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
        
        # Ensure old data is migrated
        await self.migrate_old_data(ctx.guild)
        
        # If no entrance specified, use default
        if entrance_name is None:
            default_ids = await self.config.guild(ctx.guild).default_entrance_id()
            user_id_str = str(ctx.author.id)
            entrance_name = default_ids.get(user_id_str, "default")
            
        await self.grand_entrance(ctx.message, entrance_name=entrance_name)

    @commands.command(name="help_entrance")
    async def help_entrance(self, ctx):
        """Display help for all entrance-related commands."""
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        embed = discord.Embed(
            title="📋 UltPrivates Commands Guide",
            description="Complete guide to customizing your special entrances",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🔑 Authorization",
            value="```\n!addauth [user_id] - Add authorized user\n!removeauth [user_id] - Remove authorized user\n!listauth - List all authorized users\n```",
            inline=False
        )
        
        embed.add_field(
            name="✨ Entrance Management",
            value="```\n!createentrance [name] [messages] - Create new entrance\n!deleteentrance [name] - Delete an entrance\n!listentrances - List all your entrances\n!entranceinfo [name] - Show entrance details\n!setdefault [name] - Set your default entrance\n```",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Entrance Settings",
            value="```\n!settriggers [name] [phrases] - Set trigger phrases\n!setembed [name] [setting] [value] - Customize embed\n!setdelay [seconds] - Set delay between messages\n```",
            inline=False
        )
        
        embed.add_field(
            name="🎬 Execute Effects",
            value="```\n!skadoosh - Execute skadoosh effect\n!entrance [name] - Execute specific entrance\n```",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ New Features",
            value="• Multiple entrances: You can now have up to 5 different entrances\n• Named entrances: Give each entrance a unique name\n• Dedicated triggers: Set specific trigger phrases for each entrance\n• Default entrance: Set which entrance to use when typing \"I have arrived\"",
            inline=False
        )
        
        embed.set_footer(text="Your existing entrances have been migrated to the new system automatically")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(UltPrivates(bot))
