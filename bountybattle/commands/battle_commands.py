import asyncio
import discord
import random
import datetime
from redbot.core import commands
from typing import Optional

class BattleCommands:
    """Handles all battle-related commands."""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.config = cog.config
        self.logger = cog.logger
        self.battle_manager = cog.battle_manager
        self.status_manager = cog.status_manager
        self.environment_manager = cog.environment_manager
        self.devil_fruit_manager = cog.devil_fruit_manager
        self.image_utils = cog.image_utils
        
    @commands.command(name="db")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def deathbattle(self, ctx: commands.Context, opponent: discord.Member = None):
        """
        Start a One Piece deathmatch against another user with a bounty.
        """
        try:
            # Quick check if battle is already in progress
            if ctx.channel.id in self.cog.active_channels:
                return await ctx.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")

            # Mark the channel as active immediately
            self.cog.active_channels.add(ctx.channel.id)

            # Send an initial message to provide immediate feedback
            loading_msg = await ctx.send("⚔️ **Preparing for battle...**")

            try:
                # Sync data for the challenger
                user_bounty = await self.cog.data_manager.sync_user_data(ctx.author)
                
                # If no opponent is provided, choose a random bounty holder
                if opponent is None:
                    await loading_msg.edit(content="🔍 **Finding a worthy opponent...**")
                    
                    # Find valid opponents
                    valid_opponents = []
                    all_members = await self.config.all_members(ctx.guild)
                    
                    # Limit potential opponents to 20 to avoid checking too many
                    for member_id, data in list(all_members.items())[:20]:
                        try:
                            if int(member_id) == ctx.author.id or data.get("bounty", 0) <= 0:
                                continue
                                
                            member = ctx.guild.get_member(int(member_id))
                            if member and not member.bot:
                                valid_opponents.append(member)
                        except Exception:
                            continue

                    if not valid_opponents:
                        self.cog.active_channels.remove(ctx.channel.id)
                        await loading_msg.edit(content="❌ **There are no valid users with a bounty to challenge!**")
                        return

                    opponent = random.choice(valid_opponents)
                    opponent_bounty = await self.cog.data_manager.sync_user_data(opponent)
                else:
                    # Verify opponent exists and is valid
                    if opponent.bot:
                        self.cog.active_channels.remove(ctx.channel.id)
                        await loading_msg.edit(content="❌ You cannot challenge a bot to a deathmatch!")
                        return
                        
                    if opponent == ctx.author:
                        self.cog.active_channels.remove(ctx.channel.id)
                        await loading_msg.edit(content="❌ You cannot challenge yourself to a deathmatch!")
                        return
                        
                    # Sync opponent's bounty
                    opponent_bounty = await self.cog.data_manager.sync_user_data(opponent)
                
                # Ensure both users have a valid bounty
                if user_bounty <= 0:
                    self.cog.active_channels.remove(ctx.channel.id)
                    await loading_msg.edit(content=f"❌ **{ctx.author.display_name}** needs to start their bounty journey first by typing `.startbounty`!")
                    return

                if opponent_bounty <= 0:
                    self.cog.active_channels.remove(ctx.channel.id)
                    await loading_msg.edit(content=f"❌ **{opponent.display_name}** does not have a bounty to challenge!")
                    return
                
                # Delete the loading message before proceeding
                await loading_msg.delete()
                
                # Generate fight card
                fight_card = await self.bot.loop.run_in_executor(
                    None, self.image_utils.generate_fight_card, ctx.author, opponent
                )
                
                # Send the fight card and start the battle
                await ctx.send(file=discord.File(fp=fight_card, filename="fight_card.png"))
                await self.fight(ctx, ctx.author, opponent)
                
            except Exception as e:
                await ctx.send(f"❌ An error occurred during the battle: {str(e)}")
                self.logger.error(f"Battle error: {str(e)}")
            finally:
                # Always clean up
                if ctx.channel.id in self.cog.active_channels:
                    self.cog.active_channels.remove(ctx.channel.id)

        except Exception as e:
            # Catch any unexpected errors
            await ctx.send(f"❌ An unexpected error occurred: {str(e)}")
            self.logger.error(f"Deathbattle command error: {str(e)}")
            
            # Ensure channel is removed from active channels if an error occurs
            if ctx.channel.id in self.cog.active_channels:
                self.cog.active_channels.remove(ctx.channel.id)
    
    async def fight(self, ctx, challenger, opponent):
        """Enhanced fight system with all manager integrations."""
        try:
            channel_id = ctx.channel.id
                
            # Check if channel is already in battle
            if self.battle_manager.is_channel_in_battle(channel_id):
                return await ctx.send("❌ A battle is already in progress in this channel!")

            # Initialize player data
            challenger_data = await self._initialize_player_data(challenger)
            opponent_data = await self._initialize_player_data(opponent)

            # Create battle state
            battle_state = await self.battle_manager.create_battle(
                channel_id,
                challenger_data,
                opponent_data
            )

            # Initialize environment
            environment = self.cog.environment_manager.choose_environment()
            battle_state["environment"] = environment
            environment_data = self.cog.environment_manager.get_environment_data(environment)

            # Clear any lingering effects from all managers
            self.status_manager.clear_all_effects(challenger_data)
            self.status_manager.clear_all_effects(opponent_data)
            self.environment_manager.clear_environment_effects()

            # Create initial battle embed
            embed = discord.Embed(
                title="⚔️ EPIC ONE PIECE BATTLE ⚔️",
                description=f"Battle begins in **{environment}**!\n*{environment_data['description']}*",
                color=discord.Color.blue()
            )

            # Initialize display
            def update_player_fields():
                embed.clear_fields()
                for player in [challenger_data, opponent_data]:
                    status = self.cog.message_utils.get_status_icons(player)
                    health = self.cog.message_utils.generate_health_bar(player["hp"])
                    fruit_text = f"\n<:MeraMera:1336888578705330318> *{player['fruit']}*" if player['fruit'] else ""
                    
                    embed.add_field(
                        name=f"🏴‍☠️ {player['name']}",
                        value=(
                            f"❤️ HP: {player['hp']}/250\n"
                            f"{health}\n"
                            f"✨ Status: {status}{fruit_text}"
                        ),
                        inline=True
                    )
                    
                    if player == challenger_data:
                        embed.add_field(name="⚔️", value="VS", inline=True)

            # Send initial battle state
            update_player_fields()
            message = await ctx.send(embed=embed)
            battle_log = await ctx.send("📜 **Battle Log:**")

            # Battle loop
            turn = 0
            players = [challenger_data, opponent_data]
            current_player = 0

            while all(p["hp"] > 0 for p in players) and not self.cog.battle_stopped:
                turn += 1
                attacker = players[current_player]
                defender = players[1 - current_player]

                # Process environment effects first
                env_messages, env_effects = await self.environment_manager.apply_environment_effect(
                    environment, players, turn
                )
                
                if env_messages:
                    await battle_log.edit(content=f"{battle_log.content}\n{''.join(env_messages)}")

                # Process status effects
                status_messages, status_damage = await self.status_manager.process_effects(attacker)
                if status_damage > 0:
                    attacker["hp"] = max(0, attacker["hp"] - status_damage)
                    attacker["stats"]["damage_taken"] += status_damage
                
                if status_messages:
                    await battle_log.edit(content=f"{battle_log.content}\n{''.join(status_messages)}")

                # Check if attacker can move (status effects might prevent action)
                if self.status_manager.get_effect_duration(attacker, "stun") > 0 or \
                   self.status_manager.get_effect_duration(attacker, "freeze") > 0:
                    await battle_log.edit(content=f"{battle_log.content}\n⚠️ **{attacker['name']}** is unable to move!")
                    
                else:
                    # Update cooldowns and get available moves
                    self.cog.data_utils.update_cooldowns(attacker)
                    available_moves = [move for move in self.cog.constants.MOVES if move["name"] not in attacker["moves_on_cooldown"]]
                    if not available_moves:
                        available_moves = [move for move in self.cog.constants.MOVES if move["type"] == "regular"]

                    # Select move and apply environment modifications
                    selected_move = random.choice(available_moves)
                    modified_move, env_move_messages = await self.environment_manager.calculate_environment_modifiers(
                        environment, selected_move
                    )

                    # Calculate base damage
                    base_damage, damage_message = self.cog.data_utils.calculate_damage(modified_move, attacker, turn)

                    # Process Devil Fruit effects
                    devil_fruit_bonus, fruit_message = await self.devil_fruit_manager.process_devil_fruit_effect(
                        attacker, defender, modified_move, environment
                    )
                    
                    # Calculate final damage with all effects
                    final_damage, effect_messages = await self.status_manager.calculate_damage_with_effects(
                        base_damage + devil_fruit_bonus, attacker, defender
                    )

                    # Apply final damage
                    if final_damage > 0:
                        defender["hp"] = max(0, defender["hp"] - final_damage)
                        defender["stats"]["damage_taken"] += final_damage
                        attacker["stats"]["damage_dealt"] += final_damage

                    # Apply move effects through status manager
                    if "effect" in modified_move:
                        effect_result = await self.status_manager.apply_effect(
                            modified_move["effect"],
                            defender,
                            value=modified_move.get("effect_value", 1),
                            duration=modified_move.get("effect_duration", 1)
                        )
                        if effect_result:
                            effect_messages.append(effect_result)

                turn_message = [
                    f"\n➤ Turn {turn}: **{attacker['name']}** used **{modified_move['name']}**!"  # Move announcement
                ]

                # Add effects on separate lines
                if damage_message:
                    turn_message.append(f"• {damage_message}")
                if env_move_messages:
                    turn_message.extend(f"• {msg}" for msg in env_move_messages)
                if fruit_message:
                    turn_message.append(f"• {fruit_message}")
                if effect_messages:
                    turn_message.extend(f"• {msg}" for msg in effect_messages)

                # Add final damage as its own line
                turn_message.append(f"💥 Dealt **{final_damage}** damage!")

                # Join with newlines for better readability
                formatted_message = "\n".join(turn_message)

                # Update battle log
                await battle_log.edit(content=f"{battle_log.content}\n{formatted_message}")
                
                # Update display
                update_player_fields()
                await message.edit(embed=embed)

                # Add delay between turns
                await asyncio.sleep(2)

                # Switch turns
                current_player = 1 - current_player

                # Check if anyone is defeated
                if any(p["hp"] <= 0 for p in players):
                    break

            # After battle ends, determine winner
            if not self.cog.battle_stopped:
                winner = next((p for p in players if p["hp"] > 0), players[0])
                loser = players[1] if winner == players[0] else players[0]

                # Create victory embed
                victory_embed = discord.Embed(
                    title="🏆 Battle Complete!",
                    description=f"**{winner['name']}** is victorious!",
                    color=discord.Color.gold()
                )
                await message.edit(embed=victory_embed)

                # Process victory rewards
                await self._process_victory_rewards(ctx, winner, loser)
                
                # Check for achievements
                await self.cog.data_utils.check_achievements(winner["member"])

        except Exception as e:
            self.logger.error(f"Error in fight: {str(e)}")
            await ctx.send(f"An error occurred during the battle: {str(e)}")
        finally:
            # Clean up all managers
            await self.battle_manager.end_battle(channel_id)
            if ctx.channel.id in self.cog.active_channels:
                self.cog.active_channels.remove(ctx.channel.id)
    
    async def _initialize_player_data(self, member):
        """Initialize player data with proper memory management."""
        devil_fruit = await self.config.member(member).devil_fruit()
        return {
            "name": member.display_name,
            "hp": 250,
            "max_hp": 250,
            "member": member,
            "fruit": devil_fruit,
            "moves_on_cooldown": {},
            "status": {
                "burn": 0,
                "stun": False,
                "frozen": 0,
                "transformed": 0,
                "protected": False,
                "block_active": False,
                "accuracy_reduction": 0,
                "accuracy_turns": 0,
                "elements_used": set()
            },
            "stats": {
                "damage": 0,
                "heal": 0,
                "critical_hits": 0,
                "blocks": 0,
                "burns_applied": 0,
                "stuns_applied": 0,
                "damage_dealt": 0,
                "damage_taken": 0,
                "healing_done": 0,
                "turns_survived": 0,
                "cooldowns_managed": 0
            }
        }
    
    async def _process_victory_rewards(self, ctx, winner, loser):
        """Process victory rewards with simplified logic."""
        try:
            # Get member objects
            winner_member = winner["member"]
            loser_member = loser["member"]
            
            # Simple reward calculations
            bounty_increase = random.randint(1000, 3000)
            bounty_decrease = random.randint(500, 1500)
            
            # Update winner's bounty
            async with self.config.member(winner_member).all() as winner_data:
                winner_current_bounty = winner_data.get("bounty", 0)
                if not isinstance(winner_current_bounty, int):
                    winner_current_bounty = 0
                winner_new_bounty = winner_current_bounty + bounty_increase
                winner_data["bounty"] = winner_new_bounty
                winner_data["wins"] = winner_data.get("wins", 0) + 1

            # Update loser's bounty
            async with self.config.member(loser_member).all() as loser_data:
                loser_current_bounty = loser_data.get("bounty", 0)
                if not isinstance(loser_current_bounty, int):
                    loser_current_bounty = 0
                loser_new_bounty = max(0, loser_current_bounty - bounty_decrease)
                loser_data["bounty"] = loser_new_bounty
                loser_data["losses"] = loser_data.get("losses", 0) + 1

            # Create reward embed
            reward_embed = discord.Embed(
                title="<:Beli:1237118142774247425> Battle Rewards",
                color=discord.Color.gold()
            )
            
            reward_embed.add_field(
                name=f"Winner: {winner['name']}",
                value=f"Gained {bounty_increase:,} Berries\nNew Bounty: {winner_new_bounty:,} Berries",
                inline=False
            )
            
            reward_embed.add_field(
                name=f"Loser: {loser['name']}",
                value=f"Lost {bounty_decrease:,} Berries\nNew Bounty: {loser_new_bounty:,} Berries",
                inline=False
            )
            
            await ctx.send(embed=reward_embed)

            # Update last active time
            current_time = datetime.utcnow().isoformat()
            await self.config.member(winner_member).last_active.set(current_time)
            await self.config.member(loser_member).last_active.set(current_time)

        except Exception as e:
            self.logger.error(f"Error processing victory rewards: {str(e)}")
            await ctx.send("An error occurred while processing rewards.")
            
    @commands.command(name="stopbattle")
    @commands.admin_or_permissions(administrator=True)
    async def stopbattle(self, ctx: commands.Context):
        """Stop an ongoing battle (Admin/Owner only)."""
        if ctx.channel.id not in self.cog.active_channels:
            return await ctx.send("❌ There is no ongoing battle in this channel.")
    
        # Mark the battle as stopped
        self.cog.battle_stopped = True
        self.cog.active_channels.remove(ctx.channel.id)
    
        # Choose a random reason for stopping the fight
        reasons = [
            "🚢 **The Marines have arrived!** Everyone retreats immediately! ⚓",
            "👁️ **Imu has erased this battle from history!** The fight never happened...",
            "💥 **A Buster Call has been activated!** The battlefield is destroyed! 🔥",
            "🕊️ **The Five Elders have intervened!** All fighters are forced to flee.",
            "🏴‍☠️ **Shanks stepped in!** He declares: *'This fight ends now.'*",
        ]
        reason = random.choice(reasons)
    
        await ctx.send(f"{reason}\n\n🏴‍☠️ **The battle has been forcibly ended.** No winner was declared!")