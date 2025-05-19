# berribounty/commands/battle_commands.py
"""Battle commands for the One Piece bot."""

import discord
from redbot.core import commands
from typing import Optional
from ..ui.views.battle_view import BattleView  # Fixed path
from ..ui.modals.battle_modal import BattleChallengeModal  # Fixed path
from ..utils.formatters import format_battle_stats, format_percentage, format_time_remaining  # Fixed path
from ..utils.validators import validate_battle_challenge  # Fixed path

class BattleCommands:
    """Battle command handlers."""
    
    def __init__(self, bot, battle_manager, player_manager):
        self.bot = bot
        self.battle_manager = battle_manager
        self.player_manager = player_manager
    
    async def challenge(self, ctx: commands.Context, opponent: discord.Member):
        """Challenge another player to battle."""
        challenger = ctx.author
        
        # Basic validation
        is_valid, error = validate_battle_challenge(challenger, opponent)
        if not is_valid:
            await ctx.send(f"❌ {error}")
            return
        
        # Check if players exist in the system
        challenger_player = await self.player_manager.get_or_create_player(challenger)
        opponent_player = await self.player_manager.get_or_create_player(opponent)
        
        # Check if either player is already in battle
        if await self.battle_manager.is_in_battle(challenger_player):
            await ctx.send("❌ You are already in a battle!")
            return
        
        if await self.battle_manager.is_in_battle(opponent_player):
            await ctx.send(f"❌ {opponent.display_name} is already in a battle!")
            return
        
        # Send challenge modal for customization
        modal = BattleChallengeModal(challenger, opponent, self.battle_manager)
        await ctx.send("⚔️ Customize your battle challenge!", view=discord.ui.View().add_item(
            discord.ui.Button(label="Challenge", custom_id="challenge", emoji="⚔️")
        ))
        
        # Alternative: Direct challenge without customization
        # Create battle challenge
        challenge_embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{challenger.display_name} challenges {opponent.display_name} to battle!",
            color=discord.Color.red()
        )
        
        challenge_embed.add_field(
            name="🏴‍☠️ Challenger",
            value=f"{challenger.display_name}\n"
                  f"Wins: {challenger_player.wins} | Losses: {challenger_player.losses}",
            inline=True
        )
        
        challenge_embed.add_field(
            name="🏴‍☠️ Opponent", 
            value=f"{opponent.display_name}\n"
                  f"Wins: {opponent_player.wins} | Losses: {opponent_player.losses}",
            inline=True
        )
        
        # Create accept/decline buttons
        view = BattleChallengeView(challenger, opponent, self.battle_manager)
        challenge_embed.set_footer(text=f"{opponent.display_name} has 60 seconds to respond")
        
        await ctx.send(embed=challenge_embed, view=view)
    
    async def status(self, ctx: commands.Context):
        """Check your current battle status."""
        player = await self.player_manager.get_or_create_player(ctx.author)
        battle = await self.battle_manager.get_player_battle(player)
        
        if not battle:
            embed = discord.Embed(
                title="⚔️ Battle Status",
                description="You are not currently in a battle.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🎯 Ready to Fight?",
                value="Use `battle challenge @user` to start a battle!",
                inline=False
            )
        else:
            # Show current battle status
            embed = discord.Embed(
                title="⚔️ Current Battle",
                description=f"Battle in progress with {battle.opponent_player.player.member.display_name}",
                color=discord.Color.orange()
            )
            
            # Current player status
            battle_player = battle.get_battle_player(ctx.author)
            embed.add_field(
                name="❤️ Your Status",
                value=f"HP: {battle_player.current_hp}/{battle_player.max_hp}\n"
                      f"MP: {battle_player.mp}/100",
                inline=True
            )
            
            # Opponent status
            opponent_battle_player = battle.opponent_battle_player
            embed.add_field(
                name="💀 Opponent Status",
                value=f"HP: {opponent_battle_player.current_hp}/{opponent_battle_player.max_hp}\n"
                      f"MP: {opponent_battle_player.mp}/100",
                inline=True
            )
            
            # Battle info
            embed.add_field(
                name="🎲 Battle Info",
                value=f"Turn: {battle.turn + 1}\n"
                      f"Current Player: {battle.current_battle_player.player.member.display_name}",
                inline=True
            )
            
            # Add battle control buttons if it's the player's turn
            if battle.current_battle_player.player.member == ctx.author:
                view = BattleView(battle, self.battle_manager)
                await ctx.send(embed=embed, view=view)
                return
        
        await ctx.send(embed=embed)
    
    async def stats(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """View battle statistics."""
        if member is None:
            member = ctx.author
        
        player = await self.player_manager.get_or_create_player(member)
        
        # Calculate stats
        total_battles = player.wins + player.losses
        win_rate = (player.wins / total_battles * 100) if total_battles > 0 else 0
        
        embed = discord.Embed(
            title=f"📊 {member.display_name}'s Battle Stats",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        # Basic battle record
        embed.add_field(
            name="🏆 Battle Record",
            value=f"**Wins:** {player.wins}\n"
                  f"**Losses:** {player.losses}\n"
                  f"**Total:** {total_battles}\n"
                  f"**Win Rate:** {format_percentage(win_rate)}",
            inline=True
        )
        
        # Combat stats
        embed.add_field(
            name="⚔️ Combat Stats",
            value=f"**Damage Dealt:** {player.total_damage_dealt:,}\n"
                  f"**Damage Taken:** {player.total_damage_taken:,}\n"
                  f"**Critical Hits:** {player.stats.get('critical_hits', 0)}\n"
                  f"**Perfect Wins:** {player.stats.get('perfect_wins', 0)}",
            inline=True
        )
        
        # Additional stats
        berries_earned = player.stats.get('berries_earned', 0)
        berries_lost = player.stats.get('berries_lost', 0)
        
        embed.add_field(
            name="💰 Economic Impact",
            value=f"**Berries Earned:** {berries_earned:,}\n"
                  f"**Berries Lost:** {berries_lost:,}\n"
                  f"**Net Gain:** {berries_earned - berries_lost:,}",
            inline=True
        )
        
        # Performance metrics
        if total_battles > 0:
            avg_damage_per_battle = player.total_damage_dealt / total_battles
            avg_damage_taken_per_battle = player.total_damage_taken / total_battles
            
            embed.add_field(
                name="📈 Performance",
                value=f"**Avg Damage/Battle:** {avg_damage_per_battle:.1f}\n"
                      f"**Avg Damage Taken/Battle:** {avg_damage_taken_per_battle:.1f}\n"
                      f"**Damage Ratio:** {player.total_damage_dealt/max(player.total_damage_taken, 1):.2f}:1",
                inline=True
            )
        
        # Devil fruit info
        if player.devil_fruit:
            embed.add_field(
                name="🍎 Devil Fruit",
                value=f"**{player.devil_fruit}**\n*Enhances battle abilities*",
                inline=True
            )
        
        # Battle ranking (if implemented)
        # This would require a ranking system
        embed.add_field(
            name="🏅 Achievements",
            value=f"**Unlocked:** {len(player.achievements)}\n"
                  f"**Current Title:** {player.current_title or 'Rookie Pirate'}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    async def leaderboard(self, ctx: commands.Context, category: str = "wins"):
        """Show battle leaderboards."""
        valid_categories = {
            "wins": ("wins", "🏆 Most Wins"),
            "winrate": ("win_rate", "📈 Best Win Rate"), 
            "damage": ("total_damage_dealt", "⚔️ Most Damage Dealt"),
            "battles": ("total_battles", "🎯 Most Battles")
        }
        
        if category not in valid_categories:
            await ctx.send(f"❌ Invalid category! Valid options: {', '.join(valid_categories.keys())}")
            return
        
        # Get all players in the server
        guild_data = await self.battle_manager.config.guild(ctx.guild).all()
        players_data = guild_data.get("players", {})
        
        if not players_data:
            await ctx.send("❌ No players found!")
            return
        
        # Process and sort players based on category
        stat_key, title = valid_categories[category]
        leaderboard_data = []
        
        for user_id, player_data in players_data.items():
            user = ctx.guild.get_member(int(user_id))
            if not user:
                continue
            
            if category == "winrate":
                # Calculate win rate
                wins = player_data.get("wins", 0)
                losses = player_data.get("losses", 0)
                total = wins + losses
                value = (wins / total * 100) if total >= 5 else 0  # Minimum 5 battles for win rate
            elif category == "battles":
                # Calculate total battles
                value = player_data.get("wins", 0) + player_data.get("losses", 0)
            else:
                # Direct stat lookup
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
                
                if category == "winrate":
                    formatted_value = f"{value:.1f}%"
                else:
                    formatted_value = f"{value:,}"
                
                leaderboard_text += f"{medal} **{player_name}** - {formatted_value}\n"
            
            embed.description = leaderboard_text
        
        # Add user's position if not in top 10
        user_position = None
        for i, (player_name, _) in enumerate(leaderboard_data):
            if player_name == ctx.author.display_name:
                user_position = i + 1
                break
        
        if user_position and user_position > 10:
            embed.add_field(
                name="👤 Your Position",
                value=f"#{user_position}",
                inline=True
            )
        
        embed.set_footer(text=f"Showing top {min(len(leaderboard_data), 10)} players")
        
        await ctx.send(embed=embed)
    
    async def cancel(self, ctx: commands.Context):
        """Cancel your current battle challenge or battle."""
        player = await self.player_manager.get_or_create_player(ctx.author)
        
        # Check for active challenge
        if await self.battle_manager.has_pending_challenge(player):
            await self.battle_manager.cancel_challenge(player)
            await ctx.send("✅ Battle challenge cancelled.")
            return
        
        # Check for active battle
        battle = await self.battle_manager.get_player_battle(player)
        if battle:
            # Only allow cancellation if it's the player's turn or battle just started
            if battle.turn <= 2 or battle.current_battle_player.player == player:
                battle.cancel_battle("Player cancelled")
                await ctx.send("✅ Battle cancelled.")
            else:
                await ctx.send("❌ Cannot cancel battle - wait for your turn or ask opponent to agree.")
        else:
            await ctx.send("❌ You don't have any active battles or challenges to cancel.")
    
    async def surrender(self, ctx: commands.Context):
        """Surrender your current battle."""
        player = await self.player_manager.get_or_create_player(ctx.author)
        battle = await self.battle_manager.get_player_battle(player)
        
        if not battle:
            await ctx.send("❌ You are not currently in a battle!")
            return
        
        # Confirm surrender
        embed = discord.Embed(
            title="🏳️ Confirm Surrender",
            description="Are you sure you want to surrender this battle?\n\n**This will:**\n• Count as a loss\n• End the battle immediately\n• Award victory to your opponent",
            color=discord.Color.orange()
        )
        
        view = SurrenderConfirmView(battle, player)
        await ctx.send(embed=embed, view=view)

class BattleChallengeView(discord.ui.View):
    """View for battle challenge acceptance."""
    
    def __init__(self, challenger: discord.Member, opponent: discord.Member, battle_manager):
        super().__init__(timeout=60.0)
        self.challenger = challenger
        self.opponent = opponent
        self.battle_manager = battle_manager
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the challenged player can interact."""
        return interaction.user == self.opponent
    
    @discord.ui.button(label="Accept Challenge", emoji="⚔️", style=discord.ButtonStyle.green)
    async def accept_challenge(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Accept the battle challenge."""
        # Create battle
        battle = await self.battle_manager.create_battle(self.challenger, self.opponent)
        
        if battle:
            embed = discord.Embed(
                title="⚔️ Battle Begins!",
                description=f"{self.challenger.display_name} vs {self.opponent.display_name}",
                color=discord.Color.green()
            )
            
            # Create battle view for interactive combat
            view = BattleView(battle, self.battle_manager)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.edit_message(
                content="❌ Failed to create battle!", 
                embed=None, 
                view=None
            )
    
    @discord.ui.button(label="Decline", emoji="❌", style=discord.ButtonStyle.red)
    async def decline_challenge(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Decline the battle challenge."""
        embed = discord.Embed(
            title="❌ Challenge Declined",
            description=f"{self.opponent.display_name} declined the battle challenge.",
            color=discord.Color.red()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        """Handle timeout."""
        embed = discord.Embed(
            title="⏰ Challenge Timed Out",
            description=f"{self.opponent.display_name} did not respond in time.",
            color=discord.Color.grey()
        )
        
        # Edit the original message if possible
        try:
            if hasattr(self, 'message'):
                await self.message.edit(embed=embed, view=None)
        except:
            pass

class SurrenderConfirmView(discord.ui.View):
    """View for confirming battle surrender."""
    
    def __init__(self, battle, player):
        super().__init__(timeout=30.0)
        self.battle = battle
        self.player = player
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only the surrendering player can interact."""
        return interaction.user == self.player.member
    
    @discord.ui.button(label="Confirm Surrender", emoji="🏳️", style=discord.ButtonStyle.red)
    async def confirm_surrender(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm the surrender."""
        # End battle with surrender
        self.battle.surrender_player = self.player
        self.battle.end_battle()
        
        embed = discord.Embed(
            title="🏳️ Battle Surrendered",
            description=f"{self.player.member.display_name} has surrendered the battle!",
            color=discord.Color.red()
        )
        
        # Show battle results
        winner = self.battle.winner
        embed.add_field(
            name="🏆 Winner",
            value=winner.player.member.display_name,
            inline=True
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.grey)
    async def cancel_surrender(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the surrender."""
        embed = discord.Embed(
            title="✅ Surrender Cancelled",
            description="The battle continues!",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
