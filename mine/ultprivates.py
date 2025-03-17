import discord
from redbot.core import commands, checks, Config
import asyncio
import json

class UltPrivates(commands.Cog):
    """Special commands for VIP users with fun entrance effects."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=161183456896876544)
        
        default_guild = {
            "authorized_users": [161183456896876544],
            "entrance_delay": 3.5,
            "custom_entrances": {}
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
        # Ignore bot messages
        if message.author.bot or not message.guild:
            return
        
        # Check authorization first
        if not await self.is_authorized(message.guild.id, message.author.id):
            return
            
        content = message.content.lower()
        
        if "skadoosh" in content:
            await self.skadoosh(message)
        elif "i have arrived" in content:
            await self.grand_entrance(message)
    
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
            user_id_str = str(message.author.id)
            
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
            
            # Get entrance delay
            delay = await self.config.guild(message.guild).entrance_delay()
            
            # Create initial embed
            embed = discord.Embed(
                title="👑 A Top Panda Has Arrived! 👑",
                description=entrance_messages[0],
                color=discord.Color.gold()
            )
            
            # Add user avatar if available
            if message.author.avatar:
                embed.set_thumbnail(url=message.author.avatar.url)
                
            embed.set_footer(text="All hail the wisdom of the ages!")
            
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

async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(UltPrivates(bot))
