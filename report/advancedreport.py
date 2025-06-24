import discord
from discord.ext import commands
from redbot.core import commands as red_commands, Config, checks
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import json
import time

log = logging.getLogger("red.advancedreport")

class ReportView(discord.ui.View):
    """Interactive view with quick action buttons for staff"""
    
    def __init__(self, cog, report_data: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.report_data = report_data
        self.processed = False
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only staff can use the buttons"""
        return await self.cog.is_staff_member(interaction.user, interaction.guild)
    
    @discord.ui.button(label="Mute", style=discord.ButtonStyle.secondary, emoji="🔇")
    async def mute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mute the reported user"""
        if self.processed:
            await interaction.response.send_message("❌ Already processed", ephemeral=True)
            return
            
        try:
            user_id = self.report_data['reported_user_id']
            member = interaction.guild.get_member(user_id)
            
            if not member:
                await interaction.response.send_message("❌ User not found", ephemeral=True)
                return
            
            # Simple 60 minute timeout
            await member.timeout(
                discord.utils.utcnow() + discord.timedelta(minutes=60), 
                reason=f"Report action by {interaction.user}"
            )
            
            await self.mark_processed(interaction, "🔇 User muted for 60 minutes")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ No permission to mute", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ban the reported user"""
        if self.processed:
            await interaction.response.send_message("❌ Already processed", ephemeral=True)
            return
            
        try:
            user_id = self.report_data['reported_user_id']
            reason = f"Report ban by {interaction.user}"
            
            await interaction.guild.ban(discord.Object(id=user_id), reason=reason)
            await self.mark_processed(interaction, "🔨 User banned")
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ No permission to ban", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Caution", style=discord.ButtonStyle.primary, emoji="⚠️")
    async def caution_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Issue a caution"""
        if self.processed:
            await interaction.response.send_message("❌ Already processed", ephemeral=True)
            return
            
        try:
            user_id = self.report_data['reported_user_id']
            member = interaction.guild.get_member(user_id)
            
            if not member:
                await interaction.response.send_message("❌ User not found", ephemeral=True)
                return
            
            # Check for Cautions cog
            cautions_cog = self.cog.bot.get_cog("Cautions")
            if cautions_cog:
                await self.issue_caution_with_cog(interaction, member, cautions_cog)
            else:
                await self.issue_simple_warning(interaction, member)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def issue_caution_with_cog(self, interaction, member, cautions_cog):
        """Issue caution using Cautions cog"""
        try:
            points = 1  # Simple default
            reason = f"Report: {self.report_data['reason']}"
            
            # Create warning structure
            warning = {
                "points": points,
                "reason": reason,
                "moderator_id": interaction.user.id,
                "timestamp": datetime.now(timezone.utc).timestamp(),
            }
            
            # Add to warnings
            async with cautions_cog.config.member(member).warnings() as warnings_list:
                warnings_list.append(warning)
            
            # Update total points
            total_points = sum(w.get("points", 1) for w in await cautions_cog.config.member(member).warnings())
            await cautions_cog.config.member(member).total_points.set(total_points)
            
            await self.mark_processed(interaction, f"⚠️ Caution issued - Total: {total_points} points")
            
        except Exception as e:
            log.exception("Caution error, falling back")
            await self.issue_simple_warning(interaction, member)
    
    async def issue_simple_warning(self, interaction, member):
        """Simple warning fallback"""
        try:
            # Try to DM user
            try:
                embed = discord.Embed(
                    title="⚠️ Warning",
                    description=f"You received a warning in **{interaction.guild.name}**",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Reason", value=self.report_data['reason'], inline=False)
                await member.send(embed=embed)
                dm_status = "✅ User notified"
            except:
                dm_status = "⚠️ Could not DM user"
            
            await self.mark_processed(interaction, f"⚠️ Warning issued - {dm_status}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.success, emoji="✅")
    async def dismiss_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Dismiss the report"""
        if self.processed:
            await interaction.response.send_message("❌ Already processed", ephemeral=True)
            return
            
        await self.mark_processed(interaction, "✅ Report dismissed")
    
    async def mark_processed(self, interaction: discord.Interaction, status: str):
        """Mark report as processed"""
        self.processed = True
        
        # Get original embed
        original_embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if original_embed:
            # Create updated embed
            embed = discord.Embed(
                title=original_embed.title,
                description=original_embed.description,
                color=discord.Color.green()
            )
            
            # Copy fields
            for field in original_embed.fields:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)
            
            # Add status
            embed.add_field(name="📋 Status", value=status, inline=False)
            embed.add_field(name="🔧 Processed by", value=interaction.user.mention, inline=True)
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message(f"✅ {status}", ephemeral=True)

