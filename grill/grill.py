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
            # Emoji countdown mapping
            countdown_emojis = {
                10: "🔟", 9: "9️⃣", 8: "8️⃣", 7: "7️⃣", 6: "6️⃣",
                5: "5️⃣", 4: "4️⃣", 3: "3️⃣", 2: "2️⃣", 1: "1️⃣"
            }
            
            # Funny troll messages for each countdown number
            troll_messages = {
                10: "Hope you said your goodbyes! 👋",
                9: "This is your last chance to run! 🏃‍♂️",
                8: "The grill is heating up... 🔥",
                7: "Someone's about to become crispy! 🥓",
                6: "I can smell the fear from here 👃",
                5: "Half way to DESTRUCTION! 💀",
                4: "The hammer is about to drop! 🔨",
                3: "THREE... getting spicy now! 🌶️",
                2: "TWO... almost OBLITERATED! ⚡",
                1: "ONE... say hello to the void! 🕳️"
            }
            
            # Initial dramatic message
            embed = discord.Embed(
                title="🚨 GRILL PROTOCOL ACTIVATED 🚨",
                description=f"**TARGET ACQUIRED**: {member.mention}\n\n🔥 **PREPARING THE ULTIMATE GRILL** 🔥\n\n*The countdown of DOOM begins...*",
                color=discord.Color.from_rgb(255, 69, 0)  # Red-orange
            )
            embed.add_field(name="🎯 VICTIM", value=member.display_name, inline=True)
            embed.add_field(name="⚖️ CRIME", value=reason, inline=True)
            embed.add_field(name="👨‍⚖️ EXECUTIONER", value=ctx.author.display_name, inline=True)
            embed.set_footer(text="💬 Type 'cancel' to abort this nuclear launch | ⏰ T-minus 10 seconds")
            embed.set_thumbnail(url="https://www.icegif.com/wp-content/uploads/2023/03/icegif-1433.gif")  
            
            countdown_message = await ctx.send(embed=embed)
            
            # Countdown from 10 to 1 with rate limiting consideration
            for i in range(10, 0, -1):
                emoji = countdown_emojis[i]
                troll_msg = troll_messages[i]
                
                # Color gets more intense as countdown decreases
                if i >= 7:
                    color = discord.Color.orange()
                elif i >= 4:
                    color = discord.Color.from_rgb(255, 140, 0)  # Dark orange
                else:
                    color = discord.Color.red()
                
                embed = discord.Embed(
                    title=f"🚨 {emoji} GRILL COUNTDOWN {emoji} 🚨",
                    description=f"**{member.mention}** is about to be **OBLITERATED**!\n\n{emoji} **{i}** {emoji}\n\n*{troll_msg}*",
                    color=color
                )
                
                embed.add_field(name="🎯 TARGET", value=f"{member.display_name}\n💀 *Soon to be deleted*", inline=True)
                embed.add_field(name="⚖️ CHARGES", value=f"{reason}\n🔥 *Guilty as charged*", inline=True)
                embed.add_field(name="⏰ TIME LEFT", value=f"**{i} SECOND{'S' if i != 1 else ''}**\n💥 *Until BOOM*", inline=True)
                
                # Add progressively more dramatic footer messages
                if i > 5:
                    footer_text = f"💬 Type 'cancel' to spare this soul | ⚡ {member.display_name} is sweating bullets"
                elif i > 2:
                    footer_text = f"💬 Last chance to type 'cancel'! | 😰 {member.display_name} is panicking"
                else:
                    footer_text = f"💀 TOO LATE TO CANCEL NOW | 🔥 {member.display_name}'s fate is SEALED"
                
                embed.set_footer(text=footer_text)
                
                await countdown_message.edit(embed=embed)
                
                # Check for cancellation with slightly longer timeout to reduce API calls
                try:
                    def check(msg):
                        return (msg.author == ctx.author and 
                               msg.channel == ctx.channel and 
                               msg.content.lower() == "cancel")
                    
                    await self.bot.wait_for('message', check=check, timeout=1.0)
                    
                    # Cancellation embed
                    cancel_embed = discord.Embed(
                        title="🛑 GRILL PROTOCOL ABORTED 🛑",
                        description=f"**{member.mention}** has been **SPARED**!\n\n😌 *The gods have shown mercy today...*\n\n🕊️ **CANCELLATION SUCCESSFUL** 🕊️",
                        color=discord.Color.green()
                    )
                    cancel_embed.add_field(name="💝 LUCKY SURVIVOR", value=member.display_name, inline=True)
                    cancel_embed.add_field(name="😇 MERCIFUL MODERATOR", value=ctx.author.display_name, inline=True)
                    cancel_embed.add_field(name="⏰ STOPPED AT", value=f"{i} second{'s' if i != 1 else ''} remaining", inline=True)
                    cancel_embed.set_footer(text=f"🎉 {member.display_name} lives to troll another day!")
                    
                    await countdown_message.edit(embed=cancel_embed)
                    return
                except asyncio.TimeoutError:
                    pass
                
                # Small delay to prevent API spam (Discord allows ~5 edits per 5 seconds)
                await asyncio.sleep(1.1)
            
            # Final DESTRUCTION message
            final_embed = discord.Embed(
                title="💥🔥 ABSOLUTELY GRILLED 🔥💥",
                description=f"**{member.mention}** has been **COMPLETELY OBLITERATED**!\n\n💀 *Rest in pieces* 💀\n\n🔥 **MAXIMUM GRILL ACHIEVED** 🔥",
                color=discord.Color.dark_red()
            )
            final_embed.add_field(name="⚰️ VICTIM", value=f"~~{member.display_name}~~\n*Gone but not forgotten*", inline=True)
            final_embed.add_field(name="🔨 DESTROYER", value=f"{ctx.author.display_name}\n*The Merciless*", inline=True)
            final_embed.add_field(name="💀 FINAL BLOW", value=f"{reason}\n*DEVASTATING*", inline=True)
            final_embed.set_footer(text=f"🪦 {member.display_name} was absolutely destroyed | 🔥 Another one bites the dust")
            
            await countdown_message.edit(embed=final_embed)
            
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
