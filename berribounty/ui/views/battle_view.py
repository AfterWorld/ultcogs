# berribounty/ui/views/battle_view.py
import discord
import asyncio
import random
from typing import Dict, Any, Optional
from ...models.battle import Battle, BattleState  # Fix import path
from ...constants.moves import MOVES  # Fix import path
from ...managers.battle_manager import BattleManager  # Fix import path

class BattleView(discord.ui.View):
    """Interactive battle interface with buttons and select menus."""
    
    def __init__(self, battle: Battle, battle_manager: BattleManager, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.battle = battle
        self.battle_manager = battle_manager
        self.last_interaction = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this battle."""
        if not self.battle or self.battle.state != BattleState.ACTIVE:
            await interaction.response.send_message("This battle is no longer active!", ephemeral=True)
            return False
            
        current_player = self.battle.current_battle_player.player.member
        if interaction.user != current_player:
            await interaction.response.send_message(
                f"It's {current_player.display_name}'s turn!", 
                ephemeral=True
            )
            return False
            
        return True
    
    async def on_timeout(self):
        """Handle view timeout."""
        if self.battle and self.battle.state == BattleState.ACTIVE:
            self.battle.cancel_battle("Battle timed out")
            
        # Disable all buttons
        for item in self.children:
            item.disabled = True
            
        if self.last_interaction:
            try:
                await self.last_interaction.edit_original_response(view=self)
            except:
                pass
    
    def get_battle_embed(self) -> discord.Embed:
        """Create embed showing current battle state."""
        if not self.battle:
            return discord.Embed(title="Error", description="Battle not found!", color=discord.Color.red())
            
        embed = discord.Embed(
            title="⚔️ Epic Battle ⚔️",
            color=discord.Color.blue()
        )
        
        # Environment info
        if self.battle.environment:
            embed.description = f"🌍 **{self.battle.environment['name']}**\n*{self.battle.environment['description']}*"
        
        # Player 1 info
        p1 = self.battle.player1
        embed.add_field(
            name=f"🏴‍☠️ {p1.player.member.display_name}",
            value=self._get_player_status(p1),
            inline=True
        )
        
        # VS separator
        embed.add_field(name="⚔️", value="**VS**", inline=True)
        
        # Player 2 info
        p2 = self.battle.player2
        embed.add_field(
            name=f"🏴‍☠️ {p2.player.member.display_name}",
            value=self._get_player_status(p2),
            inline=True
        )
        
        # Turn info
        current_player = self.battle.current_battle_player
        embed.add_field(
            name="🎯 Current Turn",
            value=f"**{current_player.player.member.display_name}**\nTurn: {self.battle.turn + 1}",
            inline=False
        )
        
        # Recent battle log
        if self.battle.battle_log:
            recent_logs = self.battle.battle_log[-3:]  # Last 3 entries
            log_text = "\n".join([entry["message"] for entry in recent_logs])
            embed.add_field(
                name="📜 Recent Actions",
                value=log_text or "Battle just started!",
                inline=False
            )
        
        return embed
    
    def _get_player_status(self, battle_player) -> str:
        """Get formatted player status."""
        hp_bar = self._create_health_bar(battle_player.current_hp, battle_player.max_hp)
        mp_bar = self._create_mp_bar(battle_player.mp)
        
        status_effects = []
        for effect in battle_player.status_effects:
            duration = battle_player.status_effects[effect]["duration"]
            status_effects.append(f"{effect.title()} ({duration})")
        
        status_text = ", ".join(status_effects) if status_effects else "None"
        
        fruit_text = ""
        if battle_player.player.devil_fruit:
            fruit_text = f"\n🍎 **{battle_player.player.devil_fruit}**"
        
        return (
            f"❤️ **HP:** {battle_player.current_hp}/{battle_player.max_hp}\n"
            f"{hp_bar}\n"
            f"⚡ **MP:** {battle_player.mp}/100\n"
            f"{mp_bar}\n"
            f"✨ **Status:** {status_text}"
            f"{fruit_text}"
        )
    
    def _create_health_bar(self, current: int, maximum: int, length: int = 10) -> str:
        """Create a health bar using emojis."""
        filled = int((current / maximum) * length)
        return "🟢" * filled + "🔴" * (length - filled)
    
    def _create_mp_bar(self, mp: int, length: int = 10) -> str:
        """Create an MP bar using emojis."""
        filled = int((mp / 100) * length)
        return "🔵" * filled + "⚫" * (length - filled)
    
    @discord.ui.select(
        placeholder="Choose your action...",
        options=[
            discord.SelectOption(
                label="Attack",
                description="Perform a basic attack",
                emoji="⚔️",
                value="attack"
            ),
            discord.SelectOption(
                label="Special Move",
                description="Use a special ability",
                emoji="✨",
                value="special"
            ),
            discord.SelectOption(
                label="Defend",
                description="Reduce incoming damage",
                emoji="🛡️",
                value="defend"
            ),
            discord.SelectOption(
                label="Items",
                description="Use consumable items",
                emoji="🎒",
                value="items"
            )
        ]
    )
    async def action_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle action selection."""
        self.last_interaction = interaction
        action = select.values[0]
        
        if action == "attack":
            await self._show_attack_options(interaction)
        elif action == "special":
            await self._show_special_options(interaction)
        elif action == "defend":
            await self._execute_defend(interaction)
        elif action == "items":
            await self._show_item_options(interaction)
    
    async def _show_attack_options(self, interaction: discord.Interaction):
        """Show attack move options."""
        current_player = self.battle.current_battle_player
        available_moves = []
        
        # Get basic attack moves
        for move in MOVES["basic"]:
            if not current_player.is_move_on_cooldown(move["name"]):
                available_moves.append(move)
        
        if not available_moves:
            await interaction.response.send_message(
                "No attack moves available! All moves are on cooldown.", 
                ephemeral=True
            )
            return
        
        # Create attack selection view
        view = AttackSelectView(self.battle, self.battle_manager, available_moves, self)
        embed = discord.Embed(
            title="⚔️ Select Attack",
            description="Choose your attack move:",
            color=discord.Color.red()
        )
        
        for i, move in enumerate(available_moves[:5]):  # Limit to 5 for select menu
            embed.add_field(
                name=f"{move['name']} {move.get('emoji', '⚔️')}",
                value=f"Damage: {move['damage']}\nMP Cost: {move.get('mp_cost', 0)}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def _show_special_options(self, interaction: discord.Interaction):
        """Show special move options."""
        current_player = self.battle.current_battle_player
        
        # Get devil fruit moves if player has a fruit
        special_moves = []
        if current_player.player.devil_fruit:
            fruit_data = current_player.player.devil_fruit_data
            if fruit_data and "moves" in fruit_data:
                for move in fruit_data["moves"]:
                    if (not current_player.is_move_on_cooldown(move["name"]) and 
                        current_player.mp >= move.get("mp_cost", 0)):
                        special_moves.append(move)
        
        # Add universal special moves
        for move in MOVES["special"]:
            if (not current_player.is_move_on_cooldown(move["name"]) and 
                current_player.mp >= move.get("mp_cost", 0)):
                special_moves.append(move)
        
        if not special_moves:
            await interaction.response.send_message(
                "No special moves available! Check MP cost and cooldowns.", 
                ephemeral=True
            )
            return
        
        # Create special move selection view
        view = SpecialSelectView(self.battle, self.battle_manager, special_moves, self)
        embed = discord.Embed(
            title="✨ Select Special Move",
            description="Choose your special ability:",
            color=discord.Color.purple()
        )
        
        for move in special_moves[:5]:
            embed.add_field(
                name=f"{move['name']} {move.get('emoji', '✨')}",
                value=(
                    f"Effect: {move.get('description', 'Special effect')}\n"
                    f"MP Cost: {move.get('mp_cost', 0)}\n"
                    f"Cooldown: {move.get('cooldown', 0)} turns"
                ),
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def _execute_defend(self, interaction: discord.Interaction):
        """Execute defend action."""
        current_player = self.battle.current_battle_player
        
        # Apply defend status effect
        current_player.apply_status_effect("defend", 1, {"damage_reduction": 0.5})
        current_player.restore_mp(10)  # Restore some MP for defending
        
        self.battle.add_log(f"🛡️ {current_player.player.member.display_name} takes a defensive stance!")
        
        # End turn
        self.battle.next_turn()
        
        # Update the main battle view
        embed = self.get_battle_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Check if battle ended
        if self.battle.state == BattleState.FINISHED:
            await self._handle_battle_end(interaction)
    
    async def _show_item_options(self, interaction: discord.Interaction):
        """Show item usage options."""
        # For now, just basic healing item
        embed = discord.Embed(
            title="🎒 Items",
            description="Choose an item to use:",
            color=discord.Color.green()
        )
        
        view = ItemSelectView(self.battle, self.battle_manager, self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def _handle_battle_end(self, interaction: discord.Interaction):
        """Handle battle ending."""
        if not self.battle.winner:
            return
            
        # Update view to show battle ended
        for item in self.children:
            item.disabled = True
            
        # Calculate rewards
        await self.battle_manager.process_battle_rewards(self.battle)
        
        # Create victory embed
        embed = discord.Embed(
            title="🏆 Battle Complete!",
            description=f"**{self.battle.winner.player.member.display_name}** is victorious!",
            color=discord.Color.gold()
        )
        
        # Add battle stats
        winner_stats = self.battle.winner.battle_stats
        loser_stats = self.battle.loser.battle_stats
        
        embed.add_field(
            name=f"🏆 {self.battle.winner.player.member.display_name}",
            value=(
                f"Damage Dealt: {winner_stats['damage_dealt']}\n"
                f"Damage Taken: {winner_stats['damage_taken']}\n"
                f"Healing Done: {winner_stats['healing_done']}\n"
                f"Critical Hits: {winner_stats['critical_hits']}"
            ),
            inline=True
        )
        
        embed.add_field(
            name=f"💀 {self.battle.loser.player.member.display_name}",
            value=(
                f"Damage Dealt: {loser_stats['damage_dealt']}\n"
                f"Damage Taken: {loser_stats['damage_taken']}\n"
                f"Healing Done: {loser_stats['healing_done']}\n"
                f"Critical Hits: {loser_stats['critical_hits']}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="📊 Battle Info",
            value=(
                f"Duration: {self.battle.duration:.1f}s\n"
                f"Total Turns: {self.battle.turn}\n"
                f"Environment: {self.battle.environment['name'] if self.battle.environment else 'None'}"
            ),
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed, view=self)

class AttackSelectView(discord.ui.View):
   """View for selecting attack moves."""
   
   def __init__(self, battle: Battle, battle_manager: BattleManager, moves: list, parent_view: BattleView):
       super().__init__(timeout=60.0)
       self.battle = battle
       self.battle_manager = battle_manager
       self.moves = moves
       self.parent_view = parent_view
       
       # Create select menu with available moves
       options = []
       for i, move in enumerate(moves[:25]):  # Discord limit is 25 options
           options.append(
               discord.SelectOption(
                   label=move["name"],
                   description=f"Damage: {move['damage']} | MP: {move.get('mp_cost', 0)}",
                   emoji=move.get("emoji", "⚔️"),
                   value=str(i)
               )
           )
       
       self.move_select.options = options
   
   @discord.ui.select(placeholder="Choose your attack...")
   async def move_select(self, interaction: discord.Interaction, select: discord.ui.Select):
       """Handle move selection."""
       move_index = int(select.values[0])
       selected_move = self.moves[move_index]
       
       # Execute the attack
       await self._execute_attack(interaction, selected_move)
   
   async def _execute_attack(self, interaction: discord.Interaction, move: dict):
       """Execute the selected attack move."""
       current_player = self.battle.current_battle_player
       opponent = self.battle.opponent_battle_player
       
       # Check MP cost
       mp_cost = move.get("mp_cost", 0)
       if not current_player.use_mp(mp_cost):
           await interaction.response.send_message(
               f"Not enough MP! Need {mp_cost}, have {current_player.mp}",
               ephemeral=True
           )
           return
       
       # Calculate damage with randomization
       base_damage = move["damage"]
       damage_variance = random.uniform(0.8, 1.2)  # ±20% variance
       actual_damage = int(base_damage * damage_variance)
       
       # Check for critical hit
       crit_chance = move.get("crit_chance", 0.1)
       is_critical = random.random() < crit_chance
       if is_critical:
           actual_damage = int(actual_damage * 1.5)
           current_player.battle_stats["critical_hits"] += 1
       
       # Apply devil fruit bonuses
       if current_player.player.devil_fruit:
           fruit_bonus = await self.battle_manager.calculate_fruit_bonus(
               current_player.player.devil_fruit, move
           )
           actual_damage += fruit_bonus
       
       # Apply damage
       damage_dealt = opponent.take_damage(actual_damage)
       current_player.battle_stats["damage_dealt"] += damage_dealt
       
       # Apply move effects
       if "effects" in move:
           for effect in move["effects"]:
               await self._apply_move_effect(effect, current_player, opponent)
       
       # Set cooldown
       cooldown = move.get("cooldown", 0)
       if cooldown > 0:
           current_player.set_move_cooldown(move["name"], cooldown)
       
       # Create battle log message
       crit_text = " **CRITICAL HIT!**" if is_critical else ""
       self.battle.add_log(
           f"⚔️ {current_player.player.member.display_name} used **{move['name']}**! "
           f"Dealt {damage_dealt} damage!{crit_text}"
       )
       
       # End turn
       self.battle.next_turn()
       
       # Update parent view
       embed = self.parent_view.get_battle_embed()
       await interaction.response.edit_message(
           embed=embed,
           view=self.parent_view if self.battle.state == BattleState.ACTIVE else None
       )
       
       # Check if battle ended
       if self.battle.state == BattleState.FINISHED:
           await self.parent_view._handle_battle_end(interaction)
   
   async def _apply_move_effect(self, effect: dict, attacker, defender):
       """Apply special effects from moves."""
       effect_type = effect["type"]
       
       if effect_type == "burn":
           defender.apply_status_effect("burn", effect["duration"], {"value": effect["damage"]})
           self.battle.add_log(f"🔥 {defender.player.member.display_name} is burning!")
       
       elif effect_type == "heal":
           healing = attacker.heal(effect["amount"])
           self.battle.add_log(f"💚 {attacker.player.member.display_name} healed {healing} HP!")
       
       elif effect_type == "stun":
           defender.apply_status_effect("stun", effect["duration"])
           self.battle.add_log(f"⚡ {defender.player.member.display_name} is stunned!")
       
       elif effect_type == "poison":
           defender.apply_status_effect("poison", effect["duration"], {"value": effect["damage"]})
           self.battle.add_log(f"☠️ {defender.player.member.display_name} is poisoned!")

class SpecialSelectView(discord.ui.View):
   """View for selecting special moves."""
   
   def __init__(self, battle: Battle, battle_manager: BattleManager, moves: list, parent_view: BattleView):
       super().__init__(timeout=60.0)
       self.battle = battle
       self.battle_manager = battle_manager
       self.moves = moves
       self.parent_view = parent_view
   
   @discord.ui.select(placeholder="Choose your special move...")
   async def special_select(self, interaction: discord.Interaction, select: discord.ui.Select):
       """Handle special move selection."""
       move_name = select.values[0]
       selected_move = next(move for move in self.moves if move["name"] == move_name)
       
       # Execute the special move
       await self._execute_special(interaction, selected_move)
   
   async def _execute_special(self, interaction: discord.Interaction, move: dict):
       """Execute the selected special move."""
       current_player = self.battle.current_battle_player
       opponent = self.battle.opponent_battle_player
       
       # Check MP cost
       mp_cost = move.get("mp_cost", 0)
       if not current_player.use_mp(mp_cost):
           await interaction.response.send_message(
               f"Not enough MP! Need {mp_cost}, have {current_player.mp}",
               ephemeral=True
           )
           return
       
       # Execute special move effects
       damage_dealt = 0
       
       if move["type"] == "damage":
           # Calculate special damage
           base_damage = move["damage"]
           actual_damage = int(base_damage * random.uniform(0.9, 1.1))
           damage_dealt = opponent.take_damage(actual_damage)
           current_player.battle_stats["damage_dealt"] += damage_dealt
       
       elif move["type"] == "heal":
           healing = current_player.heal(move["amount"])
           self.battle.add_log(f"💚 {current_player.player.member.display_name} healed {healing} HP!")
       
       elif move["type"] == "support":
           # Apply support effects (buffs, debuffs, etc.)
           for effect in move.get("effects", []):
               if effect["target"] == "self":
                   current_player.apply_status_effect(
                       effect["type"], effect["duration"], effect.get("value")
                   )
               elif effect["target"] == "opponent":
                   opponent.apply_status_effect(
                       effect["type"], effect["duration"], effect.get("value")
                   )
       
       # Set cooldown
       cooldown = move.get("cooldown", 0)
       if cooldown > 0:
           current_player.set_move_cooldown(move["name"], cooldown)
       
       # Create battle log message
       self.battle.add_log(
           f"✨ {current_player.player.member.display_name} used **{move['name']}**!"
           f"{f' Dealt {damage_dealt} damage!' if damage_dealt > 0 else ''}"
       )
       
       # End turn
       self.battle.next_turn()
       
       # Update parent view
       embed = self.parent_view.get_battle_embed()
       await interaction.response.edit_message(
           embed=embed,
           view=self.parent_view if self.battle.state == BattleState.ACTIVE else None
       )
       
       # Check if battle ended
       if self.battle.state == BattleState.FINISHED:
           await self.parent_view._handle_battle_end(interaction)

class ItemSelectView(discord.ui.View):
   """View for selecting items to use."""
   
   def __init__(self, battle: Battle, battle_manager: BattleManager, parent_view: BattleView):
       super().__init__(timeout=60.0)
       self.battle = battle
       self.battle_manager = battle_manager
       self.parent_view = parent_view
   
   @discord.ui.button(label="Healing Potion", emoji="🧪", style=discord.ButtonStyle.green)
   async def healing_potion(self, interaction: discord.Interaction, button: discord.ui.Button):
       """Use a healing potion."""
       current_player = self.battle.current_battle_player
       
       # Check if player has enough berries for the item
       item_cost = 1000  # 1000 berries for healing potion
       if current_player.player.berries < item_cost:
           await interaction.response.send_message(
               f"Not enough berries! Need {item_cost:,}, have {current_player.player.berries:,}",
               ephemeral=True
           )
           return
       
       # Use item
       current_player.player.remove_berries(item_cost)
       healing = current_player.heal(30)
       
       self.battle.add_log(
           f"🧪 {current_player.player.member.display_name} used a Healing Potion! "
           f"Healed {healing} HP!"
       )
       
       # End turn
       self.battle.next_turn()
       
       # Update parent view
       embed = self.parent_view.get_battle_embed()
       await interaction.response.edit_message(
           embed=embed,
           view=self.parent_view if self.battle.state == BattleState.ACTIVE else None
       )
   
   @discord.ui.button(label="Energy Drink", emoji="⚡", style=discord.ButtonStyle.blurple)
   async def energy_drink(self, interaction: discord.Interaction, button: discord.ui.Button):
       """Use an energy drink to restore MP."""
       current_player = self.battle.current_battle_player
       
       # Check if player has enough berries for the item
       item_cost = 800  # 800 berries for energy drink
       if current_player.player.berries < item_cost:
           await interaction.response.send_message(
               f"Not enough berries! Need {item_cost:,}, have {current_player.player.berries:,}",
               ephemeral=True
           )
           return
       
       # Use item
       current_player.player.remove_berries(item_cost)
       current_player.restore_mp(50)
       
       self.battle.add_log(
           f"⚡ {current_player.player.member.display_name} used an Energy Drink! "
           f"Restored 50 MP!"
       )
       
       # End turn
       self.battle.next_turn()
       
       # Update parent view
       embed = self.parent_view.get_battle_embed()
       await interaction.response.edit_message(
           embed=embed,
           view=self.parent_view if self.battle.state == BattleState.ACTIVE else None
       )
   
   @discord.ui.button(label="Back", emoji="↩️", style=discord.ButtonStyle.grey)
   async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
       """Go back to main battle menu."""
       embed = self.parent_view.get_battle_embed()
       await interaction.response.edit_message(embed=embed, view=self.parent_view)
