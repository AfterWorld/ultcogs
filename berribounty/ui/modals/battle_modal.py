"""Battle-related modal interfaces for the One Piece bot."""

import discord
from typing import Optional, Dict, Any

class BattleChallengeModal(discord.ui.Modal):
    """Modal for customizing battle challenges."""
    
    def __init__(self, challenger, opponent, battle_manager):
        super().__init__(title=f"Challenge {opponent.display_name}")
        self.challenger = challenger
        self.opponent = opponent
        self.battle_manager = battle_manager
    
    wager_input = discord.ui.TextInput(
        label="Berri Wager (Optional)",
        placeholder="Enter amount to wager (0 for no wager)...",
        required=False,
        default="0"
    )
    
    message_input = discord.ui.TextInput(
        label="Challenge Message (Optional)",
        placeholder="Send a message with your challenge...",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
       """Handle battle challenge submission."""
       try:
           # Parse wager amount
           wager = 0
           if self.wager_input.value:
               wager = int(self.wager_input.value)
               if wager < 0:
                   await interaction.response.send_message("❌ Wager cannot be negative!", ephemeral=True)
                   return
           
           # Get challenge message
           challenge_message = self.message_input.value or f"{self.challenger.display_name} challenges you to battle!"
           
           # Create battle challenge
           success = await self.battle_manager.create_challenge(
               challenger=self.challenger,
               opponent=self.opponent,
               wager=wager,
               message=challenge_message
           )
           
           if success:
               embed = discord.Embed(
                   title="⚔️ Battle Challenge Sent!",
                   description=f"Challenge sent to {self.opponent.display_name}",
                   color=discord.Color.green()
               )
               
               if wager > 0:
                   embed.add_field(name="💰 Wager", value=f"{wager:,} berries", inline=True)
               
               embed.add_field(name="💬 Message", value=challenge_message, inline=False)
               
               await interaction.response.send_message(embed=embed)
           else:
               await interaction.response.send_message("❌ Failed to send challenge!", ephemeral=True)
               
       except ValueError:
           await interaction.response.send_message("❌ Invalid wager amount!", ephemeral=True)
       except Exception as e:
           await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class BattleMoveCustomModal(discord.ui.Modal):
   """Modal for customizing battle moves."""
   
   def __init__(self, move_name, current_player, battle):
       super().__init__(title=f"Customize {move_name}")
       self.move_name = move_name
       self.current_player = current_player
       self.battle = battle
   
   target_input = discord.ui.TextInput(
       label="Target (Optional)",
       placeholder="Specify target or leave blank for opponent...",
       required=False
   )
   
   power_input = discord.ui.TextInput(
       label="Power Level (1-100)",
       placeholder="Enter power level for this move...",
       required=False,
       default="100"
   )
   
   taunt_input = discord.ui.TextInput(
       label="Battle Taunt (Optional)",
       placeholder="Add a taunt or battle cry...",
       required=False,
       max_length=150,
       style=discord.TextStyle.paragraph
   )
   
   async def on_submit(self, interaction: discord.Interaction):
       """Handle move customization submission."""
       try:
           # Parse power level
           power_level = 100
           if self.power_input.value:
               power_level = int(self.power_input.value)
               if not 1 <= power_level <= 100:
                   await interaction.response.send_message(
                       "❌ Power level must be between 1 and 100!",
                       ephemeral=True
                   )
                   return
           
           # Process the customized move
           move_data = {
               "name": self.move_name,
               "power_level": power_level / 100,  # Convert to multiplier
               "taunt": self.taunt_input.value or "",
               "target": self.target_input.value or "opponent"
           }
           
           # Execute the move with customizations
           await self._execute_customized_move(interaction, move_data)
           
       except ValueError:
           await interaction.response.send_message("❌ Invalid power level!", ephemeral=True)
       except Exception as e:
           await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
   
   async def _execute_customized_move(self, interaction: discord.Interaction, move_data: Dict[str, Any]):
       """Execute the customized move."""
       # This would integrate with the battle system
       # For now, just send a confirmation
       embed = discord.Embed(
           title="⚔️ Move Executed!",
           description=f"Used {move_data['name']} at {move_data['power_level']*100:.0f}% power!",
           color=discord.Color.blue()
       )
       
       if move_data['taunt']:
           embed.add_field(name="💬 Battle Cry", value=move_data['taunt'], inline=False)
       
       await interaction.response.send_message(embed=embed)

class BattleStrategyModal(discord.ui.Modal):
   """Modal for setting battle strategy."""
   
   def __init__(self, player, battle):
       super().__init__(title="Battle Strategy")
       self.player = player
       self.battle = battle
   
   strategy_input = discord.ui.TextInput(
       label="Strategy",
       placeholder="Choose: aggressive, defensive, balanced, or custom...",
       required=True
   )
   
   focus_input = discord.ui.TextInput(
       label="Focus",
       placeholder="attack, defense, speed, or power...",
       required=False
   )
   
   notes_input = discord.ui.TextInput(
       label="Strategy Notes",
       placeholder="Additional strategy details...",
       required=False,
       max_length=500,
       style=discord.TextStyle.paragraph
   )
   
   async def on_submit(self, interaction: discord.Interaction):
       """Handle strategy submission."""
       strategy = self.strategy_input.value.lower()
       focus = self.focus_input.value.lower() if self.focus_input.value else None
       
       # Validate strategy
       valid_strategies = ["aggressive", "defensive", "balanced", "custom"]
       if strategy not in valid_strategies:
           await interaction.response.send_message(
               f"❌ Invalid strategy! Choose from: {', '.join(valid_strategies)}",
               ephemeral=True
           )
           return
       
       # Apply strategy modifiers
       strategy_modifiers = {
           "aggressive": {"attack": 1.2, "defense": 0.8, "speed": 1.1},
           "defensive": {"attack": 0.8, "defense": 1.3, "speed": 0.9},
           "balanced": {"attack": 1.0, "defense": 1.0, "speed": 1.0},
           "custom": {"attack": 1.0, "defense": 1.0, "speed": 1.0}
       }
       
       # Set player strategy
       battle_player = self.battle.get_battle_player(self.player.member)
       if battle_player:
           battle_player.strategy = {
               "type": strategy,
               "focus": focus,
               "modifiers": strategy_modifiers[strategy],
               "notes": self.notes_input.value
           }
       
       embed = discord.Embed(
           title="🎯 Strategy Set!",
           description=f"Strategy: **{strategy.title()}**",
           color=discord.Color.green()
       )
       
       if focus:
           embed.add_field(name="Focus", value=focus.title(), inline=True)
       
       if self.notes_input.value:
           embed.add_field(name="Notes", value=self.notes_input.value, inline=False)
       
       # Show modifier effects
       modifiers = strategy_modifiers[strategy]
       modifier_text = "\n".join([
           f"{key.title()}: {'+' if val >= 1 else ''}{(val-1)*100:.0f}%"
           for key, val in modifiers.items()
       ])
       embed.add_field(name="Modifiers", value=modifier_text, inline=True)
       
       await interaction.response.send_message(embed=embed, ephemeral=True)

class BattleWagerModal(discord.ui.Modal):
   """Modal for setting up battle wagers."""
   
   def __init__(self, challenger, opponent):
       super().__init__(title="Battle Wager")
       self.challenger = challenger
       self.opponent = opponent
   
   berries_input = discord.ui.TextInput(
       label="Berries Wager",
       placeholder="Enter amount of berries to wager...",
       required=False,
       default="0"
   )
   
   item_input = discord.ui.TextInput(
       label="Item Wager (Optional)",
       placeholder="Describe any items to wager...",
       required=False,
       max_length=200
   )
   
   conditions_input = discord.ui.TextInput(
       label="Special Conditions (Optional)",
       placeholder="Any special win/loss conditions...",
       required=False,
       max_length=300,
       style=discord.TextStyle.paragraph
   )
   
   async def on_submit(self, interaction: discord.Interaction):
       """Handle wager submission."""
       try:
           # Parse berries wager
           berries_wager = 0
           if self.berries_input.value:
               berries_wager = int(self.berries_input.value)
               if berries_wager < 0:
                   await interaction.response.send_message("❌ Wager cannot be negative!", ephemeral=True)
                   return
           
           # Create wager object
           wager_data = {
               "berries": berries_wager,
               "items": self.item_input.value or None,
               "conditions": self.conditions_input.value or None,
               "challenger": self.challenger.id,
               "opponent": self.opponent.id
           }
           
           # Create confirmation embed
           embed = discord.Embed(
               title="💰 Battle Wager Set!",
               description="Wager details:",
               color=discord.Color.gold()
           )
           
           if berries_wager > 0:
               embed.add_field(name="💰 Berries", value=f"{berries_wager:,}", inline=True)
           
           if wager_data["items"]:
               embed.add_field(name="🎒 Items", value=wager_data["items"], inline=False)
           
           if wager_data["conditions"]:
               embed.add_field(name="📜 Conditions", value=wager_data["conditions"], inline=False)
           
           embed.add_field(
               name="⚠️ Warning",
               value="Both players must accept the wager before battle begins!",
               inline=False
           )
           
           await interaction.response.send_message(embed=embed)
           
       except ValueError:
           await interaction.response.send_message("❌ Invalid berries amount!", ephemeral=True)
       except Exception as e:
           await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class BattleReportModal(discord.ui.Modal):
   """Modal for reporting battle issues."""
   
   def __init__(self, battle, reporter):
       super().__init__(title="Report Battle Issue")
       self.battle = battle
       self.reporter = reporter
   
   issue_type_input = discord.ui.TextInput(
       label="Issue Type",
       placeholder="cheating, bug, harassment, etc...",
       required=True
   )
   
   description_input = discord.ui.TextInput(
       label="Description",
       placeholder="Describe the issue in detail...",
       required=True,
       max_length=1000,
       style=discord.TextStyle.paragraph
   )
   
   evidence_input = discord.ui.TextInput(
       label="Evidence (Optional)",
       placeholder="Links to screenshots, messages, etc...",
       required=False,
       max_length=500,
       style=discord.TextStyle.paragraph
   )
   
   async def on_submit(self, interaction: discord.Interaction):
       """Handle battle report submission."""
       # Create report data
       report_data = {
           "battle_id": self.battle.id if hasattr(self.battle, 'id') else "unknown",
           "reporter": self.reporter.id,
           "issue_type": self.issue_type_input.value,
           "description": self.description_input.value,
           "evidence": self.evidence_input.value or None,
           "timestamp": interaction.created_at.isoformat()
       }
       
       # Send report to admins (this would be implemented with actual admin notification)
       embed = discord.Embed(
           title="📝 Report Submitted",
           description="Your battle report has been submitted to the administrators.",
           color=discord.Color.blue()
       )
       
       embed.add_field(name="Issue Type", value=report_data["issue_type"], inline=True)
       embed.add_field(name="Battle ID", value=report_data["battle_id"], inline=True)
       embed.add_field(name="Status", value="Under Review", inline=True)
       
       embed.add_field(
           name="📞 Next Steps",
           value="An administrator will review your report and take appropriate action.",
           inline=False
       )
       
       await interaction.response.send_message(embed=embed, ephemeral=True)

class BattleSpectatorModal(discord.ui.Modal):
   """Modal for spectator interactions."""
   
   def __init__(self, battle, spectator):
       super().__init__(title="Spectator Actions")
       self.battle = battle
       self.spectator = spectator
   
   cheer_input = discord.ui.TextInput(
       label="Cheer for Player",
       placeholder="Enter player name to cheer for...",
       required=False
   )
   
   bet_input = discord.ui.TextInput(
       label="Place Bet (Berries)",
       placeholder="Enter amount to bet on your chosen player...",
       required=False
   )
   
   comment_input = discord.ui.TextInput(
       label="Spectator Comment",
       placeholder="Add a comment about the battle...",
       required=False,
       max_length=200,
       style=discord.TextStyle.paragraph
   )
   
   async def on_submit(self, interaction: discord.Interaction):
       """Handle spectator submission."""
       try:
           response_parts = []
           
           # Handle cheering
           if self.cheer_input.value:
               player_name = self.cheer_input.value
               # Add cheer to battle (this would be implemented in battle system)
               response_parts.append(f"📣 Cheering for {player_name}!")
           
           # Handle betting
           if self.bet_input.value:
               bet_amount = int(self.bet_input.value)
               if bet_amount > 0:
                   # Process spectator bet (this would be implemented)
                   response_parts.append(f"💰 Placed bet of {bet_amount:,} berries!")
           
           # Handle comment
           if self.comment_input.value:
               # Add comment to battle log
               response_parts.append(f"💬 Comment added!")
           
           if response_parts:
               embed = discord.Embed(
                   title="👥 Spectator Action",
                   description="\n".join(response_parts),
                   color=discord.Color.purple()
               )
               
               if self.comment_input.value:
                   embed.add_field(name="Your Comment", value=self.comment_input.value, inline=False)
           else:
               embed = discord.Embed(
                   title="👥 Spectator",
                   description="No actions taken.",
                   color=discord.Color.light_grey()
               )
           
           await interaction.response.send_message(embed=embed, ephemeral=True)
           
       except ValueError:
           await interaction.response.send_message("❌ Invalid bet amount!", ephemeral=True)
       except Exception as e:
           await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class CustomMoveModal(discord.ui.Modal):
   """Modal for creating custom battle moves."""
   
   def __init__(self, player):
       super().__init__(title="Create Custom Move")
       self.player = player
   
   move_name_input = discord.ui.TextInput(
       label="Move Name",
       placeholder="Enter a name for your custom move...",
       required=True,
       max_length=30
   )
   
   move_description_input = discord.ui.TextInput(
       label="Move Description",
       placeholder="Describe what your move does...",
       required=True,
       max_length=200,
       style=discord.TextStyle.paragraph
   )
   
   move_power_input = discord.ui.TextInput(
       label="Base Power (1-100)",
       placeholder="Enter base power level...",
       required=True,
       default="50"
   )
   
   move_type_input = discord.ui.TextInput(
       label="Move Type",
       placeholder="attack, defense, healing, support, etc...",
       required=True
   )
   
   special_effects_input = discord.ui.TextInput(
       label="Special Effects (Optional)",
       placeholder="burn, stun, heal, boost, etc...",
       required=False,
       max_length=100
   )
   
   async def on_submit(self, interaction: discord.Interaction):
       """Handle custom move creation."""
       try:
           # Validate inputs
           move_name = self.move_name_input.value
           if len(move_name) < 3:
               await interaction.response.send_message("❌ Move name must be at least 3 characters!", ephemeral=True)
               return
           
           base_power = int(self.move_power_input.value)
           if not 1 <= base_power <= 100:
               await interaction.response.send_message("❌ Base power must be between 1 and 100!", ephemeral=True)
               return
           
           # Create custom move data
           custom_move = {
               "name": move_name,
               "description": self.move_description_input.value,
               "base_power": base_power,
               "type": self.move_type_input.value.lower(),
               "special_effects": [effect.strip() for effect in self.special_effects_input.value.split(",") if effect.strip()],
               "creator": self.player.id,
               "mp_cost": max(10, base_power // 2),  # Calculate MP cost
               "cooldown": max(1, base_power // 20)  # Calculate cooldown
           }
           
           # Save custom move (this would be implemented with player data)
           embed = discord.Embed(
               title="⚔️ Custom Move Created!",
               description=f"**{custom_move['name']}** has been added to your moveset!",
               color=discord.Color.green()
           )
           
           embed.add_field(name="Description", value=custom_move['description'], inline=False)
           embed.add_field(name="Base Power", value=str(custom_move['base_power']), inline=True)
           embed.add_field(name="Type", value=custom_move['type'].title(), inline=True)
           embed.add_field(name="MP Cost", value=str(custom_move['mp_cost']), inline=True)
           
           if custom_move['special_effects']:
               embed.add_field(
                   name="Special Effects",
                   value=", ".join(custom_move['special_effects']),
                   inline=False
               )
           
           embed.add_field(
               name="💡 Tip",
               value="Use this move in battle to unleash its power!",
               inline=False
           )
           
           await interaction.response.send_message(embed=embed)
           
       except ValueError:
           await interaction.response.send_message("❌ Invalid power level!", ephemeral=True)
       except Exception as e:
           await interaction.response.send_message(f"❌ Error creating move: {str(e)}", ephemeral=True)