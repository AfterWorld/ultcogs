import discord
import asyncio
import logging
from typing import Set

from redbot.core import commands
from redbot.core.commands import Cog

log = logging.getLogger("red.grilled")


class Grilled(Cog):
    """
    A dramatic ban command with a 10-second countdown.
    
    Adds some flair to your moderation with a countdown before banning users.
    """
    
    def __init__(self, bot):
        self.bot = bot
        # Track active grill sessions to prevent spam
        self.active_grills: Set[int] = set()

    async def red_delete_data_for_user(self, **kwargs):
        """Required method for Red v3 data deletion compliance."""
        # This cog doesn't store user-specific data
        return

    @commands.command(name="grill")
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def grill(self, ctx, member: discord.Member, *, reason: str = "You've been grilled!"):
        """
        Ban a member with a dramatic 10-second countdown.
        
        **Arguments:**
        - `member` - The member to ban
        - `reason` - Optional reason for the ban (default: "You've been grilled!")
        
        **Examples:**
        - `[p]grill @baduser`
        - `[p]grill @spammer Spam and trolling`
        """
        # Prevent duplicate grill sessions
        if member.id in self.active_grills:
            return await ctx.send("❌ This user is already being grilled!")
        
        # Safety checks
        if not await self._can_grill_member(ctx, member):
            return
            
        self.active_grills.add(member.id)
        
        try:
            # Initial message
            embed = discord.Embed(
                title="🔥 Grill Protocol Initiated",
                description=f"🔥 Initiating grill protocol for {member.mention}... Countdown starting.",
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Reason: {reason}")
            countdown_message = await ctx.send(embed=embed)
            
            # Countdown from 10 to 1
            for i in range(10, 0, -1):
                embed = discord.Embed(
                    title="🔥 Grill Protocol Active",
                    description=f"**{i}** seconds remaining...",
                    color=discord.Color.red() if i <= 3 else discord.Color.orange()
                )
                embed.add_field(name="Target", value=member.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=True)
                embed.set_footer(text="Use 'cancel' to abort")
                await countdown_message.edit(embed=embed)
                
                # Check for cancellation
                try:
                    def check(msg):
                        return (msg.author == ctx.author and 
                               msg.channel == ctx.channel and 
                               msg.content.lower() == "cancel")
                    
                    await self.bot.wait_for('message', check=check, timeout=1.0)
                    await countdown_message.edit(
                        embed=discord.Embed(
                            title="❌ Cancelled",
                            description="Grill protocol cancelled.",
                            color=discord.Color.gray()
                        )
                    )
                    return
                except asyncio.TimeoutError:
                    pass
            
            # Final dramatic message
            embed = discord.Embed(
                title="💥 GRILLED!",
                description=f"💥 {member.mention}, you've been grilled! 🔥",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Banned by {ctx.author}")
            await countdown_message.edit(embed=embed)
            
            # Execute the ban
            await member.ban(reason=f"Grilled by {ctx.author}: {reason}")
            
            # Confirmation message
            await ctx.send(f"{member} has been banned from the server.", delete_after=10)
            
            log.info(f"User {member} ({member.id}) was grilled by {ctx.author} in {ctx.guild}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban this member!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to ban member: {str(e)}")
        except Exception as e:
            log.error(f"Unexpected error in grill command: {e}", exc_info=True)
            await ctx.send("❌ An unexpected error occurred. Check the logs.")
        finally:
            self.active_grills.discard(member.id)

    async def _can_grill_member(self, ctx, member: discord.Member) -> bool:
        """Check if the member can be safely grilled."""
        
        # Can't grill yourself
        if member == ctx.author:
            await ctx.send("❌ You can't grill yourself!")
            return False
        
        # Can't grill the bot
        if member == ctx.me:
            await ctx.send("❌ I refuse to grill myself!")
            return False
        
        # Can't grill the server owner
        if member == ctx.guild.owner:
            await ctx.send("❌ You can't grill the server owner!")
            return False
        
        # Check role hierarchy
        if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            await ctx.send("❌ You can't grill someone with equal or higher roles!")
            return False
        
        if member.top_role >= ctx.me.top_role:
            await ctx.send("❌ I can't grill someone with a higher role than me!")
            return False
        
        return True

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors gracefully."""
        if not isinstance(error, commands.CommandInvokeError):
            return
        
        if ctx.command and ctx.command.qualified_name == "grill":
            # Clean up active grill sessions on error
            if hasattr(ctx, 'args') and len(ctx.args) > 2:
                member = ctx.args[2]
                if isinstance(member, discord.Member):
                    self.active_grills.discard(member.id)
