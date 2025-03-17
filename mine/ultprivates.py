import discord
from redbot.core import commands, checks, Config
import asyncio
import json
import re

class UltPrivates(commands.Cog):
    """Special commands for VIP users with fun entrance effects."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=161183456896876544)
        
        default_guild = {
            "authorized_users": [161183456896876544],
            "entrance_delay": 3.5,
            "custom_entrances": {},
            "trigger_phrases": {},
            "embed_settings": {}
        }
        
        self.config.register_guild(**default_guild)
        
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
            await self.grand_entrance(message)
            return
        
        # Check for custom trigger phrases
        trigger_phrases = await self.config.guild(message.guild).trigger_phrases()
        if user_id_str in trigger_phrases:
            user_phrases = trigger_phrases[user_id_str]
            for phrase in user_phrases:
                if phrase.lower() in content:
                    await self.grand_entrance(message)
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
    
    async def grand_entrance(self, message):
        """
        Make a grand entrance announcement with cycling messages.
        Creates a dramatic effect for VIP users entering a channel.
        """
        try:
            # Delete the triggering message
            await message.delete()
            
            # Get custom messages if available
            custom_entrances = await self.config.guild(message.guild).custom_entrances()
            embed_settings = await self.config.guild(message.guild).embed_settings()
            user_id_str = str(message.author.id)
            
            # Get entrance messages
            if user_id_str in custom_entrances:
                entrance_messages = custom_entrances[user_id_str]
            else:
                entrance_messages = [
                    "🌟 Silence, mortals! A Panda has graced this chat with their presence! 🌟",
                    "⚡️ Tremble, for the wisdom of the ages has entered the server! ⚡️",
                    "🌪 The winds of change blow as a Top Panda steps into our midst! 🌪",
                    "🔥 Behold! The very foundation of the World Government now walks among us! 🔥",
                    "🌊 As the tides are governed by the moon, so too is this server now under the watchful eye of the main Panda! 🌊"
                ]
            
            # Get embed settings
            embed_title = "👑 A Top Panda Has Arrived! 👑"
            embed_color = discord.Color.gold()
            embed_footer = "All hail the wisdom of the ages!"
            embed_image = None
            embed_thumbnail = None
            
            # Safely get avatar URL if it exists
            if message.author.avatar:
                embed_thumbnail = message.author.avatar.url
            
            if user_id_str in embed_settings:
                settings = embed_settings[user_id_str]
                embed_title = settings.get("title", embed_title)
                embed_color = discord.Color(settings.get("color", embed_color.value))
                embed_footer = settings.get("footer", embed_footer)
                embed_image = settings.get("image", embed_image)
                embed_thumbnail = settings.get("thumbnail", embed_thumbnail)
            
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
        
    @commands.command(name="setentrance")
    async def set_custom_entrance(self, ctx, user_id: int = None, *, messages=None):
        """
        Set custom entrance messages for a user.
        Separate messages with | character.
        
        Usage:
        [p]setentrance 123456789012345678 First message! | Second message! | Final message!
        [p]setentrance - Sets for yourself
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        # If no user_id specified, use the author's ID
        if user_id is None:
            user_id = ctx.author.id
            
        # If no messages provided, show current messages
        if messages is None:
            custom_entrances = await self.config.guild(ctx.guild).custom_entrances()
            user_id_str = str(user_id)
            
            if user_id_str in custom_entrances:
                msg_list = custom_entrances[user_id_str]
                formatted_msgs = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(msg_list)])
                return await ctx.send(f"Current entrance messages for <@{user_id}>:\n{formatted_msgs}")
            else:
                return await ctx.send(f"No custom entrance messages set for <@{user_id}>.")
        
        # Parse messages (split by |)
        msg_list = [msg.strip() for msg in messages.split("|")]
        
        if len(msg_list) < 2:
            return await ctx.send("Please provide at least 2 messages separated by | character.")
            
        # Save to config
        custom_entrances = await self.config.guild(ctx.guild).custom_entrances()
        custom_entrances[str(user_id)] = msg_list
        await self.config.guild(ctx.guild).custom_entrances.set(custom_entrances)
        
        await ctx.send(f"Custom entrance messages set for <@{user_id}>!")
        
    @commands.command(name="settrigger")
    async def set_trigger_phrase(self, ctx, *, phrases=None):
        """
        Set custom trigger phrases for your entrance.
        Separate phrases with | character.
        
        Usage:
        [p]settrigger I have entered | Behold my arrival | Witness me
        [p]settrigger - Shows your current trigger phrases
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        user_id_str = str(ctx.author.id)
        
        # If no phrases provided, show current phrases
        if phrases is None:
            trigger_phrases = await self.config.guild(ctx.guild).trigger_phrases()
            
            if user_id_str in trigger_phrases:
                phrase_list = trigger_phrases[user_id_str]
                formatted_phrases = "\n".join([f"{i+1}. {phrase}" for i, phrase in enumerate(phrase_list)])
                return await ctx.send(f"Your current trigger phrases:\n{formatted_phrases}")
            else:
                return await ctx.send("You have no custom trigger phrases set.")
        
        # Parse phrases (split by |)
        phrase_list = [phrase.strip() for phrase in phrases.split("|")]
        
        if len(phrase_list) < 1:
            return await ctx.send("Please provide at least 1 trigger phrase.")
            
        # Save to config
        trigger_phrases = await self.config.guild(ctx.guild).trigger_phrases()
        trigger_phrases[user_id_str] = phrase_list
        await self.config.guild(ctx.guild).trigger_phrases.set(trigger_phrases)
        
        await ctx.send(f"Custom trigger phrases set!")
        
    @commands.command(name="setembed")
    async def set_embed_style(self, ctx, setting=None, *, value=None):
        """
        Customize your entrance embed.
        
        Settings:
        - title: Set the embed title
        - color: Set the embed color (hex code)
        - footer: Set the embed footer text
        - thumbnail: Set the thumbnail image URL
        - image: Set the main image URL
        - reset: Reset to defaults
        
        Usage:
        [p]setembed title My Grand Entrance
        [p]setembed color #FF5733
        [p]setembed footer Bow before me!
        [p]setembed thumbnail https://example.com/image.png
        [p]setembed image https://example.com/banner.gif
        [p]setembed reset
        [p]setembed - Shows current settings
        """
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        user_id_str = str(ctx.author.id)
        embed_settings = await self.config.guild(ctx.guild).embed_settings()
        
        # Initialize user settings if not exist
        if user_id_str not in embed_settings:
            embed_settings[user_id_str] = {
                "title": "👑 A Top Panda Has Arrived! 👑",
                "color": discord.Color.gold().value,
                "footer": "All hail the wisdom of the ages!",
                "thumbnail": None,
                "image": None
            }
        
        # If no setting provided, show current settings
        if setting is None:
            settings = embed_settings.get(user_id_str, {})
            embed = discord.Embed(
                title="Your Entrance Embed Settings",
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
            if user_id_str in embed_settings:
                del embed_settings[user_id_str]
                await self.config.guild(ctx.guild).embed_settings.set(embed_settings)
                return await ctx.send("Your embed settings have been reset to defaults.")
            else:
                return await ctx.send("You're already using default settings.")
        
        # Ensure value is provided for other settings
        if value is None:
            return await ctx.send("Please provide a value for this setting.")
        
        # Update the setting
        if setting.lower() == "title":
            embed_settings[user_id_str]["title"] = value
            await ctx.send(f"Embed title set to: {value}")
            
        elif setting.lower() == "footer":
            embed_settings[user_id_str]["footer"] = value
            await ctx.send(f"Embed footer set to: {value}")
            
        elif setting.lower() == "color":
            # Parse color hex
            if value.startswith("#"):
                value = value[1:]
                
            try:
                color_value = int(value, 16)
                embed_settings[user_id_str]["color"] = color_value
                await ctx.send(f"Embed color set to: #{value}")
            except ValueError:
                return await ctx.send("Invalid color hex code. Use format: #FF5733")
                
        elif setting.lower() == "thumbnail":
            # Validate URL
            if value.lower() == "none":
                embed_settings[user_id_str]["thumbnail"] = None
                await ctx.send("Thumbnail removed. Your avatar will be used instead.")
            elif url_pattern := re.match(r'https?://\S+\.(jpg|jpeg|png|gif|webp)', value, re.IGNORECASE):
                embed_settings[user_id_str]["thumbnail"] = value
                await ctx.send(f"Embed thumbnail set to: {value}")
            else:
                return await ctx.send("Invalid image URL. Must be a direct link to an image (jpg, png, gif, etc).")
                
        elif setting.lower() == "image":
            # Validate URL
            if value.lower() == "none":
                embed_settings[user_id_str]["image"] = None
                await ctx.send("Main image removed.")
            elif url_pattern := re.match(r'https?://\S+\.(jpg|jpeg|png|gif|webp)', value, re.IGNORECASE):
                embed_settings[user_id_str]["image"] = value
                await ctx.send(f"Embed main image set to: {value}")
            else:
                return await ctx.send("Invalid image URL. Must be a direct link to an image (jpg, png, gif, etc).")
                
        else:
            return await ctx.send(f"Unknown setting: {setting}. Valid settings are: title, color, footer, thumbnail, image, reset")
        
        # Save updated settings
        await self.config.guild(ctx.guild).embed_settings.set(embed_settings)
            
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
        
    # Explicit command versions
    @commands.command(name="skadoosh")
    async def cmd_skadoosh(self, ctx):
        """Execute the skadoosh effect (explicit command version)."""
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        await self.skadoosh(ctx.message)
        
    @commands.command(name="entrance")
    async def cmd_entrance(self, ctx):
        """Execute the grand entrance effect (explicit command version)."""
        if not await self.is_authorized(ctx.guild.id, ctx.author.id):
            return await ctx.send("You are not authorized to use this command.")
            
        await self.grand_entrance(ctx.message)
        
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
            name="✨ Entrance Settings",
            value="```\n!setentrance [messages] - Set custom messages (separate with |)\n!settrigger [phrases] - Set custom trigger phrases\n!setdelay [seconds] - Set delay between messages\n```",
            inline=False
        )
        
        embed.add_field(
            name="🎨 Embed Customization",
            value="```\n!setembed title [text] - Set embed title\n!setembed color [hex] - Set embed color\n!setembed footer [text] - Set embed footer\n!setembed thumbnail [url] - Set thumbnail image\n!setembed image [url] - Set main image\n!setembed reset - Reset to defaults\n```",
            inline=False
        )
        
        embed.add_field(
            name="🎬 Execute Effects",
            value="```\n!skadoosh - Execute skadoosh effect\n!entrance - Execute entrance effect\n```",
            inline=False
        )
        
        embed.set_footer(text="You can also trigger effects with phrases in normal messages")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(UltPrivates(bot))
