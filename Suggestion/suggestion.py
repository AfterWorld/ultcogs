from __future__ import annotations
import discord
import logging
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from typing import Optional

from .constants import DEFAULT_CONFIG, COLORS, STATUS_EMOJIS
from .utils import error_embed, success_embed, iso_now, cooldown_passed
from .integration import RewardSystem

log = logging.getLogger("red.suggestions")

class Suggestion(commands.Cog):
    """Thread-based suggestion system with interactive setup."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9999999999, force_registration=True)
        self.config.register_guild(**DEFAULT_CONFIG)
        self.rewarder = RewardSystem(self)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def suggest(self, ctx: commands.Context, *, text: str):
        """Submit a suggestion. Use '--anon' to hide your name."""
        guild = ctx.guild
        author = ctx.author
        conf = await self.config.guild(guild).all()

        # Check if user is blacklisted
        if author.id in conf["blacklisted_users"]:
            return await ctx.send(embed=error_embed("You are not allowed to submit suggestions."))

        # Check cooldown
        cooldowns = conf.get("cooldown_per_day", 1)
        stats = conf.get("stats", {})
        user_stats = stats.get(str(author.id), {})
        last_time = user_stats.get("last_submit", "1970-01-01T00:00:00")

        if not cooldown_passed(last_time, cooldowns):
            return await ctx.send(embed=error_embed("You've reached your daily suggestion limit."))

        # Get suggestion channel
        suggestion_channel = guild.get_channel(conf["suggestion_channel"])
        if not suggestion_channel:
            return await ctx.send(embed=error_embed("Suggestion channel is not set. Use `.suggestcreate` to configure."))

        next_id = conf["next_id"]
        anon = text.startswith("--anon")
        content = text[7:].strip() if anon else text.strip()

        # Create initial embed for the thread starter message
        embed = discord.Embed(
            title=f"{STATUS_EMOJIS['pending']} Suggestion #{next_id}",
            description=content[:2048],
            color=COLORS["pending"]
        )
        embed.add_field(name="Status", value="⏳ Pending", inline=True)
        embed.add_field(name="Votes", value="👍 0 | 👎 0", inline=True)
        
        if not anon:
            embed.set_footer(text=f"Suggested by {author.display_name}", icon_url=author.display_avatar.url)
        else:
            embed.set_footer(text="Anonymous Suggestion")

        # Send the message and create a thread
        msg = await suggestion_channel.send(embed=embed)
        
        try:
            thread = await msg.create_thread(
                name=f"Suggestion #{next_id}: {content[:80]}",
                auto_archive_duration=10080  # 7 days
            )
            
            # Add reactions to the main message
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
            
            # Send info message in thread
            info_embed = discord.Embed(
                description=f"💬 Discuss this suggestion here!\n\n**Original Suggestion:**\n{content[:1900]}",
                color=COLORS["pending"]
            )
            if not anon:
                info_embed.set_author(name=f"Submitted by {author.display_name}", icon_url=author.display_avatar.url)
            await thread.send(embed=info_embed)
            
        except discord.HTTPException as e:
            log.error(f"Failed to create thread: {e}")
            return await ctx.send(embed=error_embed("Failed to create suggestion thread."))

        # Save suggestion data
        await self.config.guild(guild).suggestions.set_raw(str(next_id), value={
            "id": next_id,
            "author_id": author.id,
            "message_id": msg.id,
            "thread_id": thread.id,
            "channel_id": msg.channel.id,
            "suggestion": content,
            "status": "pending",
            "timestamp": iso_now(),
            "anon": anon,
            "upvotes": 0,
            "downvotes": 0,
            "notified_staff": False
        })
        await self.config.guild(guild).next_id.set(next_id + 1)

        # Update user stats
        user_stats["submitted"] = user_stats.get("submitted", 0) + 1
        user_stats["last_submit"] = iso_now()
        stats[str(author.id)] = user_stats
        await self.config.guild(guild).stats.set(stats)

        # Delete the command message to keep channel clean
        try:
            await ctx.message.delete()
        except:
            pass

        await ctx.send(embed=success_embed(f"✅ Suggestion #{next_id} submitted! Check the thread for discussion."), delete_after=10)

        # Award credits if configured
        reward_amt = conf.get("reward_credits", 0)
        if reward_amt > 0:
            await self.rewarder.award(guild, author.id, reward_amt, suggestion_id=next_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle voting on suggestions"""
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) not in {"👍", "👎"}:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        conf = await self.config.guild(guild).all()
        suggestion_data = conf["suggestions"]
        
        # Find the suggestion by message_id
        target_id = None
        for sid, entry in suggestion_data.items():
            if entry.get("message_id") == payload.message_id:
                target_id = sid
                break
        
        if not target_id:
            return

        data = suggestion_data[target_id]
        if data.get("status") != "pending":
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Count votes
        upvotes = 0
        downvotes = 0
        for r in message.reactions:
            if str(r.emoji) == "👍":
                upvotes = r.count - 1  # Subtract bot's reaction
            elif str(r.emoji) == "👎":
                downvotes = r.count - 1

        # Update the embed with current vote counts
        embed = message.embeds[0]
        embed.set_field_at(1, name="Votes", value=f"👍 {upvotes} | 👎 {downvotes}", inline=True)
        await message.edit(embed=embed)

        # Update stored vote counts
        data["upvotes"] = upvotes
        data["downvotes"] = downvotes
        await self.config.guild(guild).suggestions.set_raw(target_id, value=data)

        # Check if we should notify staff
        staff_threshold = conf.get("staff_notification_threshold", 5)
        if upvotes >= staff_threshold and not data.get("notified_staff", False):
            await self._notify_staff(guild, data, message)
            data["notified_staff"] = True
            await self.config.guild(guild).suggestions.set_raw(target_id, value=data)

        # Auto-approve/decline based on thresholds
        if upvotes >= conf["upvote_threshold"]:
            await self._resolve(message, guild, data, approved=True)
        elif downvotes >= conf["downvote_threshold"]:
            await self._resolve(message, guild, data, approved=False)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle vote removal"""
        if str(payload.emoji) not in {"👍", "👎"}:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        conf = await self.config.guild(guild).all()
        suggestion_data = conf["suggestions"]
        
        target_id = None
        for sid, entry in suggestion_data.items():
            if entry.get("message_id") == payload.message_id:
                target_id = sid
                break
        
        if not target_id:
            return

        data = suggestion_data[target_id]
        if data.get("status") != "pending":
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Update vote counts
        upvotes = 0
        downvotes = 0
        for r in message.reactions:
            if str(r.emoji) == "👍":
                upvotes = r.count - 1
            elif str(r.emoji) == "👎":
                downvotes = r.count - 1

        embed = message.embeds[0]
        embed.set_field_at(1, name="Votes", value=f"👍 {upvotes} | 👎 {downvotes}", inline=True)
        await message.edit(embed=embed)

        data["upvotes"] = upvotes
        data["downvotes"] = downvotes
        await self.config.guild(guild).suggestions.set_raw(target_id, value=data)

    async def _notify_staff(self, guild: discord.Guild, data: dict, message: discord.Message):
        """Notify staff channel when suggestion reaches threshold"""
        staff_channel_id = await self.config.guild(guild).staff_channel()
        if not staff_channel_id:
            return

        staff_channel = guild.get_channel(staff_channel_id)
        if not staff_channel:
            return

        author = guild.get_member(data["author_id"]) or self.bot.get_user(data["author_id"])
        
        embed = discord.Embed(
            title=f"🔔 Suggestion #{data['id']} Needs Review",
            description=data["suggestion"][:2048],
            color=discord.Color.gold()
        )
        embed.add_field(name="Votes", value=f"👍 {data['upvotes']} | 👎 {data['downvotes']}", inline=True)
        embed.add_field(name="Status", value="⏳ Pending Review", inline=True)
        
        if author and not data.get("anon"):
            embed.set_author(name=f"Submitted by {author.display_name}", icon_url=author.display_avatar.url)
        else:
            embed.set_author(name="Anonymous Suggestion")
        
        embed.add_field(name="Actions", value=f"Use `.suggestconfig approve {data['id']}` or `.suggestconfig decline {data['id']}`", inline=False)
        embed.add_field(name="Link", value=f"[Jump to Suggestion]({message.jump_url})", inline=False)
        
        await staff_channel.send(embed=embed)

    async def _resolve(self, msg: discord.Message, guild: discord.Guild, data: dict, approved: bool):
        """Resolve a suggestion (approve or decline)"""
        sid = str(data["id"])
        embed = msg.embeds[0]
        status = "✅ Approved" if approved else "❌ Declined"
        color = COLORS["approved"] if approved else COLORS["declined"]
        emoji = STATUS_EMOJIS["approved"] if approved else STATUS_EMOJIS["declined"]

        author = guild.get_member(data["author_id"]) or self.bot.get_user(data["author_id"])
        
        # Update embed
        embed.color = color
        embed.title = f"{emoji} Suggestion #{sid}"
        embed.set_field_at(0, name="Status", value=status, inline=True)
        
        await msg.edit(embed=embed)

        # Archive the thread
        thread = guild.get_thread(data.get("thread_id"))
        if thread:
            try:
                archive_msg = discord.Embed(
                    description=f"**This suggestion has been {status.lower()}.**",
                    color=color
                )
                await thread.send(embed=archive_msg)
                await thread.edit(archived=True, locked=True)
            except:
                pass

        # Send to archive channel
        archive_id = await self.config.guild(guild).archive_channel()
        if archive_id:
            archive = guild.get_channel(archive_id)
            if archive:
                archive_embed = embed.copy()
                archive_embed.add_field(name="Link", value=f"[Original Message]({msg.jump_url})", inline=False)
                await archive.send(embed=archive_embed)

        # Log the resolution
        log_id = await self.config.guild(guild).log_channel()
        if log_id:
            log_chan = guild.get_channel(log_id)
            if log_chan:
                log_embed = discord.Embed(
                    title=f"Suggestion {status}",
                    description=f"**Suggestion #{sid}** has been {status.lower()}",
                    color=color
                )
                log_embed.add_field(name="Votes", value=f"👍 {data['upvotes']} | 👎 {data['downvotes']}", inline=True)
                if author and not data.get("anon"):
                    log_embed.add_field(name="Author", value=author.mention, inline=True)
                await log_chan.send(embed=log_embed)

        # Update stats
        if approved:
            stats = await self.config.guild(guild).stats()
            stats.setdefault(str(author.id), {})
            stats[str(author.id)]["approved"] = stats[str(author.id)].get("approved", 0) + 1
            await self.config.guild(guild).stats.set(stats)

        # Update suggestion status
        data["status"] = "approved" if approved else "declined"
        await self.config.guild(guild).suggestions.set_raw(sid, value=data)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestcreate(self, ctx: commands.Context):
        """Interactive setup wizard for the suggestion system."""
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        setup_embed = discord.Embed(
            title="📋 Suggestion System Setup",
            description="Let's configure your thread-based suggestion system!\n\n"
                       "I'll ask you a series of questions. You can type `cancel` at any time to stop.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=setup_embed)

        try:
            # 1. Suggestion Channel
            await ctx.send("**Step 1/6:** Please mention the channel where suggestions will be submitted (e.g., #suggestions)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if msg.content.lower() == 'cancel':
                return await ctx.send("Setup cancelled.")
            
            if not msg.channel_mentions:
                return await ctx.send("No channel mentioned. Setup cancelled.")
            
            suggestion_channel = msg.channel_mentions[0]
            await self.config.guild(ctx.guild).suggestion_channel.set(suggestion_channel.id)
            await ctx.send(f"✅ Suggestion channel set to {suggestion_channel.mention}")

            # 2. Staff Channel
            await ctx.send("**Step 2/6:** Please mention the staff channel for notifications (or type `skip` to skip)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if msg.content.lower() == 'cancel':
                return await ctx.send("Setup cancelled.")
            
            if msg.content.lower() != 'skip' and msg.channel_mentions:
                staff_channel = msg.channel_mentions[0]
                await self.config.guild(ctx.guild).staff_channel.set(staff_channel.id)
                await ctx.send(f"✅ Staff channel set to {staff_channel.mention}")
            else:
                await ctx.send("⏭️ Staff channel skipped")

            # 3. Staff Notification Threshold
            await ctx.send("**Step 3/6:** How many upvotes should trigger a staff notification? (e.g., 5)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if msg.content.lower() == 'cancel':
                return await ctx.send("Setup cancelled.")
            
            try:
                staff_threshold = int(msg.content)
                await self.config.guild(ctx.guild).staff_notification_threshold.set(staff_threshold)
                await ctx.send(f"✅ Staff will be notified at {staff_threshold} upvotes")
            except ValueError:
                await ctx.send("⚠️ Invalid number, using default (5)")
                await self.config.guild(ctx.guild).staff_notification_threshold.set(5)

            # 4. Auto-Approval Threshold
            await ctx.send("**Step 4/6:** How many upvotes for auto-approval? (e.g., 10, or type `none` to disable)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if msg.content.lower() == 'cancel':
                return await ctx.send("Setup cancelled.")
            
            if msg.content.lower() != 'none':
                try:
                    upvote_threshold = int(msg.content)
                    await self.config.guild(ctx.guild).upvote_threshold.set(upvote_threshold)
                    await ctx.send(f"✅ Auto-approval at {upvote_threshold} upvotes")
                except ValueError:
                    await ctx.send("⚠️ Invalid number, using default (10)")
                    await self.config.guild(ctx.guild).upvote_threshold.set(10)
            else:
                await self.config.guild(ctx.guild).upvote_threshold.set(999999)
                await ctx.send("✅ Auto-approval disabled")

            # 5. Auto-Decline Threshold
            await ctx.send("**Step 5/6:** How many downvotes for auto-decline? (e.g., 5, or type `none` to disable)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if msg.content.lower() == 'cancel':
                return await ctx.send("Setup cancelled.")
            
            if msg.content.lower() != 'none':
                try:
                    downvote_threshold = int(msg.content)
                    await self.config.guild(ctx.guild).downvote_threshold.set(downvote_threshold)
                    await ctx.send(f"✅ Auto-decline at {downvote_threshold} downvotes")
                except ValueError:
                    await ctx.send("⚠️ Invalid number, using default (5)")
                    await self.config.guild(ctx.guild).downvote_threshold.set(5)
            else:
                await self.config.guild(ctx.guild).downvote_threshold.set(999999)
                await ctx.send("✅ Auto-decline disabled")

            # 6. Log/Archive Channels (Optional)
            await ctx.send("**Step 6/6:** Mention a log channel for resolved suggestions (or type `skip`)")
            msg = await self.bot.wait_for('message', timeout=60.0, check=check)
            if msg.content.lower() != 'skip' and msg.channel_mentions:
                log_channel = msg.channel_mentions[0]
                await self.config.guild(ctx.guild).log_channel.set(log_channel.id)
                await self.config.guild(ctx.guild).archive_channel.set(log_channel.id)
                await ctx.send(f"✅ Log/Archive channel set to {log_channel.mention}")
            else:
                await ctx.send("⏭️ Log channel skipped")

            # Final summary
            final_embed = discord.Embed(
                title="✅ Setup Complete!",
                description="Your thread-based suggestion system is ready!",
                color=discord.Color.green()
            )
            final_embed.add_field(
                name="How to use",
                value=f"Users can now type `.suggest <their suggestion>` in {suggestion_channel.mention} to create a suggestion thread!",
                inline=False
            )
            final_embed.add_field(
                name="Additional Commands",
                value="• `.suggestconfig` - View all configuration commands\n"
                      "• `.suggestconfig approve <id>` - Manually approve\n"
                      "• `.suggestconfig decline <id>` - Manually decline\n"
                      "• `.suggesttop` - View top contributors",
                inline=False
            )
            await ctx.send(embed=final_embed)

        except TimeoutError:
            await ctx.send("Setup timed out. Please try again with `.suggestcreate`")

    @commands.group(name="suggestconfig", aliases=["suggestset"])
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig(self, ctx: commands.Context):
        """Configure the suggestion system."""
        if ctx.invoked_subcommand is None:
            conf = await self.config.guild(ctx.guild).all()
            
            embed = discord.Embed(
                title="⚙️ Suggestion System Configuration",
                color=discord.Color.blue()
            )
            
            sugg_ch = ctx.guild.get_channel(conf["suggestion_channel"])
            staff_ch = ctx.guild.get_channel(conf["staff_channel"])
            log_ch = ctx.guild.get_channel(conf["log_channel"])
            
            embed.add_field(name="Suggestion Channel", value=sugg_ch.mention if sugg_ch else "Not set", inline=True)
            embed.add_field(name="Staff Channel", value=staff_ch.mention if staff_ch else "Not set", inline=True)
            embed.add_field(name="Log Channel", value=log_ch.mention if log_ch else "Not set", inline=True)
            embed.add_field(name="Staff Notification", value=f"{conf.get('staff_notification_threshold', 5)} upvotes", inline=True)
            embed.add_field(name="Auto-Approve", value=f"{conf['upvote_threshold']} upvotes", inline=True)
            embed.add_field(name="Auto-Decline", value=f"{conf['downvote_threshold']} downvotes", inline=True)
            embed.add_field(name="Daily Limit", value=f"{conf['cooldown_per_day']} per user", inline=True)
            embed.add_field(name="Reward", value=f"{conf['reward_credits']} credits", inline=True)
            
            await ctx.send(embed=embed)

    @suggestconfig.command(name="setchannel")
    async def _setchan(self, ctx, channel: discord.TextChannel):
        """Set the suggestion channel"""
        await self.config.guild(ctx.guild).suggestion_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Suggestion channel set to {channel.mention}"))

    @suggestconfig.command(name="setstaffchannel")
    async def _setstaffchan(self, ctx, channel: discord.TextChannel):
        """Set the staff notification channel"""
        await self.config.guild(ctx.guild).staff_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Staff channel set to {channel.mention}"))

    @suggestconfig.command(name="setlogchannel")
    async def _setlogchan(self, ctx, channel: discord.TextChannel):
        """Set the log channel"""
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Log channel set to {channel.mention}"))

    @suggestconfig.command(name="setarchivechannel")
    async def _setarchivechan(self, ctx, channel: discord.TextChannel):
        """Set the archive channel"""
        await self.config.guild(ctx.guild).archive_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Archive channel set to {channel.mention}"))

    @suggestconfig.command(name="staffthreshold")
    async def _staffthreshold(self, ctx, amount: int):
        """Set upvotes needed for staff notification"""
        await self.config.guild(ctx.guild).staff_notification_threshold.set(max(1, amount))
        await ctx.send(embed=success_embed(f"Staff will be notified at {amount} upvotes"))

    @suggestconfig.command(name="reward")
    async def _setreward(self, ctx, amount: int):
        """Set credit reward for submitting suggestions"""
        await self.config.guild(ctx.guild).reward_credits.set(max(0, amount))
        await ctx.send(embed=success_embed(f"Suggestions will reward `{amount}` credits/Beri."))

    @suggestconfig.command(name="usebericore")
    async def _togglebericore(self, ctx, toggle: bool):
        """Toggle BeriCore integration"""
        await self.config.guild(ctx.guild).use_beri_core.set(toggle)
        await ctx.send(embed=success_embed(f"BeriCore integration {'enabled' if toggle else 'disabled'}."))

    @suggestconfig.command(name="setthresholds")
    async def _thresholds(self, ctx, upvotes: int = 10, downvotes: int = 5):
        """Set auto-approve and auto-decline thresholds"""
        await self.config.guild(ctx.guild).upvote_threshold.set(upvotes)
        await self.config.guild(ctx.guild).downvote_threshold.set(downvotes)
        await ctx.send(embed=success_embed(f"Thresholds set: 👍 {upvotes} | 👎 {downvotes}"))

    @suggestconfig.command(name="cooldown")
    async def _cooldown(self, ctx, per_day: int = 1):
        """Set daily suggestion limit per user"""
        await self.config.guild(ctx.guild).cooldown_per_day.set(max(0, per_day))
        await ctx.send(embed=success_embed(f"Users may submit up to {per_day} suggestions per day."))

    @suggestconfig.command(name="blacklist")
    async def _blacklist(self, ctx, action: str, user: discord.Member):
        """Add or remove a user from the blacklist"""
        ids = await self.config.guild(ctx.guild).blacklisted_users()
        if action == "add":
            ids.append(user.id)
            await self.config.guild(ctx.guild).blacklisted_users.set(list(set(ids)))
            await ctx.send(embed=success_embed(f"{user} is now blacklisted."))
        elif action == "remove":
            ids = [i for i in ids if i != user.id]
            await self.config.guild(ctx.guild).blacklisted_users.set(ids)
            await ctx.send(embed=success_embed(f"{user} is no longer blacklisted."))
        else:
            await ctx.send("Usage: `[p]suggestconfig blacklist add/remove @user`")

    @suggestconfig.command(name="approve")
    async def _approve(self, ctx, sid: int):
        """Manually approve a suggestion"""
        conf = await self.config.guild(ctx.guild).all()
        data = conf["suggestions"].get(str(sid))
        if not data:
            return await ctx.send(embed=error_embed("Invalid suggestion ID."))
        if data["status"] != "pending":
            return await ctx.send(embed=error_embed("This suggestion has already been resolved."))

        chan = ctx.guild.get_channel(data["channel_id"])
        try:
            msg = await chan.fetch_message(data["message_id"])
            await self._resolve(msg, ctx.guild, data, approved=True)
            await ctx.send(embed=success_embed(f"✅ Suggestion #{sid} has been approved."))
        except discord.NotFound:
            await ctx.send(embed=error_embed("Could not find the suggestion message."))

    @suggestconfig.command(name="decline")
    async def _decline(self, ctx, sid: int):
        """Manually decline a suggestion"""
        conf = await self.config.guild(ctx.guild).all()
        data = conf["suggestions"].get(str(sid))
        if not data:
            return await ctx.send(embed=error_embed("Invalid suggestion ID."))
        if data["status"] != "pending":
            return await ctx.send(embed=error_embed("This suggestion has already been resolved."))

        chan = ctx.guild.get_channel(data["channel_id"])
        try:
            msg = await chan.fetch_message(data["message_id"])
            await self._resolve(msg, ctx.guild, data, approved=False)
            await ctx.send(embed=success_embed(f"❌ Suggestion #{sid} has been declined."))
        except discord.NotFound:
            await ctx.send(embed=error_embed("Could not find the suggestion message."))

    @commands.command()
    @commands.guild_only()
    async def suggesttop(self, ctx):
        """Show top suggesters and approvals."""
        stats = await self.config.guild(ctx.guild).stats()
        if not stats:
            return await ctx.send(embed=error_embed("No statistics available yet."))
        
        sorted_stats = sorted(stats.items(), key=lambda x: x[1].get("approved", 0), reverse=True)
        
        embed = discord.Embed(
            title="🏆 Top Suggestion Contributors",
            color=discord.Color.gold()
        )
        
        lines = []
        for i, (uid, s) in enumerate(sorted_stats[:10], 1):
            user = ctx.guild.get_member(int(uid)) or self.bot.get_user(int(uid))
            name = user.display_name if user else f"User {uid}"
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"`#{i}`"
            approved = s.get("approved", 0)
            submitted = s.get("submitted", 0)
            lines.append(f"{medal} **{name}** — ✅ {approved} approved / 📝 {submitted} submitted")
        
        embed.description = "\n".join(lines) if lines else "No contributors yet."
        await ctx.send(embed=embed)
