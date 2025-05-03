import discord
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from redbot.core import commands

class BountyCommands:
    """Handles all bounty-related commands."""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.config = cog.config
        self.logger = cog.logger
        self.data_manager = cog.data_manager
        
    @commands.command()
    async def startbounty(self, ctx):
        """Start your bounty journey."""
        user = ctx.author
        
        # Use data manager to sync bounties
        true_bounty = await self.data_manager.sync_user_data(user)
        
        # If they have any existing data
        if true_bounty is not None and true_bounty > 0:
            return await ctx.send(f"Ye already have a bounty of `{true_bounty:,}` Berries, ye scallywag!")
            
        # For both new players and those with 0 bounty
        try:
            initial_bounty = random.randint(50, 100)
            
            # Update bounty
            new_bounty = await self.data_manager.safe_modify_bounty(user, initial_bounty, "set")
            if new_bounty is None:
                return await ctx.send("❌ Failed to set your bounty. Please try again.")
            
            # Initialize stats only if they don't exist
            if not await self.config.member(user).wins():
                await self.config.member(user).wins.set(0)
            if not await self.config.member(user).losses():
                await self.config.member(user).losses.set(0)
            
            # Always update last active time
            await self.config.member(user).last_active.set(datetime.utcnow().isoformat())
            
            # Create appropriate embed
            devil_fruit = await self.data_manager.get_devil_fruit(user)
            if devil_fruit:
                embed = discord.Embed(
                    title="🏴‍☠️ Bounty Renewed!",
                    description=f"**{user.display_name}**'s bounty has been renewed!",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="🏴‍☠️ Welcome to the Grand Line!",
                    description=f"**{user.display_name}** has started their pirate journey!",
                    color=discord.Color.blue()
                )
            
            embed.add_field(
                name="Initial Bounty",
                value=f"`{initial_bounty:,}` Berries",
                inline=False
            )
            
            # Check for beta tester title
            beta_active = await self.config.guild(ctx.guild).beta_active()
            if beta_active:
                unlocked_titles = await self.config.member(user).titles()
                if "BETA TESTER" not in unlocked_titles:
                    unlocked_titles.append("BETA TESTER")
                    await self.config.member(user).titles.set(unlocked_titles)
                    embed.add_field(
                        name="🎖️ Special Title Unlocked",
                        value="`BETA TESTER`",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in startbounty: {str(e)}")
            await ctx.send("⚠️ An error occurred while starting your bounty journey. Please try again.")
            
    @commands.command()
    async def mybounty(self, ctx):
        """Check your bounty amount."""
        user = ctx.author
        
        # Sync data first
        true_bounty = await self.data_manager.sync_user_data(user)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking your bounty.")
            
        # Get current title based on synced bounty
        current_title = self.cog.data_utils.get_bounty_title(true_bounty)
        
        embed = discord.Embed(
            title="🏴‍☠️ Bounty Status",
            description=f"**{user.display_name}**'s current bounty:",
            color=discord.Color.gold()
        )
        embed.add_field(name="<:Beli:1237118142774247425> Bounty", value=f"`{true_bounty:,}` Berries", inline=False)
        embed.add_field(name="🎭 Title", value=f"`{current_title}`", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def dailybounty(self, ctx):
        """Claim your daily bounty increase."""
        user = ctx.author
        
        # Sync bounty data first
        current_bounty = await self.config.member(user).bounty()
        
        # Check last claim time
        last_claim = await self.config.member(user).last_daily_claim()
        now = datetime.utcnow()

        if last_claim:
            last_claim = datetime.fromisoformat(last_claim)
            time_left = timedelta(days=1) - (now - last_claim)
            
            if time_left.total_seconds() > 0:
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return await ctx.send(f"Ye can't claim yer daily bounty yet! Try again in {hours} hours and {minutes} minutes! ⏳")

        # Prompt for treasure chest
        await ctx.send(f"Ahoy, {user.display_name}! Ye found a treasure chest! Do ye want to open it? (yes/no)")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await self.config.member(user).last_daily_claim.set(None)
            return await ctx.send("Ye let the treasure slip through yer fingers! Try again tomorrow, ye landlubber!")

        if msg.content.lower() == "yes":
            increase = random.randint(1000, 5000)
            
            # Update bounty
            new_bounty = await self.data_manager.safe_modify_bounty(user, increase, "add")
            if new_bounty is None:
                return await ctx.send("❌ Failed to update your bounty. Please try again.")
            
            # Update last claim time
            await self.config.member(user).last_daily_claim.set(now.isoformat())
            
            # Get new title
            new_title = self.cog.data_utils.get_bounty_title(new_bounty)
            
            await ctx.send(f"<:Beli:1237118142774247425> Ye claimed {increase:,} Berries! Yer new bounty is {new_bounty:,} Berries!\n"
                         f"Current Title: {new_title}")

            # Announce if the user reaches a significant rank
            if new_bounty >= 900000000:
                await self.announce_rank(ctx.guild, user, new_title)
        else:
            await self.config.member(user).last_daily_claim.set(None)
            await ctx.send("Ye decided not to open the chest. The Sea Kings must've scared ye off!")
    
    async def announce_rank(self, guild, user, title):
        """Announce when a user reaches a significant rank."""
        channel = discord.utils.get(guild.text_channels, name="general")
        if channel:
            await channel.send(f"🎉 Congratulations to {user.mention} for reaching the rank of **{title}** with a bounty of {user.display_name}'s bounty!")

    @commands.command()
    async def mostwanted(self, ctx):
        """Display the top users with the highest bounties."""
        # Load current bounty data
        bounties = self.data_manager.load_bounties()
        
        if not bounties:
            return await ctx.send("🏴‍☠️ No bounties have been claimed yet! Be the first to start your journey with `.startbounty`.")

        # Filter out inactive or invalid entries and sort by amount
        valid_bounties = []
        for user_id, data in bounties.items():
            try:
                member = ctx.guild.get_member(int(user_id))
                if member and data.get("amount", 0) > 0:
                    valid_bounties.append((user_id, data))
            except (ValueError, AttributeError):
                continue

        if not valid_bounties:
            return await ctx.send("🏴‍☠️ No active bounties found! Start your journey with `.startbounty`.")

        sorted_bounties = sorted(valid_bounties, key=lambda x: x[1]["amount"], reverse=True)
        pages = [sorted_bounties[i:i + 10] for i in range(0, len(sorted_bounties), 10)]
        
        current_page = 0
        
        async def create_leaderboard_embed(page_data, page_num):
            embed = discord.Embed(
                title="🏆 Most Wanted Pirates 🏆",
                description="The most notorious pirates of the sea!",
                color=discord.Color.gold()
            )
            
            total_pages = len(pages)
            embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total Pirates: {len(sorted_bounties)}")
            
            for i, (user_id, data) in enumerate(page_data, start=1 + (page_num * 10)):
                member = ctx.guild.get_member(int(user_id))
                if not member:
                    continue
                
                # Get user's devil fruit if they have one
                devil_fruit = data.get("fruit", "None")
                fruit_display = f" • <:MeraMera:1336888578705330318> {devil_fruit}" if devil_fruit and devil_fruit != "None" else ""
                
                # Create rank emoji based on position
                rank_emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                # Format the bounty amount with commas
                bounty_amount = "{:,}".format(data["amount"])
                
                embed.add_field(
                    name=f"{rank_emoji} {member.display_name}",
                    value=f"<:Beli:1237118142774247425> `{bounty_amount} Berries`{fruit_display}",
                    inline=False
                )
            
            return embed

        # Send initial embed
        embed = await create_leaderboard_embed(pages[current_page], current_page)
        message = await ctx.send(embed=embed)

        # Add reactions for navigation
        if len(pages) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return (
                    user == ctx.author 
                    and str(reaction.emoji) in ["⬅️", "➡️"] 
                    and reaction.message.id == message.id
                )

            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add",
                        timeout=60.0,
                        check=check
                    )

                    if str(reaction.emoji) == "➡️":
                        current_page = (current_page + 1) % len(pages)
                    elif str(reaction.emoji) == "⬅️":
                        current_page = (current_page - 1) % len(pages)

                    embed = await create_leaderboard_embed(pages[current_page], current_page)
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)
                    
                except asyncio.TimeoutError:
                    break

            await message.clear_reactions()
            
    @commands.command()
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def bountyhunt(self, ctx, target: discord.Member):
        """Attempt to steal a percentage of another user's bounty with a lock-picking minigame."""
        try:
            hunter = ctx.author
            
            # Initial validation checks
            if hunter == target:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Ye can't hunt yer own bounty, ye scallywag!")
            
            if target.bot:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Ye can't steal from bots, they're too secure!")

            # Sync data for both hunter and target
            hunter_bounty = await self.data_manager.sync_user_data(hunter)
            target_bounty = await self.data_manager.sync_user_data(target)
            
            if hunter_bounty is None or target_bounty is None:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ An error occurred while checking bounties.")

            # Check minimum bounty requirements
            min_bounty = 1000
            if target_bounty < min_bounty:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"<:Beli:1237118142774247425> **{target.display_name}** is too broke to be worth hunting! (Minimum: {min_bounty:,} Berries)")

            # Generate lock-picking challenge
            patterns = {
                "Easy": ["🔒🔑", "🔑🔒"],
                "Medium": ["🔒🔑🔑", "🔑🔒🔑", "🔑🔑🔒"],
                "Hard": ["🔒🔑🔑🔒", "🔑🔒🔒🔑", "🔑🔑🔒🔒"]
            }
            
            # Difficulty scales with target's bounty
            if target_bounty > 1_000_000:
                difficulty = "Hard"
                time_limit = 8
            elif target_bounty > 100_000:
                difficulty = "Medium"
                time_limit = 10
            else:
                difficulty = "Easy"
                time_limit = 12

            lock_code = random.choice(patterns[difficulty])

            # Create challenge embed
            challenge_embed = discord.Embed(
                title="🏴‍☠️ Bounty Hunt Attempt!",
                description=(
                    f"**{hunter.display_name}** is attempting to break into **{target.display_name}**'s safe! 🔐\n\n"
                    f"**Difficulty:** {difficulty}\n"
                    f"**Time Limit:** {time_limit} seconds\n"
                    f"**Pattern to Match:** `{lock_code}`"
                ),
                color=discord.Color.blue()
            )
            await ctx.send(embed=challenge_embed)

            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == hunter and m.channel == ctx.channel,
                    timeout=time_limit
                )
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⌛ Time's Up!",
                    description=f"**{hunter.display_name}** took too long! {target.display_name} was alerted!",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=timeout_embed)

            if msg.content.strip() != lock_code:
                fail_embed = discord.Embed(
                    title="❌ Lock Pick Failed!",
                    description=f"**{hunter.display_name}** failed to pick the lock! {target.display_name} was alerted!",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=fail_embed)

            # Calculate success chance and critical failure
            success = random.random() < 0.6  # 60% base success rate
            critical_failure = random.random() < 0.05  # 5% critical failure chance

            if success and not critical_failure:
                # Calculate steal amount with minimum guarantee
                base_steal = random.uniform(0.05, 0.20)
                steal_amount = max(int(base_steal * target_bounty), 500)
                
                # Update hunter's bounty (add)
                hunter_new_bounty = await self.data_manager.safe_modify_bounty(hunter, steal_amount, "add")
                if hunter_new_bounty is None:
                    await ctx.send("⚠️ Failed to update hunter's bounty!")
                    return
                
                # Update target's bounty (subtract)
                target_new_bounty = await self.data_manager.safe_modify_bounty(target, steal_amount, "subtract")
                if target_new_bounty is None:
                    await ctx.send("⚠️ Failed to update target's bounty!")
                    return

                # Create success embed
                success_embed = discord.Embed(
                    title="🏴‍☠️ Bounty Hunt Success!",
                    description=f"<:Beli:1237118142774247425> **{hunter.display_name}** successfully infiltrated **{target.display_name}**'s vault!",
                    color=discord.Color.green()
                )
                success_embed.add_field(
                    name="💎 Stolen Amount",
                    value=f"`{steal_amount:,}` Berries",
                    inline=False
                )
                success_embed.add_field(
                    name="🏆 New Hunter Bounty",
                    value=f"`{hunter_new_bounty:,}` Berries",
                    inline=True
                )
                success_embed.add_field(
                    name="💀 New Target Bounty",
                    value=f"`{target_new_bounty:,}` Berries",
                    inline=True
                )
                await ctx.send(embed=success_embed)
                
                # Update hunter stats for achievements
                current_stolen = await self.config.member(hunter).bounty_hunted() or 0
                total_stolen = current_stolen + steal_amount
                await self.config.member(hunter).bounty_hunted.set(total_stolen)
                await self.config.member(hunter).successful_hunts.set(
                    (await self.config.member(hunter).successful_hunts() or 0) + 1
                )

            elif critical_failure:
                # Handle critical failure
                penalty = max(int(hunter_bounty * 0.10), 1000)
                
                # Update hunter's bounty (subtract penalty)
                hunter_new_bounty = await self.data_manager.safe_modify_bounty(hunter, penalty, "subtract")
                if hunter_new_bounty is None:
                    await ctx.send("⚠️ Failed to update hunter's bounty!")
                    return

                # Update failed hunts stat
                await self.config.member(hunter).failed_hunts.set(
                    (await self.config.member(hunter).failed_hunts() or 0) + 1
                )

                failure_embed = discord.Embed(
                    title="💥 Critical Failure!",
                    description=(
                        f"**{hunter.display_name}** got caught in a trap while trying to rob "
                        f"**{target.display_name}**!\n\n"
                        f"*The Marines were alerted and imposed a fine!*"
                    ),
                    color=discord.Color.red()
                )
                failure_embed.add_field(
                    name="💸 Fine Amount",
                    value=f"`{penalty:,}` Berries",
                    inline=False
                )
                failure_embed.add_field(
                    name="🏴‍☠️ Remaining Bounty",
                    value=f"`{hunter_new_bounty:,}` Berries",
                    inline=True
                )
                await ctx.send(embed=failure_embed)

            else:
                # Handle normal failure
                await self.config.member(hunter).failed_hunts.set(
                    (await self.config.member(hunter).failed_hunts() or 0) + 1
                )
                await ctx.send(f"💀 **{hunter.display_name}** failed to steal from **{target.display_name}**!")

            # Update last active time
            current_time = datetime.utcnow().isoformat()
            await self.config.member(hunter).last_active.set(current_time)
            await self.config.member(target).last_active.set(current_time)
            
            # Check for achievements
            if total_stolen >= 100_000:
                unlocked_titles = await self.config.member(hunter).titles()
                if "The Bounty Hunter" not in unlocked_titles:
                    unlocked_titles.append("The Bounty Hunter")
                    await self.config.member(hunter).titles.set(unlocked_titles)
                    await ctx.send(f"🎖️ **{hunter.display_name}** has earned the title `The Bounty Hunter`!")

        except Exception as e:
            self.logger.error(f"Error in bountyhunt command: {str(e)}")
            await ctx.send("❌ An error occurred during the bounty hunt!")