class AdvancedReport(red_commands.Cog):
    """Advanced reporting system with context menus and quick actions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890987654321, force_registration=True)
        
        # Register config
        self.config.register_guild(
            report_channel=None,
            staff_roles=[],
            ping_staff=True,
            log_channel=None,
            default_mute_duration=60,
            blacklisted_users=[],
            default_caution_points=1
        )
        
        self.config.register_member(
            warnings=[],
            report_count=0,
            total_points=0,
            applied_thresholds=[]
        )
        
        self.config.register_global(
            total_reports=0
        )
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        self.bot.add_view(ReportView(self, {}))
        log.info("AdvancedReport cog loaded successfully")
    
    def cog_unload(self):
        """Called when the cog is unloaded"""
        log.info("AdvancedReport cog unloaded")
    
    async def is_staff_member(self, user: discord.Member, guild: discord.Guild) -> bool:
        """Check if user is staff"""
        if user.guild_permissions.administrator:
            return True
            
        staff_roles = await self.config.guild(guild).staff_roles()
        user_role_ids = [role.id for role in user.roles]
        return any(role_id in user_role_ids for role_id in staff_roles)
    
    async def is_blacklisted(self, user_id: int, guild: discord.Guild) -> bool:
        """Check if user is blacklisted"""
        blacklisted = await self.config.guild(guild).blacklisted_users()
        return user_id in blacklisted
    
    async def get_caution_points(self, guild: discord.Guild) -> int:
        """Get configured caution points"""
        try:
            points = await self.config.guild(guild).default_caution_points()
            return max(1, min(10, points))
        except:
            return 1
    
    # Configuration commands
    @red_commands.group(name="reportset", aliases=["rset"])
    @checks.admin_or_permissions(administrator=True)
    async def report_settings(self, ctx):
        """Configure the report system"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @report_settings.command(name="channel")
    async def set_report_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the report channel"""
        if channel is None:
            channel = ctx.channel
        
        await self.config.guild(ctx.guild).report_channel.set(channel.id)
        await ctx.send(f"✅ Report channel set to {channel.mention}")
    
    @report_settings.command(name="staffroles")
    async def set_staff_roles(self, ctx, *roles: discord.Role):
        """Set staff roles"""
        if not roles:
            await ctx.send("❌ Please specify at least one role")
            return
        
        role_ids = [role.id for role in roles]
        await self.config.guild(ctx.guild).staff_roles.set(role_ids)
        
        role_mentions = [role.mention for role in roles]
        await ctx.send(f"✅ Staff roles set to: {', '.join(role_mentions)}")
    
    @report_settings.command(name="view")
    async def view_settings(self, ctx):
        """View current settings"""
        settings = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(title="📋 Report Settings", color=discord.Color.blue())
        
        # Report channel
        channel = ctx.guild.get_channel(settings['report_channel'])
        embed.add_field(
            name="Report Channel",
            value=channel.mention if channel else "Not set",
            inline=True
        )
        
        # Staff roles
        staff_roles = [ctx.guild.get_role(role_id) for role_id in settings['staff_roles']]
        staff_roles = [role.mention for role in staff_roles if role]
        embed.add_field(
            name="Staff Roles",
            value=', '.join(staff_roles) if staff_roles else "Not set",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @report_settings.command(name="integration")
    async def check_integration(self, ctx):
        """Check Cautions cog integration"""
        cautions_cog = self.bot.get_cog("Cautions")
        
        embed = discord.Embed(title="🔗 Integration Status", color=discord.Color.blue())
        
        if cautions_cog:
            embed.add_field(
                name="⚠️ Cautions Cog",
                value="✅ **Available** - Caution button will use Cautions system",
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ Cautions Cog",
                value="❌ **Not Available** - Will use simple warning system",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    # Report commands
    @red_commands.command(name="report")
    async def report_command(self, ctx, user: discord.Member, *, reason: str):
        """Report a user to staff"""
        # Validation
        if await self.is_blacklisted(ctx.author.id, ctx.guild):
            await ctx.send("❌ You are blacklisted from reporting.", delete_after=10)
            return
        
        if user == ctx.author:
            await ctx.send("❌ You cannot report yourself!", delete_after=10)
            return
        
        if user.bot:
            await ctx.send("❌ You cannot report bots!", delete_after=10)
            return
        
        if await self.is_staff_member(user, ctx.guild):
            await ctx.send("❌ You cannot report staff members!", delete_after=10)
            return
        
        # Process the report
        await self.create_report(ctx.guild, ctx.author, user, reason, ctx.message, ctx.channel)
        
        # Clean up
        try:
            await ctx.message.delete()
        except:
            pass
        
        # Confirm
        try:
            await ctx.author.send(f"✅ Your report against **{user}** has been submitted.")
        except:
            await ctx.send(f"✅ {ctx.author.mention}, your report submitted.", delete_after=10)
    
    async def create_report(self, guild: discord.Guild, reporter: discord.User, 
                          reported_user: discord.User, reason: str, 
                          source_message: discord.Message, source_channel: discord.TextChannel):
        """Create and send a report"""
        
        # Get report channel
        report_channel_id = await self.config.guild(guild).report_channel()
        if not report_channel_id:
            log.warning(f"No report channel set for guild {guild.id}")
            return
        
        report_channel = guild.get_channel(report_channel_id)
        if not report_channel:
            log.warning(f"Report channel not found for guild {guild.id}")
            return
        
        # Generate simple report ID
        try:
            report_count = await self.config.global.total_reports()
            report_count += 1
            await self.config.global.total_reports.set(report_count)
            report_id = f"RPT-{report_count:06d}"
        except Exception as e:
            log.warning(f"Error with report count: {e}")
            report_id = f"RPT-{int(time.time())}"
        
        # Create embed
        embed = discord.Embed(
            title="🚨 New Report",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="📋 Report ID", value=f"`{report_id}`", inline=True)
        embed.add_field(name="👤 Reported User", value=f"{reported_user.mention}\n`{reported_user}` (ID: {reported_user.id})", inline=True)
        embed.add_field(name="👮 Reporter", value=f"{reporter.mention}\n`{reporter}` (ID: {reporter.id})", inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.add_field(name="📍 Channel", value=source_channel.mention, inline=True)
        
        # Add message link if available
        if source_message:
            embed.add_field(name="🔗 Message Link", value=f"[Jump to Message]({source_message.jump_url})", inline=True)
            
            if source_message.content:
                content = source_message.content[:300]
                if len(source_message.content) > 300:
                    content += "..."
                embed.add_field(name="💬 Message Content", value=f"```{content}```", inline=False)
        
        embed.set_footer(text="Report submitted")
        if reporter.avatar:
            embed.set_author(name=f"Report by {reporter}", icon_url=reporter.avatar.url)
        
        # Create report data
        report_data = {
            'report_id': report_id,
            'reporter_id': reporter.id,
            'reported_user_id': reported_user.id,
            'reason': reason,
            'guild_id': guild.id
        }
        
        # Create view
        view = ReportView(self, report_data)
        
        # Get staff roles for pinging
        staff_roles = await self.config.guild(guild).staff_roles()
        content = ""
        if staff_roles:
            staff_mentions = [f"<@&{role_id}>" for role_id in staff_roles]
            content = f"🚨 **New Report** - Staff attention needed\n{' '.join(staff_mentions)}"
        
        # Send the report
        try:
            await report_channel.send(content=content, embed=embed, view=view)
            log.info(f"Report {report_id} sent to {report_channel.name}")
        except Exception as e:
            log.exception(f"Error sending report: {e}")

# Setup function
async def setup(bot):
    await bot.add_cog(AdvancedReport(bot))
