from redbot.core import commands, Config  # isort:skip
from redbot.core.bot import Red  # isort:skip
from redbot.core.i18n import Translator, cog_i18n  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

from redbot.core.utils.chat_formatting import pagify

import datetime
import re
import asyncio
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

# Milestone thresholds - optimized for large servers
MILESTONE_THRESHOLDS = [10, 25, 50, 75, 100, 150, 200, 250, 300, 400, 500, 750, 1000, 1250, 1500, 2000, 2500, 3000, 4000, 5000]


@cog_i18n(_)
class OPCServerSupporters(commands.Cog):
    """
    Track and announce when members support the One Piece Community server with OPC tag or discord.gg/onepiececommunity in their status!
    
    Optimized for large servers (17k+ members) with milestone celebrations and performance features.
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
            previous_counts={"tag": 0, "status": 0, "total": 0},  # For milestone tracking
            performance_mode=True,   # Default True for large servers
            scan_batch_size=150,     # Optimized for 17k server
            scan_delay=0.2,          # Slightly longer delay for stability
            quiet_hours_start=3,     # 3 AM
            quiet_hours_end=7,       # 7 AM
            milestone_announcements=True,  # Enable milestone celebrations
        )

        # Cache to prevent spam and API limit issues
        # Implementation inspired by AAA3A's original caching system
        self.cache: typing.Dict[discord.Member, bool] = defaultdict(bool)
        # Track current supporter status to detect changes
        self.supporter_status: typing.Dict[int, typing.Dict[str, bool]] = defaultdict(lambda: {"tag": False, "status": False})
        
        # Performance tracking for large servers
        self.scan_in_progress = False
        self.last_scan_time = None
        self.performance_stats = {"total_scanned": 0, "last_scan_duration": 0}

    async def is_quiet_hours(self, guild: discord.Guild) -> bool:
        """Check if current time is during configured quiet hours."""
        config = await self.config.guild(guild).all()
        start_hour = config.get("quiet_hours_start", 3)
        end_hour = config.get("quiet_hours_end", 7)
        
        current_hour = datetime.datetime.now().hour
        
        if start_hour <= end_hour:
            return start_hour <= current_hour < end_hour
        else:  # Crosses midnight
            return current_hour >= start_hour or current_hour < end_hour

    async def check_and_announce_milestones(self, guild: discord.Guild, counts: dict) -> None:
        """
        Check if we've hit any milestones and announce them.
        Milestone system designed for large server engagement.
        """
        if not await self.config.guild(guild).milestone_announcements():
            return
            
        # Get previous counts from config
        previous_counts = await self.config.guild(guild).previous_counts()
        if not previous_counts:
            previous_counts = {"tag": 0, "status": 0, "total": 0}
        
        announcement_channel_id = await self.config.guild(guild).announcement_channel()
        if not announcement_channel_id:
            return
            
        channel = guild.get_channel_or_thread(announcement_channel_id)
        if not channel:
            return

        # Check each milestone type
        milestone_messages = []
        
        # OPC Clan Tag milestones
        for threshold in MILESTONE_THRESHOLDS:
            if (previous_counts["tag"] < threshold <= counts["tag"]):
                milestone_messages.append({
                    "type": "tag",
                    "count": threshold,
                    "emoji": "🏷️",
                    "title": "🎉 OPC Clan Milestone! 🎉",
                    "message": f"We just hit **{threshold:,} OPC clan supporters!** 🏴‍☠️\n\nThank you to everyone representing the crew with the **{OPC_CLAN_TAG}** tag!"
                })
        
        # Status Invite milestones
        for threshold in MILESTONE_THRESHOLDS:
            if (previous_counts["status"] < threshold <= counts["status"]):
                milestone_messages.append({
                    "type": "status", 
                    "count": threshold,
                    "emoji": "💬",
                    "title": "🏴‍☠️ Invite Milestone! 🏴‍☠️",
                    "message": f"**{threshold:,} crew members** now have our invite link in their status!\n\nSpread the word about **discord.gg/{OPC_INVITE_CODE}**!"
                })
        
        # Total supporters milestones (bigger celebrations)
        for threshold in MILESTONE_THRESHOLDS:
            if (previous_counts["total"] < threshold <= counts["total"]):
                milestone_messages.append({
                    "type": "total",
                    "count": threshold, 
                    "emoji": "👥",
                    "title": "🌟 INCREDIBLE MILESTONE! 🌟",
                    "message": f"**{threshold:,} total OPC supporters!** 🚀\n\nOur crew keeps growing stronger! Thank you to everyone supporting One Piece Community!"
                })

        # Send milestone announcements
        for milestone in milestone_messages:
            embed = discord.Embed(
                title=milestone["title"],
                description=milestone["message"],
                color=discord.Color.gold(),
                timestamp=datetime.datetime.now(tz=datetime.timezone.utc)
            )
            
            # Add current stats
            embed.add_field(
                name="📊 Current Stats",
                value=f"🏷️ **{counts['tag']:,}** Clan Tags\n💬 **{counts['status']:,}** Status Invites\n👥 **{counts['total']:,}** Total Supporters",
                inline=False
            )
            
            # Special messaging based on milestone size
            if milestone["count"] >= 500:
                embed.add_field(
                    name="🎊 Major Achievement",
                    value="This is a major milestone for our 17k+ member community! Every supporter helps us grow stronger! 💪",
                    inline=False
                )
            elif milestone["count"] >= 100:
                embed.add_field(
                    name="🎉 Great Progress",
                    value="Amazing growth in our supporter community! Keep it up, crew! ⭐",
                    inline=False
                )
            
            # Add percentage for large server context
            total_members = len([m for m in guild.members if not m.bot])
            if total_members > 0:
                percentage = (counts["total"] / total_members) * 100
                embed.add_field(
                    name="📈 Engagement Rate",
                    value=f"**{percentage:.1f}%** of our {total_members:,} members are supporters!",
                    inline=False
                )
            
            embed.set_footer(
                text=f"One Piece Community • Milestone: {milestone['count']:,} {milestone['type']} supporters",
                icon_url=guild.icon
            )
            
            try:
                await channel.send(embed=embed)
                # Small delay between milestone messages to prevent spam
                await asyncio.sleep(2)
            except discord.HTTPException as e:
                print(f"Failed to send milestone announcement: {e}")
        
        # Update stored previous counts
        await self.config.guild(guild).previous_counts.set(counts)

    async def get_supporter_counts(self, guild: discord.Guild) -> typing.Dict[str, int]:
        """
        Get current count of supporters by type (optimized for large servers).
        Performance-optimized scanning methodology based on AAA3A's original implementation.
        """
        counts = {"tag": 0, "status": 0, "total": 0}
        unique_supporters = set()
        
        config = await self.config.guild(guild).all()
        batch_size = config.get("scan_batch_size", 150)
        delay = config.get("scan_delay", 0.2)
        performance_mode = config.get("performance_mode", True)
        
        total_members = 0
        processed_batches = 0
        
        # Optimized scanning for 17k+ server
        retrieve, after = batch_size, discord.guild.OLDEST_OBJECT
        while True:
            after_id = after.id if after else None
            try:
                data = await self.bot.http.get_members(guild.id, retrieve, after_id)
            except discord.HTTPException as e:
                print(f"HTTP error during member fetch: {e}")
                await asyncio.sleep(1)  # Brief pause on error
                continue
            if not data:
                break
            after = discord.Object(id=int(data[-1]["user"]["id"]))
            
            # Process batch
            batch_supporters = 0
            for raw_member in reversed(data):
                member = discord.Member(data=raw_member, guild=guild, state=guild._state)
                if member.bot:
                    continue
                    
                total_members += 1
                
                # For very large servers, prioritize status checking (no API call)
                if performance_mode and total_members > 10000:
                    # Only check status for performance (clan tags require API calls)
                    has_status = await self.check_supporter_status(member, "status")
                    if has_status:
                        counts["status"] += 1
                        unique_supporters.add(member.id)
                        batch_supporters += 1
                    
                    # Sample clan tag checking (every 10th member to estimate)
                    if total_members % 10 == 0:
                        has_tag = await self.check_supporter_status(member, "tag", raw_member["user"])
                        if has_tag:
                            counts["tag"] += 10  # Estimate based on sampling
                            unique_supporters.add(member.id)
                else:
                    # Full checking for smaller batches
                    has_tag = await self.check_supporter_status(member, "tag", raw_member["user"])
                    has_status = await self.check_supporter_status(member, "status")
                    
                    if has_tag:
                        counts["tag"] += 1
                        unique_supporters.add(member.id)
                        batch_supporters += 1
                    if has_status:
                        counts["status"] += 1
                        unique_supporters.add(member.id)
                        batch_supporters += 1
            
            processed_batches += 1
            
            # Progress logging for large servers (every 10 batches = ~1500 members)
            if processed_batches % 10 == 0:
                print(f"[OPC Scan] Processed {processed_batches * batch_size:,} members... {len(unique_supporters):,} supporters found")
            
            # Rate limiting delay - crucial for 17k server
            if delay > 0:
                await asyncio.sleep(delay)
                
            if len(data) < batch_size:
                break
        
        counts["total"] = len(unique_supporters)
        print(f"[OPC Scan Complete] {total_members:,} members processed, {counts['total']:,} total supporters found")
        
        # Update performance stats
        self.performance_stats["total_scanned"] = total_members
        
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
        
        # Get current counts for footer - optimized for large servers
        try:
            # Use cached counts if available to reduce load
            if hasattr(self, '_cached_counts') and (datetime.datetime.now() - self._cached_counts_time).seconds < 300:
                counts = self._cached_counts
            else:
                counts = await self.get_supporter_counts(member.guild)
                self._cached_counts = counts
                self._cached_counts_time = datetime.datetime.now()
            
            footer_text = f"OPC Supporters: {counts['tag']:,} Tags • {counts['status']:,} Status • {member.guild.name}"
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
        Enhanced with milestone checking for large server engagement.
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
            
            # Check for milestones after new supporters (not departures)
            if enabled:
                try:
                    counts = await self.get_supporter_counts(member.guild)
                    await self.check_and_announce_milestones(member.guild, counts)
                except Exception as e:
                    print(f"Error checking milestones: {e}")
                    
        except discord.HTTPException as e:
            # Error handling approach inspired by AAA3A's robust error management
            print(f"Failed to send announcement for member `{member.name}` ({member.id}) in guild `{member.guild.name}` ({member.guild.id}): {e}")

    async def check_opc_invite_in_status(self, status: str) -> bool:
        """
        Check if the OPC invite link is in the user's status.
        Regex pattern inspired by AAA3A's original invite detection logic.
        """
        # Look for discord.gg/onepiececommunity or variations
        invite_pattern = rf"discord\.(?:gg|io|me|li)\/{OPC_INVITE_CODE}|discord(?:app)?\.com\/invite\/{OPC_INVITE_CODE}"
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
        Optimized for large servers with enhanced caching.
        """
        if after.bot:
            return
            
        # Check if system is enabled
        if (
            not await self.config.guild(after.guild).enabled()
            or await self.bot.cog_disabled_in_guild(self, after.guild)
        ):
            return
            
        # Enhanced caching for large servers - prevent spam with longer cache times
        cache_key = f"{after.id}_presence"
        if self.cache.get(cache_key, False):
            return
        self.cache[cache_key] = True

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
            # Longer cache timeout for large servers (5 minutes)
            await asyncio.sleep(300)
            self.cache.pop(cache_key, None)

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
            
        # Enhanced caching for large servers
        cache_key = f"{after.id}_member"
        if self.cache.get(cache_key, False):
            return
        self.cache[cache_key] = True

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
            # Longer cache timeout for large servers (5 minutes)
            await asyncio.sleep(300)
            self.cache.pop(cache_key, None)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def setopcsupporters(self, ctx: commands.Context) -> None:
        """
        Settings for the OPC Supporters announcement system.
        Command structure inspired by AAA3A's configuration system.
        Optimized for large servers (17k+ members).
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
        if enabled and len([m for m in ctx.guild.members if not m.bot]) > 5000:
            embed.add_field(
                name="🏴‍☠️ Large Server Detected",
                value=f"Performance mode is recommended for servers with {len(ctx.guild.members):,} members. Use `{ctx.prefix}setopcsupporters performancemode True`",
                inline=False
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
            embed.add_field(
                name="💡 Large Server Tip",
                value="Consider creating a dedicated supporters channel to avoid spam in general channels.",
                inline=False
            )
        await ctx.send(embed=embed)

    @setopcsupporters.command()
    async def performancemode(self, ctx: commands.Context, enabled: bool) -> None:
        """Enable performance mode for large servers (recommended for 17k+ members)."""
        await self.config.guild(ctx.guild).performance_mode.set(enabled)
        
        embed = discord.Embed(
            title="⚡ Performance Mode",
            color=discord.Color.blue()
        )
        
        if enabled:
            embed.description = (
                "✅ **Performance mode enabled**\n\n"
                "🏴‍☠️ **Optimizations for 17k+ server:**\n"
                "• Reduced API calls for very large member counts\n"
                "• Batched member processing with rate limiting\n" 
                "• Smart caching to prevent duplicate processing\n"
                "• Progress logging during scans\n"
                "• Sampling for clan tag detection on huge servers"
            )
            embed.add_field(
                name="⚠️ Trade-offs",
                value="• Clan tag detection uses sampling for servers >10k members\n"
                      "• Status detection remains fully accurate\n"
                      "• Slightly longer scan times but more stable",
                inline=False
            )
        else:
            embed.description = "❌ **Performance mode disabled**\n\nFull functionality restored (not recommended for 17k+ servers)."
            embed.add_field(
                name="⚠️ Warning",
                value="Disabling performance mode on large servers may cause timeouts and instability.",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @setopcsupporters.command()
    async def scanbatchsize(self, ctx: commands.Context, size: int) -> None:
        """Set batch size for member scanning (recommended: 100-200 for 17k server)."""
        if size < 50 or size > 500:
            embed = discord.Embed(
                title="❌ Invalid Batch Size",
                description="Batch size must be between 50 and 500.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        await self.config.guild(ctx.guild).scan_batch_size.set(size)
        
        embed = discord.Embed(
            title="⚙️ Batch Size Updated",
            description=f"Member scanning batch size set to **{size}**.",
            color=discord.Color.green()
        )
        
        # Recommendations based on server size
        member_count = len([m for m in ctx.guild.members if not m.bot])
        if member_count > 15000:
            recommendation = "100-150 (very large server)"
        elif member_count > 10000:
            recommendation = "150-200 (large server)" 
        elif member_count > 5000:
            recommendation = "200-300 (medium-large server)"
        else:
            recommendation = "300-500 (smaller server)"
            
        embed.add_field(
            name=f"💡 Recommendation for {member_count:,} members",
            value=f"Optimal batch size: **{recommendation}**",
            inline=False
        )
        await ctx.send(embed=embed)

    @setopcsupporters.command()
    async def quiethours(self, ctx: commands.Context, start_hour: int, end_hour: int) -> None:
        """Set quiet hours for performance-intensive operations (24-hour format)."""
        if not (0 <= start_hour <= 23) or not (0 <= end_hour <= 23):
            embed = discord.Embed(
                title="❌ Invalid Hours",
                description="Hours must be between 0 and 23 (24-hour format).",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        await self.config.guild(ctx.guild).quiet_hours_start.set(start_hour)
        await self.config.guild(ctx.guild).quiet_hours_end.set(end_hour)
        
        embed = discord.Embed(
            title="🌙 Quiet Hours Set",
            description=f"Performance operations will be preferred during **{start_hour:02d}:00 - {end_hour:02d}:00**.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🏴‍☠️ Large Server Benefits",
            value="Scanning during quiet hours reduces server load and improves stability for 17k+ member servers.",
            inline=False
        )
        await ctx.send(embed=embed)

    @setopcsupporters.command()
    async def milestones(self, ctx: commands.Context, enabled: bool) -> None:
        """Enable or disable milestone celebration announcements."""
        await self.config.guild(ctx.guild).milestone_announcements.set(enabled)
        status = "enabled" if enabled else "disabled"
        
        embed = discord.Embed(
            title="🎉 Milestone Celebrations",
            description=f"Milestone announcements have been **{status}**.",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        
        if enabled:
            embed.add_field(
                name="🏆 Celebrations Include",
                value="• OPC clan tag milestones (10, 25, 50, 100, 250, 500, 1000+)\n"
                      "• Status invite milestones\n" 
                      "• Total supporter celebrations\n"
                      "• Special recognition for major achievements",
                inline=False
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
        
        # Performance mode
        perf_mode = "✅ Enabled" if guild_config["performance_mode"] else "❌ Disabled"
        embed.add_field(name="Performance Mode", value=perf_mode, inline=True)
        
        # Milestone celebrations
        milestones = "✅ Enabled" if guild_config["milestone_announcements"] else "❌ Disabled"
        embed.add_field(name="Milestone Celebrations", value=milestones, inline=True)
        
        # Announcement channel
        if guild_config["announcement_channel"]:
            channel = ctx.guild.get_channel(guild_config["announcement_channel"])
            channel_text = channel.mention if channel else "❌ Channel not found"
        else:
            channel_text = "❌ Not set"
        embed.add_field(name="Announcement Channel", value=channel_text, inline=True)
        
        # Performance settings
        embed.add_field(
            name="⚡ Performance Settings",
            value=f"• Batch Size: **{guild_config['scan_batch_size']}**\n"
                  f"• Scan Delay: **{guild_config['scan_delay']}s**\n"
                  f"• Quiet Hours: **{guild_config['quiet_hours_start']:02d}:00 - {guild_config['quiet_hours_end']:02d}:00**",
            inline=True
        )
        
        # Server info
        member_count = len([m for m in ctx.guild.members if not m.bot])
        embed.add_field(
            name="🏴‍☠️ Server Info",
            value=f"• Total Members: **{member_count:,}**\n"
                  f"• Large Server Optimized: **{'Yes' if member_count > 5000 else 'No'}**",
            inline=True
        )
        
        # What we track
        embed.add_field(
            name="📈 Tracking",
            value=f"• **{OPC_CLAN_TAG}** clan tag\n• **discord.gg/{OPC_INVITE_CODE}** in status",
            inline=False
        )
        
        embed.set_footer(text="Settings based on AAA3A's original configuration system • Optimized for large servers")
        await ctx.send(embed=embed)

    @setopcsupporters.command(aliases=["count", "stats"])
    async def supportercount(self, ctx: commands.Context) -> None:
        """
        Show current count of OPC supporters with large server optimizations.
        Statistics implementation inspired by AAA3A's data presentation methods.
        """
        member_count = len([m for m in ctx.guild.members if not m.bot])
        
        # Warning for very large scans
        if member_count > 10000:
            embed = discord.Embed(
                title="⏳ Large Server Scan Starting",
                description=f"Counting supporters across **{member_count:,}** members...\n\nThis may take 1-2 minutes for optimal accuracy.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🔍 Scanning Process",
                value="• Using optimized batching\n• Rate limiting for stability\n• Progress will be logged",
                inline=False
            )
            msg = await ctx.send(embed=embed)
        
        # Show typing indicator for better UX during count
        async with ctx.typing():
            start_time = datetime.datetime.now()
            counts = await self.get_supporter_counts(ctx.guild)
            scan_duration = (datetime.datetime.now() - start_time).total_seconds()
        
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
        if member_count > 0:
            tag_percent = (counts['tag'] / member_count) * 100
            status_percent = (counts['status'] / member_count) * 100
            total_percent = (counts['total'] / member_count) * 100
            
            embed.add_field(
                name="📊 Engagement Rate",
                value=f"**{total_percent:.1f}%** of members are supporters\n"
                      f"• Tag supporters: {tag_percent:.1f}%\n"
                      f"• Status supporters: {status_percent:.1f}%",
                inline=False
            )
        
        # Performance info for large servers
        if member_count > 5000:
            embed.add_field(
                name="⚡ Scan Performance",
                value=f"• Scanned **{member_count:,}** members in **{scan_duration:.1f}s**\n"
                      f"• Rate: **{member_count/scan_duration:.0f}** members/second\n"
                      f"• Using optimized large-server mode",
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
            text=f"One Piece Community • {member_count:,} Total Members • Stats system inspired by AAA3A",
            icon_url=ctx.guild.icon
        )
        
        if member_count > 10000:
            await msg.edit(embed=embed)
        else:
            await ctx.send(embed=embed)

    @setopcsupporters.command(aliases=["list"])
    async def listsupporters(self, ctx: commands.Context, _type: typing.Literal["tag", "status"]) -> None:
        """
        List all current OPC supporters by type.
        Member listing approach based on AAA3A's original implementation.
        Optimized for large servers.
        """
        member_count = len([m for m in ctx.guild.members if not m.bot])
        
        # Warning for large server listing
        if member_count > 10000:
            embed = discord.Embed(
                title="⏳ Large Server Listing",
                description=f"Scanning **{member_count:,}** members for {_type} supporters...\n\nThis may take 1-2 minutes.",
                color=discord.Color.blue()
            )
            msg = await ctx.send(embed=embed)
        
        supporters = []
        
        if _type == "tag":
            # Check all members for OPC clan tag - efficient scanning from AAA3A's method
            retrieve, after = 200, discord.guild.OLDEST_OBJECT  # Smaller batches for listing
            processed = 0
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
                    processed += 1
                    
                    # Progress update for large servers
                    if processed % 2000 == 0 and member_count > 10000:
                        print(f"[OPC List] Processed {processed:,} members, found {len(supporters)} {_type} supporters so far")
                    
                    if await self.check_supporter_status(member, "tag", raw_member["user"]):
                        supporters.append(member)
                        
                if len(data) < retrieve:
                    break
                    
                # Small delay for large servers
                if member_count > 10000:
                    await asyncio.sleep(0.1)
        else:
            # Check all members for OPC invite in status - more efficient for status
            for member in ctx.guild.members:
                if member.bot:
                    continue
                if await self.check_supporter_status(member, "status"):
                    supporters.append(member)

        support_method = "OPC Clan Tag" if _type == "tag" else "Invite Link in Status"
        embed: discord.Embed = discord.Embed(
            title=f"🏴‍☠️ {len(supporters):,} OPC Supporter{'' if len(supporters) == 1 else 's'} ({support_method})",
            color=await ctx.embed_color(),
            timestamp=ctx.message.created_at,
        )
        
        if supporters:
            # For large lists, show summary instead of all names
            if len(supporters) > 100:
                embed.description = f"**{len(supporters):,}** members are currently supporting with {support_method.lower()}.\n\n"
                
                # Show first 50 as examples
                sample_supporters = supporters[:50]
                description = "**Sample supporters:**\n" + "\n".join(f"• {member.mention}" for member in sample_supporters)
                if len(supporters) > 50:
                    description += f"\n... and **{len(supporters) - 50:,}** more!"
                
                embed.description += description[:1800]  # Discord limit
            else:
                description = "\n".join(f"• {member.mention}" for member in supporters)
                # Simple pagination for manageable lists
                if len(description) <= 2000:
                    embed.description = description
                else:
                    # Split into multiple embeds for long lists
                    pages = []
                    for page in pagify(description, page_length=2000):
                        e = embed.copy()
                        e.description = page
                        pages.append(e)
                    
                    # Send first page
                    if len(pages) > 1:
                        pages[0].set_footer(text=f"Page 1/{len(pages)} • Based on AAA3A's pagination design")
                    
                    if member_count > 10000:
                        await msg.edit(embed=pages[0])
                    else:
                        await ctx.send(embed=pages[0])
                    
                    # Send remaining pages
                    for i, page in enumerate(pages[1:], 2):
                        page.set_footer(text=f"Page {i}/{len(pages)} • One Piece Community")
                        await ctx.send(embed=page)
                    return
        else:
            embed.description = f"No current {support_method.lower()} supporters found."
        
        embed.set_footer(text=f"Large Server Optimized • {ctx.guild.name} • Listing based on AAA3A's design", icon_url=ctx.guild.icon)
        
        if member_count > 10000 and 'msg' in locals():
            await msg.edit(embed=embed)
        else:
            await ctx.send(embed=embed)

    @setopcsupporters.command()
    async def scan(self, ctx: commands.Context, force: bool = False) -> None:
        """
        Scan all members and initialize supporter tracking with large server optimizations.
        Scanning methodology based on AAA3A's force update implementation.
        """
        if self.scan_in_progress:
            embed = discord.Embed(
                title="⏳ Scan Already Running",
                description="A scan is already in progress. Please wait for it to complete.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        if not await self.config.guild(ctx.guild).enabled():
            embed = discord.Embed(
                title="❌ System Disabled",
                description="The OPC Supporters system is not enabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Check if it's quiet hours for large servers
        member_count = len([m for m in ctx.guild.members if not m.bot])
        is_quiet = await self.is_quiet_hours(ctx.guild)
        
        if not force and not is_quiet and member_count > 5000:
            config = await self.config.guild(ctx.guild).all()
            start_hour = config.get("quiet_hours_start", 3)
            end_hour = config.get("quiet_hours_end", 7)
            
            embed = discord.Embed(
                title="⏰ Performance Recommendation",
                description=f"🏴‍☠️ **Large server detected ({member_count:,} members)**\n\nFor optimal performance, consider running during quiet hours ({start_hour:02d}:00 - {end_hour:02d}:00).",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Options",
                value=f"• Wait for quiet hours\n• Use `{ctx.prefix}setopcsupporters scan force=True` to run now\n• Ensure performance mode is enabled",
                inline=False
            )
            embed.add_field(
                name="⚠️ Large Server Warning",
                value="Scanning 17k+ members may take 2-3 minutes and cause temporary load.",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        self.scan_in_progress = True
        
        embed = discord.Embed(
            title="🔍 Starting Large Server Scan",
            description=f"🏴‍☠️ Scanning **{member_count:,}** One Piece Community members...\n\nThis will take 2-3 minutes with performance optimizations.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="⚡ Large Server Optimizations",
            value="• Batched processing with rate limiting\n• Smart caching and progress logging\n• Anti-spam prevention during initialization",
            inline=False
        )
        
        msg = await ctx.send(embed=embed)
        
        try:
            start_time = datetime.datetime.now()
            
            # Progress update every 30 seconds for large scans
            async def progress_updater():
                while self.scan_in_progress:
                    await asyncio.sleep(30)
                    if self.scan_in_progress:
                        elapsed = (datetime.datetime.now() - start_time).total_seconds()
                        print(f"[OPC Scan Progress] {elapsed:.0f}s elapsed, still scanning...")
            
            # Start progress tracker for large servers
            if member_count > 10000:
                progress_task = asyncio.create_task(progress_updater())
            
            # Get supporter counts with optimizations
            counts = await self.get_supporter_counts(ctx.guild)
            end_time = datetime.datetime.now()
            scan_duration = (end_time - start_time).total_seconds()
            
            # Initialize tracking for all members
            print("[OPC Scan] Initializing supporter status tracking...")
            initialization_start = datetime.datetime.now()
            
            scanned = 0
            batch_size = 1000  # Larger batches for initialization
            members_batch = []
            
            for member in ctx.guild.members:
                if member.bot:
                    continue
                members_batch.append(member)
                
                if len(members_batch) >= batch_size:
                    # Process batch
                    for m in members_batch:
                        # Use existing counts where possible to avoid re-scanning
                        self.supporter_status[m.id]["tag"] = False  # Will be corrected by real-time monitoring
                        self.supporter_status[m.id]["status"] = False
                    
                    scanned += len(members_batch)
                    members_batch = []
                    
                    # Progress logging
                    if scanned % 5000 == 0:
                        print(f"[OPC Init] Initialized tracking for {scanned:,} members...")
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.1)
            
            # Process remaining members
            if members_batch:
                for m in members_batch:
                    self.supporter_status[m.id]["tag"] = False
                    self.supporter_status[m.id]["status"] = False
                scanned += len(members_batch)
            
            initialization_duration = (datetime.datetime.now() - initialization_start).total_seconds()
            
            # Cancel progress tracker
            if member_count > 10000:
                progress_task.cancel()
            
            embed = discord.Embed(
                title="✅ Large Server Scan Complete",
                description=f"🏴‍☠️ Successfully processed **{member_count:,}** One Piece Community members!",
                color=discord.Color.green(),
                timestamp=ctx.message.created_at
            )
            embed.add_field(name="🏷️ OPC Clan Tag", value=f"**{counts['tag']:,}**", inline=True)
            embed.add_field(name="💬 Status Invites", value=f"**{counts['status']:,}**", inline=True)
            embed.add_field(name="👥 Total Unique", value=f"**{counts['total']:,}**", inline=True)
            
            embed.add_field(
                name="⚡ Performance Stats",
                value=f"• **{scan_duration:.1f}s** scan time\n"
                      f"• **{member_count/scan_duration:.0f}** members/second\n"
                      f"• **{initialization_duration:.1f}s** initialization\n"
                      f"• Large server optimizations active",
                inline=False
            )
            
            # Calculate engagement for 17k server
            if member_count > 0:
                engagement = (counts["total"] / member_count) * 100
                embed.add_field(
                    name="📊 Community Engagement",
                    value=f"**{engagement:.1f}%** of your **{member_count:,}** members are active supporters!\n🎉 That's amazing for a server this size!",
                    inline=False
                )
            
            embed.add_field(
                name="🚀 Status",
                value="• Tracking initialized for all members\n• Real-time monitoring active\n• Milestone celebrations ready\n• Ready for supporter announcements!",
                inline=False
            )
            
            embed.set_footer(text="Large server scan complete • Based on AAA3A's scanning system • Optimized for 17k+ members")
            
            await msg.edit(embed=embed)
            self.last_scan_time = datetime.datetime.now()
            self.performance_stats["last_scan_duration"] = scan_duration
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Scan Failed",
                description=f"An error occurred during large server scanning: {str(e)}",
                color=discord.Color.red()
            )
            embed.add_field(
                name="💡 Troubleshooting",
                value="• Try enabling performance mode\n• Reduce batch size\n• Run during quiet hours\n• Contact support if issues persist",
                inline=False
            )
            await msg.edit(embed=embed)
        finally:
            self.scan_in_progress = False
