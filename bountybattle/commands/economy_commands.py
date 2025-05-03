import discord
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from redbot.core import commands

class EconomyCommands:
    """Handles all economy-related commands."""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.config = cog.config
        self.logger = cog.logger
        self.data_manager = cog.data_manager
        
    @commands.command()
    async def bankstats(self, ctx):
        """View statistics about World Government bank fees and taxes."""
        global_bank = await self.config.guild(ctx.guild).global_bank()
        
        # Create detailed embed
        embed = discord.Embed(
            title="🏦 World Government Bank Statistics",
            description="Detailed breakdown of Marine fees and taxes",
            color=discord.Color.gold()
        )
        
        # Show fee structure
        embed.add_field(
            name="📊 Fee Structure",
            value=(
                "**Deposit Fees:**\n"
                "• Tax: 10% of deposit\n"
                "• Processing Fee: 1-5% of deposit\n\n"
                "**Withdrawal Fees:**\n"
                "• Base Fee: 2-8% of withdrawal\n"
                "• Interest: 1% per hour (compounds)\n"
                "• Surprise Audit: 5% of remaining balance (10% chance)\n\n"
                "**All fees go to the World Government Treasury**"
            ),
            inline=False
        )
        
        # Show current treasury
        embed.add_field(
            name="🏛️ Current Treasury",
            value=f"`{global_bank:,}` Berries",
            inline=False
        )
        
        # Show example calculation
        deposit_amount = 100000
        tax = int(deposit_amount * 0.10)
        proc_fee = int(deposit_amount * 0.03)  # Example 3%
        total_fees = tax + proc_fee
        
        embed.add_field(
            name="💰 Example Transaction (100,000 Berry Deposit)",
            value=(
                f"Base Amount: `{deposit_amount:,}` Berries\n"
                f"Tax (10%): `{tax:,}` Berries\n"
                f"Processing Fee (3%): `{proc_fee:,}` Berries\n"
                f"Total Fees: `{total_fees:,}` Berries\n"
                f"Net Deposit: `{deposit_amount - total_fees:,}` Berries"
            ),
            inline=False
        )
        
        embed.set_footer(text="The Marines thank you for your continued cooperation! 🫡")
        
        await ctx.send(embed=embed)
    
    @commands.group(name="bountybank", aliases=["bbank"], invoke_without_command=True)
    async def bountybank(self, ctx):
        """Check your bank balance and the global bank amount."""
        user = ctx.author
        
        # Get balances
        bank_balance = await self.config.member(user).bank_balance()
        global_bank = await self.config.guild(ctx.guild).global_bank()
        last_deposit = await self.config.member(user).last_deposit_time()
        
        # Calculate interest that will go to global bank (1% per hour)
        current_time = datetime.utcnow()
        interest_pending = 0
        
        if last_deposit and bank_balance > 0:
            last_deposit_time = datetime.fromisoformat(last_deposit)
            hours_passed = (current_time - last_deposit_time).total_seconds() / 3600
            interest_rate = hours_passed * 0.01  # 1% per hour, no cap
            interest_pending = int(bank_balance * interest_rate)
        
        embed = discord.Embed(
            title="🏦 World Government Bank Status",
            description="The World Government charges fees and interest on all stored Berries!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Your Bank Balance",
            value=f"`{bank_balance:,}` Berries",
            inline=False
        )
        
        if interest_pending > 0:
            embed.add_field(
                name="⚠️ Interest Due",
                value=(
                    f"`{interest_pending:,}` Berries\n"
                    "*Interest will be collected on withdrawal or during random Marine audits!*"
                ),
                inline=False
            )
        
        embed.add_field(
            name="World Government Treasury",
            value=f"`{global_bank:,}` Berries",
            inline=False
        )
        
        embed.set_footer(text="💸 Interest Rate: 1% per hour (Compounds continuously)")
        await ctx.send(embed=embed)

    @bountybank.command(name="deposit")
    async def bank_deposit(self, ctx, amount):
        """Deposit bounty into your bank account (10% tax goes to World Government)."""
        user = ctx.author
        
        # Sync data first
        true_bounty = await self.data_manager.sync_user_data(user)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking your bounty.")
        
        # Handle 'all' case
        if str(amount).lower() == 'all':
            amount = true_bounty
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send("❌ Please provide a valid number or 'all'!")
        
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive!")
            
        if amount > true_bounty:
            return await ctx.send(f"❌ You only have `{true_bounty:,}` Berries to deposit!")
        
        # Calculate tax (10%) plus random "processing fee" (1-5%)
        tax = int(amount * 0.10)
        processing_fee = int(amount * random.uniform(0.01, 0.05))
        total_fees = tax + processing_fee
        deposit_amount = amount - total_fees
        
        # Remove from bounty
        new_bounty = await self.data_manager.safe_modify_bounty(user, amount, "subtract")
        if new_bounty is None:
            return await ctx.send("❌ Failed to update your bounty. Please try again.")
        
        # Add to bank (minus fees)
        current_balance = await self.config.member(user).bank_balance()
        await self.config.member(user).bank_balance.set(current_balance + deposit_amount)
        
        # Update last deposit time for interest calculation
        await self.config.member(user).last_deposit_time.set(datetime.utcnow().isoformat())
        
        # Add fees to global bank
        global_bank = await self.config.guild(ctx.guild).global_bank()
        await self.config.guild(ctx.guild).global_bank.set(global_bank + total_fees)
        
        embed = discord.Embed(
            title="🏦 World Government Bank Deposit",
            description=(
                f"Deposited: `{amount:,}` Berries\n"
                f"Tax (10%): `{tax:,}` Berries\n"
                f"Processing Fee: `{processing_fee:,}` Berries\n"
                f"Net Deposit: `{deposit_amount:,}` Berries\n\n"
                f"⚠️ *Interest of 1% per hour will be collected by the World Government!*"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)

    @bountybank.command(name="withdraw")
    async def bank_withdraw(self, ctx, amount):
        """Withdraw bounty from your bank account (subject to fees and interest collection)."""
        user = ctx.author
        
        # Check bank balance
        bank_balance = await self.config.member(user).bank_balance()
        last_deposit = await self.config.member(user).last_deposit_time()
        
        # Calculate accumulated interest
        current_time = datetime.utcnow()
        interest_due = 0
        
        if last_deposit:
            last_deposit_time = datetime.fromisoformat(last_deposit)
            hours_passed = (current_time - last_deposit_time).total_seconds() / 3600
            interest_rate = hours_passed * 0.01  # 1% per hour
            interest_due = int(bank_balance * interest_rate)
        
        # Handle 'all' case
        if str(amount).lower() == 'all':
            amount = bank_balance
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send("❌ Please provide a valid number or 'all'!")
        
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive!")
        
        if amount > bank_balance:
            return await ctx.send(f"❌ You only have `{bank_balance:,}` Berries in your bank!")
        
        # Calculate withdrawal fee (2-8% random fee)
        withdrawal_fee = int(amount * random.uniform(0.02, 0.08))
        total_deductions = withdrawal_fee + interest_due
        final_amount = amount - total_deductions
        
        # Ensure they can afford the fees
        if total_deductions > bank_balance:
            return await ctx.send(
                f"❌ Cannot withdraw! Outstanding fees (`{total_deductions:,}` Berries) exceed your balance!"
            )
        
        # Update bank balance
        await self.config.member(user).bank_balance.set(bank_balance - amount)
        await self.config.member(user).last_deposit_time.set(current_time.isoformat())
        
        # Add to bounty
        new_bounty = await self.data_manager.safe_modify_bounty(user, final_amount, "add")
        if new_bounty is None:
            return await ctx.send("❌ Failed to update your bounty. Please try again.")
        
        # Add fees and interest to global bank
        global_bank = await self.config.guild(ctx.guild).global_bank()
        await self.config.guild(ctx.guild).global_bank.set(global_bank + total_deductions)
        
        embed = discord.Embed(
            title="🏦 World Government Bank Withdrawal",
            description=(
                f"Withdrawal Amount: `{amount:,}` Berries\n"
                f"Interest Collected: `{interest_due:,}` Berries\n"
                f"Withdrawal Fee: `{withdrawal_fee:,}` Berries\n"
                f"Amount Received: `{final_amount:,}` Berries"
            ),
            color=discord.Color.green()
        )
        
        # Random chance of additional "audit"
        if random.random() < 0.10:  # 10% chance
            audit_fee = int(bank_balance * 0.05)  # 5% of remaining balance
            await self.config.member(user).bank_balance.set(bank_balance - amount - audit_fee)
            await self.config.guild(ctx.guild).global_bank.set(global_bank + total_deductions + audit_fee)
            
            embed.add_field(
                name="🏛️ SURPRISE MARINE AUDIT!",
                value=f"The Marines conducted a random audit and collected `{audit_fee:,}` Berries in fees!",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def globalbank(self, ctx):
        """Check how many berries are stored in the World Government's vault."""
        global_bank = await self.config.guild(ctx.guild).global_bank()
        
        embed = discord.Embed(
            title="🏛️ World Government Treasury",
            description=(
                f"💰 Current Vault Contents:\n"
                f"`{global_bank:,}` Berries\n\n"
                f"*Tax collected from all pirate banking transactions.*"
            ),
            color=discord.Color.blue()
        )
        
        # Add info about bank heist if enough berries
        if global_bank >= 10000:
            embed.add_field(
                name="⚠️ Security Notice",
                value=(
                    "The vault contains enough berries to be targeted by pirates!"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="📜 Notice",
                value=(
                    f"Need `{10000 - global_bank:,}` more berries before the vault "
                    "becomes worth targeting."
                ),
                inline=False
            )
        
        embed.set_footer(text="The World Government collects tax on all bank deposits")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def berryflip(self, ctx, bet: Optional[int] = None):
        """Flip a coin to potentially increase your bounty. Higher bets have lower win chances!"""
        try:
            user = ctx.author
            
            # Sync data first
            true_bounty = await self.data_manager.sync_user_data(user)
            if true_bounty is None:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ An error occurred while checking your bounty.")

            if true_bounty == 0:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("🏴‍☠️ Ye need to start yer bounty journey first! Type `.startbounty`")
                
            # Validate bet amount
            if bet is None:
                bet = min(true_bounty, 10000)  # Default to 10k or max bounty
            elif bet < 100:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Minimum bet is `100` Berries! Don't be stingy!")
            elif bet > true_bounty:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"❌ Ye only have `{true_bounty:,}` Berries to bet!")

            # Create initial embed
            embed = discord.Embed(
                title="🎲 Berry Flip Gamble",
                description=f"**{user.display_name}** is betting `{bet:,}` Berries!",
                color=discord.Color.gold()
            )
            
            # Calculate win probability based on bet size
            if bet <= 1000:
                win_probability = 0.75  # 75% chance
                difficulty = "Easy"
            elif bet <= 10000:
                win_probability = 0.60  # 60% chance
                difficulty = "Medium"
            elif bet <= 50000:
                win_probability = 0.40  # 40% chance
                difficulty = "Hard"
            elif bet <= 100000:
                win_probability = 0.20  # 20% chance
                difficulty = "Very Hard"
            else:
                win_probability = 0.10  # 10% chance
                difficulty = "Extreme"

            embed.add_field(
                name="Difficulty",
                value=f"**{difficulty}**\nWin Chance: `{win_probability*100:.0f}%`",
                inline=False
            )

            message = await ctx.send(embed=embed)
            await asyncio.sleep(2)  # Dramatic pause

            # Determine outcome
            won = random.random() < win_probability
            
            if won:
                # Calculate bonus multiplier based on risk
                multiplier = 1.0
                if bet > 50000:
                    multiplier = 2.0
                elif bet > 10000:
                    multiplier = 1.5
                
                winnings = int(bet * multiplier)
                
                # Update bounty
                new_bounty = await self.data_manager.safe_modify_bounty(user, winnings, "add")
                if new_bounty is None:
                    return await ctx.send("❌ Failed to update your bounty. Please try again.")

                bonus_text = f"💫 BONUS WIN! ({multiplier}x Multiplier)\n" if multiplier > 1 else ""
                
                embed.color = discord.Color.green()
                embed.description = (
                    f"🎉 **{user.display_name}** won `{winnings:,}` Berries!\n"
                    f"{bonus_text}"
                    f"New Bounty: `{new_bounty:,}` Berries"
                )
            else:
                loss = bet
                
                # Update bounty
                new_bounty = await self.data_manager.safe_modify_bounty(user, loss, "subtract")
                if new_bounty is None:
                    return await ctx.send("❌ Failed to update your bounty. Please try again.")
                
                embed.color = discord.Color.red()
                embed.description = (
                    f"💀 **{user.display_name}** lost `{loss:,}` Berries!\n"
                    f"Remaining Bounty: `{new_bounty:,}` Berries"
                )

            # Update last active time
            await self.config.member(user).last_active.set(datetime.utcnow().isoformat())

            # Check for new title
            current_title = await self.config.member(user).current_title()
            new_title = self.cog.data_utils.get_bounty_title(new_bounty)

            if new_title != current_title:
                await self.config.member(user).current_title.set(new_title)
                embed.add_field(
                    name="🎭 New Title Unlocked!",
                    value=f"`{new_title}`",
                    inline=False
                )

            # Announce if reached significant rank
            if new_bounty >= 900_000_000:
                await self.cog.bounty_commands.announce_rank(ctx.guild, user, new_title)

            # Update the embed
            await message.edit(embed=embed)

        except Exception as e:
            ctx.command.reset_cooldown(ctx)
            self.logger.error(f"Error in berryflip command: {str(e)}")
            await ctx.send("❌ An error occurred during the gamble!")