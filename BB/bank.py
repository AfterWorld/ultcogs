"""
Bank system for managing Berris currency.
"""
import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import ReactionPredicate
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional

# Handle imports more robustly
try:
    from .utils import setup_logger, format_berris, calculate_robbery_amount, safe_send
    from .constants import *
except ImportError:
    # Fallback for when the cog is loaded through CogManager
    from utils import setup_logger, format_berris, calculate_robbery_amount, safe_send
    from constants import *

class BankSystem:
    """Handles all banking operations for Berris."""
    
    def __init__(self, config: Config):
        self.config = config
        self.log = setup_logger("bank")
        
    async def get_balance(self, user: discord.Member) -> int:
        """Get a user's bank balance."""
        return await self.config.member(user).bank_balance()
    
    async def get_berris(self, user: discord.Member) -> int:
        """Get a user's total berris."""
        return await self.config.member(user).total_berris()
    
    async def add_berris(self, user: discord.Member, amount: int) -> int:
        """Add berris to a user's total."""
        current = await self.get_berris(user)
        new_total = current + amount
        await self.config.member(user).total_berris.set(new_total)
        self.log.info(f"Added {amount} berris to {user.name}. New total: {new_total}")
        return new_total
    
    async def deposit_berris(self, user: discord.Member, amount: int) -> bool:
        """Deposit berris into the bank."""
        total_berris = await self.get_berris(user)
        
        if amount <= 0:
            return False
        
        if amount > total_berris:
            return False
        
        # Remove from total berris and add to bank
        await self.config.member(user).total_berris.set(total_berris - amount)
        
        current_balance = await self.get_balance(user)
        await self.config.member(user).bank_balance.set(current_balance + amount)
        
        self.log.info(f"{user.name} deposited {amount} berris to bank")
        return True
    
    async def withdraw_berris(self, user: discord.Member, amount: int) -> bool:
        """Withdraw berris from the bank."""
        bank_balance = await self.get_balance(user)
        
        if amount <= 0 or amount > bank_balance:
            return False
        
        # Remove from bank and add to total berris
        await self.config.member(user).bank_balance.set(bank_balance - amount)
        
        total_berris = await self.get_berris(user)
        await self.config.member(user).total_berris.set(total_berris + amount)
        
        self.log.info(f"{user.name} withdrew {amount} berris from bank")
        return True
    
    async def get_security_level(self, user: discord.Member) -> str:
        """Get a user's bank security level."""
        return await self.config.member(user).security_level()
    
    async def upgrade_security(self, user: discord.Member, level: str) -> bool:
        """Upgrade a user's bank security."""
        if level not in BANK_SECURITY_LEVELS:
            return False
        
        cost = BANK_SECURITY_LEVELS[level]["cost"]
        total_berris = await self.get_berris(user)
        
        if total_berris < cost:
            return False
        
        # Deduct cost and upgrade security
        await self.config.member(user).total_berris.set(total_berris - cost)
        await self.config.member(user).security_level.set(level)
        
        self.log.info(f"{user.name} upgraded security to {level} for {cost} berris")
        return True
    
    async def attempt_robbery(self, robber: discord.Member, target: discord.Member) -> dict:
        """Attempt to rob another user's bank account."""
        target_balance = await self.get_balance(target)
        
        if target_balance < MIN_ROBBERY_AMOUNT:
            return {"success": False, "reason": "insufficient_funds"}
        
        # Check security level
        security_level = await self.get_security_level(target)
        protection = BANK_SECURITY_LEVELS[security_level]["protection"]
        
        # Calculate success chance
        base_success_rate = ROBBERY_SUCCESS_RATE
        final_success_rate = base_success_rate * (1 - protection)
        
        success = random.random() < final_success_rate
        
        if success:
            stolen_amount = calculate_robbery_amount(target_balance)
            
            # Transfer berris
            await self.config.member(target).bank_balance.set(target_balance - stolen_amount)
            
            robber_berris = await self.get_berris(robber)
            await self.config.member(robber).total_berris.set(robber_berris + stolen_amount)
            
            self.log.info(f"{robber.name} successfully robbed {stolen_amount} berris from {target.name}")
            
            return {
                "success": True,
                "amount": stolen_amount,
                "security_level": security_level
            }
        else:
            self.log.info(f"{robber.name} failed to rob {target.name} (security: {security_level})")
            return {
                "success": False,
                "reason": "security_stopped",
                "security_level": security_level
            }

