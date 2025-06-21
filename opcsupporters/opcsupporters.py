from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import pagify

import datetime
import re
from collections import defaultdict

# Credits:
# This cog is heavily inspired by and based on the ServerSupporters cog by AAA3A
# Original ServerSupporters cog: https://github.com/AAA3A-AAA3A/AAA3A-cogs
# Many thanks to AAA3A for the original concept, structure, and implementation ideas
# Modified specifically for One Piece Community server with announcement-only functionality

_: Translator = Translator("OPCServerSupporters", __file__)

# Hardcoded values for One Piece Community
OPC_INVITE_CODE = "onepiececommunity"
OPC_CLAN_TAG = "OPC"


@cog_i18n(_)
class OPCServerSupporters(commands.Cog):
    """
    Track and announce when members support the One Piece Community server with OPC tag or discord.gg/onepiececommunity in their status!
    
    Based on the original ServerSupporters cog by AAA3A (https://github.com/AAA3A-AAA3A/AAA3A-cogs)
    """

    def __init__(self, bot: Red) -> None:
        super().__init__()
        self.bot = bot

        self.config: Config = Config.get_conf(
            self,
            identifier=205192943327321000143939875896557571751,  # Different ID from original
            force_registration=True,
        )
        self.config.register_guild(
            enabled=False,
            announcement_channel=None,
        )

        # Cache to prevent spam and API limit issues
        # Implementation inspired by AAA3A's original caching system
        self.cache: typing.Dict[discord.Member, bool] = defaultdict(bool)
        # Track current supporter status to detect changes
        self.supporter_status: typing.Dict[int, typing.Dict[str, bool]] = defaultdict(lambda: {"tag": False, "status": False})

    async def get_supporter_counts(self, guild: discord.Guild) -> typing.Dict[str, int]:
        """
        Get current count of supporters by type (optimized single scan).
        Counting methodology inspired by AAA3A's original implementation.
        """
        counts = {"tag": 0, "status": 0, "total": 0}
        unique_supporters = set()
        
        # Single scan through all members - efficient approach from AAA3A's design
        retrieve, after = 1000, discord.guild.OLDEST_OBJECT
        while True:
            after_id = after.id if after else None
            try:
                data = await self.bot.http.get_members(guild.id, retrieve, after_id)
            except discord.HTTPException:
                break
            if not data:
                break
            after = discord.Object(id=int(data[-1]["user"]["id"]))
            
            for raw_member in reversed(data):
                member = discord.Member(data=raw_member, guild=guild, state=guild._state)
                if member.bot:
                    continue
                    
                has_tag = await self.check_supporter_status(member, "tag", raw_member["user"])
                has_status = await self.check_supporter_status(member, "status")
                
                if has_tag:
                    counts["tag"] += 1
                    unique_supporters.add(member.id)
                if has_status:
                    counts["status"] += 1
                    unique_supporters.add(member.id)
                    
            if len(data) < 1000:
                break
        
        counts["total"] = len(unique_supporters)
        return counts

    async def get_announcement_embed(self, member: discord.Member, _type: typing.Literal["tag", "status"], enabled: bool = True) -> discord.Embed:
        """
        Create embed for supporter announcements.
        Embed structure and styling inspired by AAA3A's original design.
        """
        if _type == "tag":
            support_method = f"**{OPC_CLAN_TAG}** clan tag"
        else:
            support_method = f"**discord.gg/{OPC_INVITE_CODE}** in their status"

        if enabled:
            title = "🎉 New OPC Supporter!"
            description = f"{member.mention} is now supporting One Piece Community by using {support_method}!"
            color = discord.Color.green()
        else:
            title = "😔 OPC Supporter Departed"
            description = f"{member.mention} is no longer supporting One Piece Community with {support_method}."
            color = discord.Color.red()

        embed: discord.Embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar,
        )
        embed.set_thumbnail(url=member.display_avatar)
        
        # Add field showing what they're supporting with
        if enabled:
            embed.add_field(
                name="Supporting with:",
                value=support_method,
                inline=True
            )
        
        # Get current counts for footer - inspired by AAA3A's logging approach
        try:
            counts = await self.get_supporter_counts(member.guild)
            footer_text = f"OPC Supporters: {counts['tag']} Tags • {counts['status']} Status • {member.guild.name}"
        except Exception:
            footer_text = f"One Piece Community • {member.guild.name}"
            
        embed.set_footer(
            text=footer_text, 
            icon_url=member.guild.icon
        )
        
        return embed

    async def announce_supporter_change(self, member: discord.Member, _type: typing.Literal["tag", "status"], enabled: bool = True) -> None:
        """
        Send announcement to the configured channel.
        Logging methodology based on AAA3A's original implementation.
        """
        announcement_channel_id = await self.config.guild(member.guild).announcement_channel()
        if not announcement_channel_id:
            return
            
        announcement_channel = member.guild.get_channel_or_thread(announcement_channel_id)
        if not announcement_channel:
            return

        try:
            embed = await self.get_announcement_embed(member, _type, enabled)
            await announcement_channel.send(embed=embed)
        except discord.HTTPException as e:
            # Error handling approach inspired by AAA3A's robust error management
            print(f"Failed to send announcement for member `{member.name}` ({member.id}) in guild `{member.guild.name}` ({member.guild.id}): {e}")

    async def check_opc_invite_in_status(self, status: str) -> bool:
        """
        Check if the OPC invite link is in the user's status.
        Regex pattern inspired by AAA3A's original invite detection logic.
        """
        # Look for discord.gg/onepiececommunity or variations
        invite_pattern = r"discord\.(?:gg|io|me|li)\/onepiececommunity|discord(?:app)?\.com\/invite\/onepiececommunity"
        return bool(re.search(invite_pattern, status, re.IGNORECASE))

    async def check_supporter_status(
        self,
        member: discord.Member,
        _type: typing.Literal["tag", "status"],
        user_payload: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> bool:
        """
        Check if member is currently supporting via tag or status.
        Detection logic based on AAA3A's original check methods.
        """
        if _type == "tag":
            if user_payload is None:
                try:
                    user_payload = await self.bot.http.request(
                        discord.http.Route(
                            "GET",
                            "/users/{user_id}",
                            user_id=member.id,
                        )
                    )
                except discord.HTTPException:
                    return False
            
            # Check if they have OPC clan tag - clan detection from AAA3A's implementation
            return (
                user_payload.get("clan") is not None
                and user_payload["clan"].get("identity_enabled", False)
                and user_payload["clan"].get("tag") == OPC_CLAN_TAG
            )
            
        elif _type == "status":
            # Check for OPC invite in custom status - status checking from AAA3A's method
            if not member.activities:
                return False
                
            custom_activity = next(
                (a for a in member.activities if isinstance(a, discord.CustomActivity)), 
                None
            )
            if not custom_activity or not custom_activity.name:
                return False
                
            return await self.check_opc_invite_in_status(custom_activity.name)
        
        return False

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member) -> None:
        """
        Listen for status changes to detect OPC invite links.
        Event listener structure based on AAA3A's original presence monitoring.
        """
        if after.bot:
            return
            
        # Check if system is enabled
        if (
            not await self.config.guild(after.guild).enabled()
            or await self.bot.cog_disabled_in_guild(self, after.guild)
        ):
            return
            
        # Prevent spam with cache - caching approach from AAA3A's anti-spam system
        if self.cache[after]:
            return
        self.cache[after] = True

        try:
            # Check current status supporter state
            current_status_support = await self.check_supporter_status(after, "status")
            previous_status_support = self.supporter_status[after.id]["status"]
            
            # Update our tracking
            self.supporter_status[after.id]["status"] = current_status_support
            
            # Only announce if there's a change - change detection from AAA3A's logic
            if previous_status_support != current_status_support:
                await self.announce_supporter_change(after, "status", current_status_support)
                
        finally:
            self.cache.pop(after, None)

    @commands.Cog.listener()
    async def on_member_update(
        self, 
        before: discord.Member, 
        after: discord.Member,
        user_payload: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> None:
        """
        Listen for clan tag changes.
        Member update monitoring based on AAA3A's original tag tracking system.
        """
        if after.bot:
            return
            
        # Check if system is enabled
        if (
            not await self.config.guild(after.guild).enabled()
            or await self.bot.cog_disabled_in_guild(self, after.guild)
        ):
            return
            
        # Prevent spam with cache - using AAA3A's caching strategy
        if self.cache[after]:
            return
        self.cache[after] = True

        try:
            # Check current tag supporter state
            current_tag_support = await self.check_supporter_status(after, "tag", user_payload)
            previous_tag_support = self.supporter_status[after.id]["tag"]
            
            # Update our tracking
            self.supporter_status[after.id]["tag"] = current_tag_support
            
            # Only announce if there's a change
            if previous_tag_support != current_tag_support:
                await self.announce_supporter_change(after, "tag", current_tag_support)
                
        finally:
            self.cache.pop(after, None)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setopcsupporters(self, ctx: commands.Context) -> None:
        """
        Settings for the OPC Supporters announcement system.
        Command structure inspired by AAA3A's configuration system.
        """
        pass

    @setopcsupporters.command()
    async def enabled(self, ctx: commands.Context, enabled: bool) -> None:
        """Enable or disable the OPC supporters system."""
        await self.config.guild(ctx.guild).enabled.set(enabled)
        status = "enabled" if enabled else "disabled"
        embed = discord.Embed(
            title="⚙️ OPC Supporters System",
            description=f"The system has been **{status}**.",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        await ctx.send(embed=embed)

    @setopcsupporters.command()
    async def announcementchannel(self, ctx: commands.Context, channel: typing.Union[discord.TextChannel, discord.VoiceChannel, discord.Thread] = None) -> None:
        """Set the channel where supporter announcements will be sent."""
        if channel is None:
            await self.config.guild(ctx.guild).announcement_channel.set(None)
            embed = discord.Embed(
                title="📢 Announcement Channel",
                description="Announcement channel has been **removed**.",
                color=discord.Color.red()
            )
        else:
            await self.config.guild(ctx.guild).announcement_channel.set(channel.id)
            embed = discord.Embed(
                title="📢 Announcement Channel",
                description=f"Announcements will now be sent to {channel.mention}.",
                color=discord.Color.green()
            )
        await ctx.send(embed=embed)

    @setopcsupporters.command()
    async def showsettings(self, ctx: commands.Context) -> None:
        """Show current settings for the OPC supporters system."""
        guild_config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="⚙️ OPC Supporters Settings",
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at
        )
        
        # System status
        status = "✅ Enabled" if guild_config["enabled"] else "❌ Disabled"
        embed.add_field(name="System Status", value=status, inline=True)
        
        # Announcement channel
        if guild_config["announcement_channel"]:
            channel = ctx.guild.get_channel(guild_config["announcement_channel"])
            channel_text = channel.mention if channel else "❌ Channel not found"
        else:
            channel_text = "❌ Not set"
        embed.add_field(name="Announcement Channel", value=channel_text, inline=True)
        
        # What we track
        embed.add_field(
            name="📈 Tracking",
            value=f"• **{OPC_CLAN_TAG}** clan tag\n• **discord.gg/{OPC_INVITE_CODE}** in status",
            inline=False
        )
        
        embed.set_footer(text="Settings based on AAA3A's original configuration system")
        await ctx.send(embed=embed)

    @setopcsupporters.command(aliases=["count", "stats"])
    async def supportercount(self, ctx: commands.Context) -> None:
        """
        Show current count of OPC supporters.
        Statistics implementation inspired by AAA3A's data presentation methods.
        """
        # Show typing indicator for better UX during count
        async with ctx.typing():
            counts = await self.get_supporter_counts(ctx.guild)
        
        embed = discord.Embed(
            title="🏴‍☠️ OPC Supporter Statistics",
            color=discord.Color.gold(),
            timestamp=ctx.message.created_at
        )
        
        # Main stats
        embed.add_field(
            name="📋 OPC Clan Tag",
            value=f"**{counts['tag']:,}** supporters",
            inline=True
        )
        embed.add_field(
            name="💬 Status Invite",
            value=f"**{counts['status']:,}** supporters",
            inline=True
        )
        embed.add_field(
            name="👥 Total Unique",
            value=f"**{counts['total']:,}** supporters",
            inline=True
        )
        
        # Calculate percentages
        total_members = len([m for m in ctx.guild.members if not m.bot])
        if total_members > 0:
            tag_percent = (counts['tag'] / total_members) * 100
            status_percent = (counts['status'] / total_members) * 100
            total_percent = (counts['total'] / total_members) * 100
            
            embed.add_field(
                name="📊 Engagement Rate",
                value=f"**{total_percent:.1f}%** of members are supporters\n"
                      f"• Tag supporters: {tag_percent:.1f}%\n"
                      f"• Status supporters: {status_percent:.1f}%",
                inline=False
            )
        
        embed.add_field(
            name="📈 What We Track",
            value=f"• **{OPC_CLAN_TAG}** clan tag usage\n"
                  f"• **discord.gg/{OPC_INVITE_CODE}** in status\n"
                  f"• Real-time changes and updates",
            inline=False
        )
        
        embed.set_footer(
            text=f"One Piece Community • Total Members: {total_members:,} • Stats system inspired by AAA3A",
            icon_url=ctx.guild.icon
        )
        
        await ctx.send(embed=embed)

    @setopcsupporters.command(aliases=["list"])
    async def listsupporters(self, ctx: commands.Context, _type: typing.Literal["tag", "status"]) -> None:
        """
        List all current OPC supporters by type.
        Member listing approach based on AAA3A's original implementation.
        """
        supporters = []
        
        if _type == "tag":
            # Check all members for OPC clan tag - efficient scanning from AAA3A's method
            retrieve, after = 1000, discord.guild.OLDEST_OBJECT
            while True:
                after_id = after.id if after else None
                data = await ctx.bot.http.get_members(ctx.guild.id, retrieve, after_id)
                if not data:
                    break
                after = discord.Object(id=int(data[-1]["user"]["id"]))
                
                for raw_member in reversed(data):
                    member = discord.Member(data=raw_member, guild=ctx.guild, state=ctx.guild._state)
                    if member.bot:
                        continue
                    if await self.check_supporter_status(member, "tag", raw_member["user"]):
                        supporters.append(member)
                        
                if len(data) < 1000:
                    break
        else:
            # Check all members for OPC invite in status
            supporters = [
                member for member in ctx.guild.members
                if not member.bot and await self.check_supporter_status(member, "status")
            ]

        support_method = "OPC Clan Tag" if _type == "tag" else "Invite Link in Status"
        embed: discord.Embed = discord.Embed(
            title=f"🏴‍☠️ {len(supporters)} OPC Supporter{'' if len(supporters) == 1 else 's'} ({support_method})",
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        embed.set_footer(text=f"One Piece Community • {ctx.guild.name} • Listing based on AAA3A's design", icon_url=ctx.guild.icon)
        
        if supporters:
            description = "\n".join(f"• {member.mention}" for member in supporters)
            # Simple pagination - inspired by AAA3A's Menu system but simplified
            if len(description) <= 2000:
                embed.description = description
                await ctx.send(embed=embed)
            else:
                # Split into multiple embeds for long lists
                pages = []
                for page in pagify(description, page_length=2000):
                    e = embed.copy()
                    e.description = page
                    pages.append(e)
                
                # Send first page with navigation info
                if len(pages) > 1:
                    pages[0].set_footer(text=f"Page 1/{len(pages)} • Based on AAA3A's pagination design")
                await ctx.send(embed=pages[0])
                
                # Send remaining pages
                for i, page in enumerate(pages[1:], 2):
                    page.set_footer(text=f"Page {i}/{len(pages)} • One Piece Community")
                    await ctx.send(embed=page)
        else:
            embed.description = f"No current {support_method.lower()} supporters found."
            await ctx.send(embed=embed)

    @setopcsupporters.command()
    async def scan(self, ctx: commands.Context) -> None:
        """
        Scan all members and initialize supporter tracking (run this once after setup).
        Scanning methodology based on AAA3A's force update implementation.
        """
        if not await self.config.guild(ctx.guild).enabled():
            embed = discord.Embed(
                title="❌ System Disabled",
                description="The OPC Supporters system is not enabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🔍 Initializing OPC Supporter Tracking",
            description="Scanning all members to prevent false announcements...",
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=embed)
        
        scanned = 0
        tag_supporters = 0
        status_supporters = 0
        
        # Scan all members and initialize tracking without announcements
        # Efficient scanning approach from AAA3A's implementation
        retrieve, after = 1000, discord.guild.OLDEST_OBJECT
        while True:
            after_id = after.id if after else None
            data = await ctx.bot.http.get_members(ctx.guild.id, retrieve, after_id)
            if not data:
                break
            after = discord.Object(id=int(data[-1]["user"]["id"]))
            
            for raw_member in reversed(data):
                member = discord.Member(data=raw_member, guild=ctx.guild, state=ctx.guild._state)
                if member.bot:
                    continue
                    
                scanned += 1
                
                # Check and initialize tracking without announcements
                tag_support = await self.check_supporter_status(member, "tag", raw_member["user"])
                status_support = await self.check_supporter_status(member, "status")
                
                self.supporter_status[member.id]["tag"] = tag_support
                self.supporter_status[member.id]["status"] = status_support
                
                if tag_support:
                    tag_supporters += 1
                if status_support:
                    status_supporters += 1
                    
            if len(data) < 1000:
                break
        
        embed = discord.Embed(
            title="✅ OPC Supporter Scan Complete",
            description=f"Successfully scanned **{scanned:,}** members",
            color=discord.Color.green(),
            timestamp=ctx.message.created_at
        )
        embed.add_field(name="🏷️ OPC Clan Tag Supporters", value=f"**{tag_supporters:,}**", inline=True)
        embed.add_field(name="💬 Invite Status Supporters", value=f"**{status_supporters:,}**", inline=True)
        embed.add_field(name="📢 Status", value="Now tracking changes for announcements!", inline=False)
        embed.set_footer(text="Initialization complete • Based on AAA3A's scanning system")
        
        await msg.edit(embed=embed)