import asyncio
import random
from typing import Dict, Optional
import discord
from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify

class DenDenMushi(commands.Cog):
    """
    One Piece themed communication system using Den Den Mushi.
    
    This cog allows administrators to set up channel-to-channel
    communications with various Den Den Mushi types, each with
    unique properties like range and transmission speed.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_guild = {
            "connections": {},  # {source_channel_id: {"target": target_channel_id, "type": snail_type}}
        }
        self.config.register_guild(**default_guild)
        self.active_connections: Dict[int, Dict[str, int]] = {}
        self.snail_types = {
            "Baby": {"emoji": "🐌", "color": 0x87CEEB, "range": "short"},
            "Adult": {"emoji": "🐌", "color": 0x4682B4, "range": "medium"},
            "Silver": {"emoji": "🐌", "color": 0xC0C0C0, "range": "long"},
            "Golden": {"emoji": "🐌", "color": 0xFFD700, "range": "global"},
            "Black": {"emoji": "🐌", "color": 0x000000, "range": "intercept"}
        }
        
    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def dendenmushi(self, ctx: commands.Context):
        """Manage Den Den Mushi connections."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @dendenmushi.command(name="connect")
    async def dendenmushi_connect(self, ctx: commands.Context, target_channel: discord.TextChannel, snail_type: str = None):
        """
        Connect to a target channel using a Den Den Mushi.
        
        You can optionally specify the snail type (Baby, Adult, Silver, Golden, Black).
        If no type is specified, one will be chosen randomly.
        """
        guild = ctx.guild
        source_channel = ctx.channel

        if source_channel.id in self.active_connections:
            await ctx.send("Purupurupuru~ This Den Den Mushi is already connected!")
            return

        if snail_type and snail_type.capitalize() not in self.snail_types:
            await ctx.send(f"Behehehe~ That's not a real Den Den Mushi type! Choose from {', '.join(self.snail_types.keys())}.")
            return

        chosen_type = snail_type.capitalize() if snail_type else random.choice(list(self.snail_types.keys()))
        
        if not self._check_connection_range(source_channel, target_channel, chosen_type):
            await ctx.send(f"Behehehe~ The {chosen_type} Den Den Mushi can't reach that far!")
            return

        self.active_connections[source_channel.id] = {"target": target_channel.id, "type": chosen_type}
        await self.config.guild(guild).connections.set(self.active_connections)
        await ctx.send(f"Gacha~ Connected to {target_channel.mention} using a {chosen_type} Den Den Mushi! {self.snail_types[chosen_type]['emoji']}")

    @dendenmushi.command(name="disconnect")
    async def dendenmushi_disconnect(self, ctx: commands.Context):
        """Disconnect the current Den Den Mushi."""
        guild = ctx.guild
        source_channel = ctx.channel

        if source_channel.id not in self.active_connections:
            await ctx.send("Behehehe~ This Den Den Mushi isn't connected to anything!")
            return

        del self.active_connections[source_channel.id]
        await self.config.guild(guild).connections.set(self.active_connections)
        await ctx.send("Catcha~ The Den Den Mushi has gone back to sleep.")

    @dendenmushi.command(name="list")
    async def dendenmushi_list(self, ctx: commands.Context):
        """List all active Den Den Mushi connections in the server."""
        guild = ctx.guild
        connections = await self.config.guild(guild).connections()
        
        if not connections:
            await ctx.send("There are no active Den Den Mushi connections in this part of the Grand Line.")
            return

        message = "Active Den Den Mushi connections:\n\n"
        for source_id, connection_info in connections.items():
            source_channel = guild.get_channel(int(source_id))
            target_channel = guild.get_channel(int(connection_info['target']))
            if source_channel and target_channel:
                snail_type = connection_info['type']
                message += f"{self.snail_types[snail_type]['emoji']} {snail_type} Den Den Mushi: {source_channel.mention} → {target_channel.mention}\n"

        for page in pagify(message):
            await ctx.send(page)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Check if the message is in a source channel
        if message.channel.id in self.active_connections:
            await self._send_message(message, is_source=True)
        
        # Check if the message is in a target channel
        for source_id, connection_info in self.active_connections.items():
            if message.channel.id == connection_info['target']:
                await self._send_message(message, is_source=False, source_id=source_id)

    async def _send_message(self, message: discord.Message, is_source: bool, source_id: int = None):
        if is_source:
            connection_info = self.active_connections[message.channel.id]
            target_channel = self.bot.get_channel(connection_info['target'])
            source_channel = message.channel
        else:
            source_channel = self.bot.get_channel(source_id)
            target_channel = message.channel

        if not target_channel or not source_channel:
            return

        snail_type = connection_info['type'] if is_source else self.active_connections[source_id]['type']
        color = self.snail_types[snail_type]['color']
        emoji = self.snail_types[snail_type]['emoji']

        embed = discord.Embed(
            title=f"{emoji} Den Den Mushi Message {emoji}",
            description=f"**{message.author.display_name}:** {message.content}",
            color=color
        )
        embed.set_footer(text=f"Transmitted via {snail_type} Den Den Mushi • Gacha~")

        # Handle attachments (images, GIFs)
        if message.attachments:
            file = message.attachments[0]
            if file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                embed.set_image(url=file.url)
            embed.add_field(name="Attachments", value="\n".join([f"[{a.filename}]({a.url})" for a in message.attachments]), inline=False)

        # Handle URLs in the message content
        urls = re.findall(r'(https?://\S+)', message.content)
        if urls:
            embed.add_field(name="URLs", value="\n".join(urls), inline=False)

        delay = self._get_transmission_delay(snail_type)
        await asyncio.sleep(delay)

        destination = target_channel if is_source else source_channel
        await destination.send("Purupurupuru~", embed=embed)

    @dendenmushi.command(name="intercept")
    @checks.is_owner()
    async def dendenmushi_intercept(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Secretly intercept messages from a channel.
        
        This command is only available to the bot owner and simulates the Black Den Den Mushi.
        """
        guild = ctx.guild
        source_channel = ctx.channel

        self.active_connections[source_channel.id] = {"target": channel.id, "type": "Black"}
        await self.config.guild(guild).connections.set(self.active_connections)
        await ctx.send(f"Black Den Den Mushi activated. Intercepting messages from {channel.mention}. Shhh!", delete_after=10)

    def _check_connection_range(self, source_channel: discord.TextChannel, target_channel: discord.TextChannel, snail_type: str) -> bool:
        """Check if the connection is within the range of the Den Den Mushi type."""
        snail_range = self.snail_types[snail_type]['range']
        
        if snail_range == "global":
            return True
        elif snail_range == "intercept":
            return True  # Assuming Black Den Den Mushi can intercept any channel
        
        # Calculate "distance" based on channel positions
        distance = abs(source_channel.position - target_channel.position)
        
        if snail_range == "short":
            return distance <= 5
        elif snail_range == "medium":
            return distance <= 15
        elif snail_range == "long":
            return distance <= 30
        
        return False

    def _get_transmission_delay(self, snail_type: str) -> float:
        """Get the transmission delay based on the Den Den Mushi type."""
        if snail_type == "Baby":
            return 0.5
        elif snail_type == "Adult":
            return 1.0
        elif snail_type == "Silver":
            return 0.2
        elif snail_type == "Golden":
            return 0.1
        elif snail_type == "Black":
            return 0.0  # Instant transmission for interception
        return 0.5  # Default delay

    async def cog_load(self):
        for guild in self.bot.guilds:
            self.active_connections.update(await self.config.guild(guild).connections())

async def setup(bot):
    await bot.add_cog(DenDenMushi(bot))