class BankCommands(commands.Cog):
    """Bank-related commands."""
    
    def __init__(self, bot, config: Config):
        self.bot = bot
        self.config = config
        self.bank = BankSystem(config)
        self.log = setup_logger("bank_commands")
    
    @commands.group(name="bank", invoke_without_command=True)
    async def bank_group(self, ctx):
        """Check your bank status."""
        user = ctx.author
        balance = await self.bank.get_balance(user)
        total_berris = await self.bank.get_berris(user)
        security = await self.bank.get_security_level(user)
        
        embed = discord.Embed(
            title=f"🏦 {user.display_name}'s Bank Account",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="💰 Wallet",
            value=format_berris(total_berris),
            inline=True
        )
        
        embed.add_field(
            name="🏦 Bank Balance",
            value=format_berris(balance),
            inline=True
        )
        
        embed.add_field(
            name="🛡️ Security Level",
            value=security.title(),
            inline=True
        )
        
        protection_percent = int(BANK_SECURITY_LEVELS[security]["protection"] * 100)
        embed.add_field(
            name="📊 Protection",
            value=f"{protection_percent}% theft protection",
            inline=False
        )
        
        await safe_send(ctx, embed=embed)
    
    @bank_group.command(name="deposit")
    @commands.cooldown(1, BANK_DEPOSIT_COOLDOWN, commands.BucketType.user)
    async def deposit(self, ctx, amount: int):
        """Deposit berris into your bank account."""
        user = ctx.author
        
        if amount <= 0:
            await safe_send(ctx, "❌ Please enter a valid amount to deposit.")
            return
        
        total_berris = await self.bank.get_berris(user)
        if amount > total_berris:
            await safe_send(ctx, f"❌ You only have {format_berris(total_berris)} in your wallet.")
            return
        
        success = await self.bank.deposit_berris(user, amount)
        
        if success:
            new_balance = await self.bank.get_balance(user)
            embed = discord.Embed(
                title="💰 Deposit Successful",
                description=f"Deposited {format_berris(amount)} into your bank account.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="New Bank Balance",
                value=format_berris(new_balance),
                inline=False
            )
            await safe_send(ctx, embed=embed)
        else:
            await safe_send(ctx, "❌ Deposit failed. Please try again.")
    
    @bank_group.command(name="withdraw")
    async def withdraw(self, ctx, amount: int):
        """Withdraw berris from your bank account."""
        user = ctx.author
        
        if amount <= 0:
            await safe_send(ctx, "❌ Please enter a valid amount to withdraw.")
            return
        
        balance = await self.bank.get_balance(user)
        if amount > balance:
            await safe_send(ctx, f"❌ You only have {format_berris(balance)} in your bank account.")
            return
        
        success = await self.bank.withdraw_berris(user, amount)
        
        if success:
            new_total = await self.bank.get_berris(user)
            embed = discord.Embed(
                title="💸 Withdrawal Successful",
                description=f"Withdrew {format_berris(amount)} from your bank account.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="New Wallet Balance",
                value=format_berris(new_total),
                inline=False
            )
            await safe_send(ctx, embed=embed)
        else:
            await safe_send(ctx, "❌ Withdrawal failed. Please try again.")
    
    @bank_group.command(name="security")
    async def security(self, ctx, level: str = None):
        """Upgrade your bank security level."""
        user = ctx.author
        
        if level is None:
            # Show available security levels
            embed = discord.Embed(
                title="🛡️ Bank Security Levels",
                description="Upgrade your security to protect against robberies!",
                color=discord.Color.blue()
            )
            
            for sec_level, data in BANK_SECURITY_LEVELS.items():
                protection_percent = int(data["protection"] * 100)
                embed.add_field(
                    name=f"{sec_level.title()}",
                    value=(
                        f"Cost: {format_berris(data['cost'])}\n"
                        f"Protection: {protection_percent}%"
                    ),
                    inline=True
                )
            
            embed.add_field(
                name="Usage",
                value="Use `bank security <level>` to upgrade",
                inline=False
            )
            
            await safe_send(ctx, embed=embed)
            return
        
        level = level.lower()
        if level not in BANK_SECURITY_LEVELS:
            await safe_send(ctx, "❌ Invalid security level. Use `bank security` to see options.")
            return
        
        current_level = await self.bank.get_security_level(user)
        if level == current_level:
            await safe_send(ctx, f"❌ You already have {level} security level.")
            return
        
        cost = BANK_SECURITY_LEVELS[level]["cost"]
        total_berris = await self.bank.get_berris(user)
        
        if total_berris < cost:
            await safe_send(ctx, f"❌ You need {format_berris(cost)} to upgrade to {level} security.")
            return
        
        success = await self.bank.upgrade_security(user, level)
        
        if success:
            protection = int(BANK_SECURITY_LEVELS[level]["protection"] * 100)
            embed = discord.Embed(
                title="🛡️ Security Upgraded",
                description=f"Your bank security has been upgraded to **{level.title()}**!",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="Protection Level",
                value=f"{protection}% theft protection",
                inline=False
            )
            await safe_send(ctx, embed=embed)
        else:
            await safe_send(ctx, "❌ Security upgrade failed. Please try again.")
    
    @commands.command(name="rob")
    @commands.cooldown(1, BANK_ROBBERY_COOLDOWN, commands.BucketType.user)
    async def rob_user(self, ctx, target: discord.Member):
        """Attempt to rob another user's bank account."""
        robber = ctx.author
        
        if target == robber:
            await safe_send(ctx, "❌ You can't rob yourself!")
            return
        
        if target.bot:
            await safe_send(ctx, "❌ You can't rob bots!")
            return
        
        target_balance = await self.bank.get_balance(target)
        if target_balance < MIN_ROBBERY_AMOUNT:
            await safe_send(ctx, f"❌ {target.display_name} doesn't have enough berris in their bank to rob.")
            return
        
        # Attempt the robbery
        result = await self.bank.attempt_robbery(robber, target)
        
        if result["success"]:
            stolen_amount = result["amount"]
            embed = discord.Embed(
                title="💰 Robbery Successful!",
                description=f"{robber.display_name} successfully robbed {target.display_name}!",
                color=discord.Color.dark_red()
            )
            embed.add_field(
                name="Stolen Amount",
                value=format_berris(stolen_amount),
                inline=False
            )
            await safe_send(ctx, embed=embed)
        else:
            if result["reason"] == "security_stopped":
                security_level = result["security_level"]
                embed = discord.Embed(
                    title="🛡️ Robbery Failed!",
                    description=f"{target.display_name}'s {security_level} security stopped the robbery!",
                    color=discord.Color.blue()
                )
                await safe_send(ctx, embed=embed)
            else:
                await safe_send(ctx, "❌ Robbery failed. Try again later.")