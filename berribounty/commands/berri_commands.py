"""Berri (currency) commands for the One Piece bot."""

import discord
import random
import time
from redbot.core import commands
from typing import Optional
from ..formatters import format_berries, format_time_remaining
from ..validators import validate_berries_amount, validate_gamble_amount, validate_cooldown

class BerriCommands:
    """Berri command handlers."""
    
    def __init__(self, bot, player_manager):
        self.bot = bot
        self.player_manager = player_manager
        
        # Cooldown tracking
        self.daily_cooldowns = {}
        self.work_cooldowns = {}
        self.gamble_cooldowns = {}
    
    async def balance(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """Check berri balance."""
        if member is None:
            member = ctx.author
        
        player = await self.player_manager.get_or_create_player(member)
        
        embed = discord.Embed(
            title=f"💰 {member.display_name}'s Wallet",
            color=discord.Color.gold()
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        # Main balance
        embed.add_field(
            name="💳 In Wallet",
            value=format_berries(player.berries),
            inline=True
        )
        
        # Bank balance (if implemented)
        bank_berries = getattr(player, 'bank_berries', 0)
        embed.add_field(
            name="🏦 In Bank", 
            value=format_berries(bank_berries),
            inline=True
        )
        
        # Total wealth
        total_wealth = player.berries + bank_berries
        embed.add_field(
            name="💎 Total Wealth",
            value=format_berries(total_wealth),
            inline=True
        )
        
        # Additional info for self-check
        if member == ctx.author:
            # Show earning stats
            berries_earned = player.stats.get('berries_earned', 0)
            berries_spent = player.stats.get('berries_lost', 0)
            
            embed.add_field(
                name="📊 Statistics",
                value=f"Earned: {format_berries(berries_earned)}\n"
                      f"Spent: {format_berries(berries_spent)}\n"
                      f"Net Gain: {format_berries(berries_earned - berries_spent)}",
                inline=False
            )
            
            # Show available commands
            embed.add_field(
                name="💡 Earn More",
                value="• `berri daily` - Daily claim\n"
                      "• `berri work` - Work for berries\n"
                      "• `berri gamble` - Risk it for riches\n"
                      "• `battle challenge` - Battle for berries",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    async def give(self, ctx: commands.Context, amount: int, recipient: discord.Member):
        """Give berries to another player."""
        giver = ctx.author
        
        # Validate amount
        giver_player = await self.player_manager.get_or_create_player(giver)
        is_valid, error = validate_berries_amount(amount, giver_player.berries)
        if not is_valid:
           await ctx.send(f"❌ {error}")
           return
       
        # Can't give to self
        if giver == recipient:
           await ctx.send("❌ You can't give berries to yourself!")
           return
       
        # Can't give to bots
        if recipient.bot:
           await ctx.send("❌ You can't give berries to bots!")
           return
       
        # Get recipient player
        recipient_player = await self.player_manager.get_or_create_player(recipient)
       
        # Check daily transfer limit (prevent abuse)
        transfer_key = f"{giver.id}_transfers"
        current_time = time.time()
        daily_transfers = self.daily_cooldowns.get(transfer_key, [])
       
        # Clean old transfers (24 hours)
        daily_transfers = [t for t in daily_transfers if current_time - t < 86400]
       
        if len(daily_transfers) >= 5:  # Max 5 transfers per day
           await ctx.send("❌ You've reached your daily transfer limit (5 transfers per day)!")
           return
       
        # Transfer berries
        giver_player.remove_berries(amount)
        recipient_player.add_berries(amount)
       
        # Save players
        await self.player_manager.save_player(giver_player)
        await self.player_manager.save_player(recipient_player)
       
        # Track transfer
        daily_transfers.append(current_time)
        self.daily_cooldowns[transfer_key] = daily_transfers
       
        # Update stats
        giver_player.stats['berries_given'] = giver_player.stats.get('berries_given', 0) + amount
        recipient_player.stats['berries_received'] = recipient_player.stats.get('berries_received', 0) + amount
       
        #  Create confirmation embed
        embed = discord.Embed(
            title="💸 Berries Transferred!",
            description=f"{giver.display_name} gave {format_berries(amount)} to {recipient.display_name}",
            color=discord.Color.green()
        )
       
        embed.add_field(
           name=f"💰 {giver.display_name}'s Balance",
           value=format_berries(giver_player.berries),
           inline=True
        )
       
        embed.add_field(
           name=f"💰 {recipient.display_name}'s Balance", 
           value=format_berries(recipient_player.berries),
           inline=True
        )
       
        transfers_remaining = 5 - len(daily_transfers)
        embed.add_field(
           name="📊 Daily Transfers",
           value=f"{transfers_remaining} remaining",
           inline=True
        )
       
        await ctx.send(embed=embed)
   
    async def daily(self, ctx: commands.Context):
       """Claim your daily berries."""
       player = await self.player_manager.get_or_create_player(ctx.author)
       
       # Check cooldown
       user_id = ctx.author.id
       current_time = time.time()
       last_daily = self.daily_cooldowns.get(user_id, 0)
       
       is_ready, time_remaining = validate_cooldown(last_daily, 86400)  # 24 hours
       
       if not is_ready:
           embed = discord.Embed(
               title="⏰ Daily Claim Not Ready",
               description=f"Come back in {format_time_remaining(time_remaining)}!",
               color=discord.Color.orange()
           )
           await ctx.send(embed=embed)
           return
       
       # Calculate daily amount based on player level/stats
       base_amount = 5000
       
       # Bonus for wins
       win_bonus = min(player.wins * 100, 5000)  # Max 5k bonus
       
       # Random daily bonus
       random_bonus = random.randint(500, 2000)
       
       # Total daily amount
       daily_amount = base_amount + win_bonus + random_bonus
       
       # Add berries
       player.add_berries(daily_amount)
       await self.player_manager.save_player(player)
       
       # Update cooldown
       self.daily_cooldowns[user_id] = current_time
       
       # Update stats
       player.stats['daily_claims'] = player.stats.get('daily_claims', 0) + 1
       player.stats['berries_earned'] = player.stats.get('berries_earned', 0) + daily_amount
       
       # Create reward embed
       embed = discord.Embed(
           title="🌅 Daily Berries Claimed!",
           description=f"You collected {format_berries(daily_amount)} berries!",
           color=discord.Color.gold()
       )
       
       embed.add_field(
           name="💰 Breakdown",
           value=f"Base: {format_berries(base_amount)}\n"
                 f"Win Bonus: {format_berries(win_bonus)}\n"
                 f"Lucky Bonus: {format_berries(random_bonus)}",
           inline=True
       )
       
       embed.add_field(
           name="💳 New Balance",
           value=format_berries(player.berries),
           inline=True
       )
       
       # Streak bonus (if implemented)
       streak = player.stats.get('daily_streak', 0) + 1
       player.stats['daily_streak'] = streak
       
       if streak > 1:
           embed.add_field(
               name="🔥 Daily Streak",
               value=f"{streak} days in a row!",
               inline=True
           )
       
       embed.set_footer(text="Come back tomorrow for more berries!")
       
       await ctx.send(embed=embed)
   
    async def work(self, ctx: commands.Context):
       """Work to earn berries."""
       player = await self.player_manager.get_or_create_player(ctx.author)
       
       # Check cooldown (4 hours)
       user_id = ctx.author.id
       current_time = time.time()
       last_work = self.work_cooldowns.get(user_id, 0)
       
       is_ready, time_remaining = validate_cooldown(last_work, 14400)  # 4 hours
       
       if not is_ready:
           embed = discord.Embed(
               title="😴 Still Tired",
               description=f"You can work again in {format_time_remaining(time_remaining)}!",
               color=discord.Color.orange()
           )
           await ctx.send(embed=embed)
           return
       
       # Different work types with different rewards
       work_types = [
           {
               "name": "Treasure Hunting",
               "description": "You searched for buried treasure",
               "emoji": "🗺️",
               "min_reward": 2000,
               "max_reward": 8000
           },
           {
               "name": "Fishing",
               "description": "You caught some valuable fish",
               "emoji": "🎣",
               "min_reward": 1500,
               "max_reward": 5000
           },
           {
               "name": "Odd Jobs",
               "description": "You helped around the port town",
               "emoji": "🔨",
               "min_reward": 1000,
               "max_reward": 4000
           },
           {
               "name": "Merchant Work",
               "description": "You assisted a traveling merchant",
               "emoji": "🏪",
               "min_reward": 2500,
               "max_reward": 6000
           },
           {
               "name": "Ship Maintenance",
               "description": "You repaired ships at the dock",
               "emoji": "⚓",
               "min_reward": 1800,
               "max_reward": 5500
           }
       ]
       
       # Select random work type
       work = random.choice(work_types)
       
       # Calculate earnings with skill bonus
       base_earnings = random.randint(work["min_reward"], work["max_reward"])
       
       # Skill bonus based on work count
       work_count = player.stats.get('work_count', 0)
       skill_bonus = min(int(base_earnings * (work_count * 0.01)), int(base_earnings * 0.5))  # Max 50% bonus
       
       total_earnings = base_earnings + skill_bonus
       
       # Add berries
       player.add_berries(total_earnings)
       await self.player_manager.save_player(player)
       
       # Update cooldown and stats
       self.work_cooldowns[user_id] = current_time
       player.stats['work_count'] = work_count + 1
       player.stats['berries_earned'] = player.stats.get('berries_earned', 0) + total_earnings
       
       # Create work result embed
       embed = discord.Embed(
           title=f"{work['emoji']} Work Complete!",
           description=f"**{work['name']}**\n{work['description']}",
           color=discord.Color.blue()
       )
       
       embed.add_field(
           name="💰 Earnings",
           value=f"Base: {format_berries(base_earnings)}\n"
                 f"Skill Bonus: {format_berries(skill_bonus)}\n"
                 f"**Total: {format_berries(total_earnings)}**",
           inline=True
       )
       
       embed.add_field(
           name="💳 New Balance",
           value=format_berries(player.berries),
           inline=True
       )
       
       embed.add_field(
           name="📊 Work Experience",
           value=f"Jobs Completed: {player.stats['work_count']}\n"
                 f"Skill Level: {min(100, work_count // 10)}%",
           inline=True
       )
       
       # Random events
       if random.random() < 0.1:  # 10% chance
           bonus_events = [
               ("Found an extra treasure!", random.randint(500, 2000)),
               ("Helpful stranger tipped you!", random.randint(300, 1500)),
               ("Lucky day! Extra payment!", random.randint(800, 2500))
           ]
           
           event_text, bonus_amount = random.choice(bonus_events)
           player.add_berries(bonus_amount)
           await self.player_manager.save_player(player)
           
           embed.add_field(
               name="🍀 Bonus Event!",
               value=f"{event_text}\n+{format_berries(bonus_amount)}",
               inline=False
           )
       
       embed.set_footer(text="You can work again in 4 hours!")
       
       await ctx.send(embed=embed)
   
    async def gamble(self, ctx: commands.Context, amount: int):
       """Gamble your berries."""
       player = await self.player_manager.get_or_create_player(ctx.author)
       
       # Validate amount
       is_valid, error = validate_gamble_amount(amount, player.berries)
       if not is_valid:
           await ctx.send(f"❌ {error}")
           return
       
       # Check cooldown (30 minutes)
       user_id = ctx.author.id
       current_time = time.time()
       last_gamble = self.gamble_cooldowns.get(user_id, 0)
       
       is_ready, time_remaining = validate_cooldown(last_gamble, 1800)  # 30 minutes
       
       if not is_ready:
           embed = discord.Embed(
               title="🎰 Gambling Cooldown",
               description=f"You can gamble again in {format_time_remaining(time_remaining)}!",
               color=discord.Color.orange()
           )
           await ctx.send(embed=embed)
           return
       
       # Remove bet amount
       player.remove_berries(amount)
       
       # Gambling mechanics
       dice_roll = random.randint(1, 100)
       
       # Determine outcome
       if dice_roll <= 35:  # 35% chance to lose all
           winnings = 0
           multiplier = 0
           outcome = "lose"
           result_text = "💀 **You Lost!**"
           color = discord.Color.red()
       elif dice_roll <= 65:  # 30% chance to get money back
           winnings = amount
           multiplier = 1.0
           outcome = "break_even"
           result_text = "😐 **Break Even**"
           color = discord.Color.orange()
       elif dice_roll <= 85:  # 20% chance to win 1.5x
           winnings = int(amount * 1.5)
           multiplier = 1.5
           outcome = "small_win"
           result_text = "😊 **Small Win!**"
           color = discord.Color.green()
       elif dice_roll <= 95:  # 10% chance to win 2x
           winnings = amount * 2
           multiplier = 2.0
           outcome = "big_win"
           result_text = "🤑 **Big Win!**"
           color = discord.Color.dark_green()
       else:  # 5% chance to win 3x
           winnings = amount * 3
           multiplier = 3.0
           outcome = "jackpot"
           result_text = "🎉 **JACKPOT!**"
           color = discord.Color.gold()
       
       # Add winnings
       if winnings > 0:
           player.add_berries(winnings)
       
       await self.player_manager.save_player(player)
       
       # Update cooldown and stats
       self.gamble_cooldowns[user_id] = current_time
       player.stats['gambles_made'] = player.stats.get('gambles_made', 0) + 1
       player.stats['berries_gambled'] = player.stats.get('berries_gambled', 0) + amount
       
       if outcome == "lose":
           player.stats['berries_lost'] = player.stats.get('berries_lost', 0) + amount
       else:
           player.stats['berries_earned'] = player.stats.get('berries_earned', 0) + winnings
       
       # Create result embed
       embed = discord.Embed(
           title="🎰 Gambling Results",
           description=result_text,
           color=color
       )
       
       embed.add_field(
           name="🎲 Your Roll",
           value=f"{dice_roll}/100",
           inline=True
       )
       
       embed.add_field(
           name="💰 Bet Amount",
           value=format_berries(amount),
           inline=True
       )
       
       if outcome != "lose":
           embed.add_field(
               name="🏆 Winnings",
               value=format_berries(winnings),
               inline=True
           )
       
       embed.add_field(
           name="📊 Net Result",
           value=format_berries(winnings - amount),
           inline=True
       )
       
       embed.add_field(
           name="💳 New Balance",
           value=format_berries(player.berries),
           inline=True
       )
       
       # Gambling stats
       total_gambled = player.stats.get('berries_gambled', 0)
       total_won = player.stats.get('berries_earned', 0)
       
       embed.add_field(
           name="🎯 Gambling Stats",
           value=f"Games Played: {player.stats.get('gambles_made', 0)}\n"
                 f"Total Wagered: {format_berries(total_gambled)}\n"
                 f"Net P/L: {format_berries(total_won - total_gambled)}",
           inline=False
       )
       
       # Special messages for big wins/losses
       if outcome == "jackpot":
           embed.add_field(
               name="🎊 Congratulations!",
               value="You hit the jackpot! Lady Luck smiles upon you!",
               inline=False
           )
       elif dice_roll <= 10:  # Really bad luck
           embed.add_field(
               name="😢 Better Luck Next Time",
               value="Even the best pirates have bad days at sea...",
               inline=False
           )
       
       embed.set_footer(text="Gamble responsibly! You can gamble again in 30 minutes.")
       
       await ctx.send(embed=embed)
   
    async def leaderboard(self, ctx: commands.Context, category: str = "berries"):
       """Show berries leaderboard."""
       valid_categories = {
           "berries": ("berries", "💰 Richest Pirates"),
           "total": ("total_wealth", "💎 Total Wealth"),
           "earned": ("berries_earned", "💵 Most Earned"),
           "lost": ("berries_lost", "💸 Most Lost"),
           "gambled": ("berries_gambled", "🎰 Biggest Gamblers")
       }
       
       if category not in valid_categories:
           await ctx.send(f"❌ Invalid category! Valid options: {', '.join(valid_categories.keys())}")
           return
       
       # Get all players in the server
       guild_data = await self.player_manager.config.guild(ctx.guild).all()
       players_data = guild_data.get("players", {})
       
       if not players_data:
           await ctx.send("❌ No players found!")
           return
       
       # Process and sort players
       stat_key, title = valid_categories[category]
       leaderboard_data = []
       
       for user_id, player_data in players_data.items():
           user = ctx.guild.get_member(int(user_id))
           if not user:
               continue
           
           if category == "total":
               # Calculate total wealth (berries + bank)
               value = player_data.get("berries", 0) + player_data.get("bank_berries", 0)
           else:
               # Get stat value
               if category in ["earned", "lost", "gambled"]:
                   value = player_data.get("stats", {}).get(stat_key, 0)
               else:
                   value = player_data.get(stat_key, 0)
           
           leaderboard_data.append((user.display_name, value))
       
       # Sort by value (descending)
       leaderboard_data.sort(key=lambda x: x[1], reverse=True)
       
       # Create leaderboard embed
       embed = discord.Embed(
           title=f"🏴‍☠️ {title} Leaderboard",
           color=discord.Color.gold()
       )
       
       if not leaderboard_data:
           embed.description = "No qualifying players found!"
       else:
           # Top 10 leaderboard
           leaderboard_text = ""
           medals = ["🥇", "🥈", "🥉"]
           
           for i, (player_name, value) in enumerate(leaderboard_data[:10]):
               rank = i + 1
               medal = medals[i] if i < 3 else f"{rank}."
               formatted_value = format_berries(value)
               leaderboard_text += f"{medal} **{player_name}** - {formatted_value}\n"
           
           embed.description = leaderboard_text
       
       # Add user's position if not in top 10
       user_position = None
       user_value = None
       for i, (player_name, value) in enumerate(leaderboard_data):
           if player_name == ctx.author.display_name:
               user_position = i + 1
               user_value = value
               break
       
       if user_position and user_position > 10:
           embed.add_field(
               name="👤 Your Position",
               value=f"#{user_position} - {format_berries(user_value)}",
               inline=True
           )
       
       embed.set_footer(text=f"Showing top {min(len(leaderboard_data), 10)} players")
       
       await ctx.send(embed=embed)
   
    async def bank(self, ctx: commands.Context, action: str = None, amount: int = None):
       """Bank management commands."""
       player = await self.player_manager.get_or_create_player(ctx.author)
       
       if action is None:
           # Show bank status
           embed = discord.Embed(
               title="🏦 Your Bank Account",
               color=discord.Color.blue()
           )
           
           embed.add_field(
               name="💳 Wallet Balance",
               value=format_berries(player.berries),
               inline=True
           )
           
           bank_berries = getattr(player, 'bank_berries', 0)
           embed.add_field(
               name="🏦 Bank Balance",
               value=format_berries(bank_berries),
               inline=True
           )
           
           embed.add_field(
               name="💰 Total Wealth",
               value=format_berries(player.berries + bank_berries),
               inline=True
           )
           
           embed.add_field(
               name="💡 Commands",
               value="`berri bank deposit <amount>` - Deposit berries\n"
                     "`berri bank withdraw <amount>` - Withdraw berries",
               inline=False
           )
           
           await ctx.send(embed=embed)
           return
       
       # Bank actions
       if action.lower() == "deposit":
           if amount is None:
               await ctx.send("❌ Please specify an amount to deposit!")
               return
           
           is_valid, error = validate_berries_amount(amount, player.berries)
           if not is_valid:
               await ctx.send(f"❌ {error}")
               return
           
           # Transfer to bank
           player.remove_berries(amount)
           if not hasattr(player, 'bank_berries'):
               player.bank_berries = 0
           player.bank_berries += amount
           
           await self.player_manager.save_player(player)
           
           embed = discord.Embed(
               title="🏦 Deposit Successful",
               description=f"Deposited {format_berries(amount)} to your bank account",
               color=discord.Color.green()
           )
           
           embed.add_field(name="💳 Wallet", value=format_berries(player.berries), inline=True)
           embed.add_field(name="🏦 Bank", value=format_berries(player.bank_berries), inline=True)
           
           await ctx.send(embed=embed)
       
       elif action.lower() == "withdraw":
           if amount is None:
               await ctx.send("❌ Please specify an amount to withdraw!")
               return
           
           bank_berries = getattr(player, 'bank_berries', 0)
           is_valid, error = validate_berries_amount(amount, bank_berries)
           if not is_valid:
               await ctx.send(f"❌ {error}")
               return
           
           # Transfer from bank
           player.add_berries(amount)
           player.bank_berries -= amount
           
           await self.player_manager.save_player(player)
           
           embed = discord.Embed(
               title="🏦 Withdrawal Successful",
               description=f"Withdrew {format_berries(amount)} from your bank account",
               color=discord.Color.green()
           )
           
           embed.add_field(name="💳 Wallet", value=format_berries(player.berries), inline=True)
           embed.add_field(name="🏦 Bank", value=format_berries(player.bank_berries), inline=True)
           
           await ctx.send(embed=embed)
       
       else:
           await ctx.send("❌ Invalid action! Use `deposit` or `withdraw`.")