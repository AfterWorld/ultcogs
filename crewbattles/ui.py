"""
crewbattles/ui.py
User interface components for crew management (buttons, views, modals)
"""

from typing import Optional, TYPE_CHECKING
import discord
from discord.ext import commands

from .constants import CrewRole
from .logger import EnhancedCrewLogger
from .utils import EmbedBuilder

if TYPE_CHECKING:
    from .crew import CrewManagement


class EnhancedCrewButton(discord.ui.Button):
    """Enhanced button for joining a crew with better error handling and logging"""
    
    def __init__(self, crew_name: str, crew_emoji: str, cog: 'CrewManagement'):
        super().__init__(
            label=f"Join {crew_name}", 
            style=discord.ButtonStyle.primary, 
            custom_id=f"crew_join_{crew_name}"
        )
        self.crew_name = crew_name
        self.crew_emoji = crew_emoji
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        """Enhanced callback with comprehensive error handling and logging"""
        try:
            member = interaction.user
            guild_id = str(interaction.guild_id)
            
            # Defer the response to prevent timeout
            await interaction.response.defer(ephemeral=True)
            
            # Use guild lock for thread safety
            async with self.cog.get_guild_lock(guild_id):
                crew = self.cog.crews.get(guild_id, {}).get(self.crew_name)
                
                if not crew:
                    await interaction.followup.send(
                        embed=EmbedBuilder.create_error_embed(
                            "Crew Not Found", 
                            "This crew no longer exists."
                        ),
                        ephemeral=True
                    )
                    return
        
                if member.id in crew["members"]:
                    await interaction.followup.send(
                        embed=EmbedBuilder.create_warning_embed(
                            "Already in Crew", 
                            "You are already in this crew."
                        ),
                        ephemeral=True
                    )
                    return
        
                # Check if already in another crew
                for other_name, other_crew in self.cog.crews.get(guild_id, {}).items():
                    if member.id in other_crew["members"]:
                        await interaction.followup.send(
                            embed=EmbedBuilder.create_warning_embed(
                                "Already in a Crew", 
                                f"You are already in the crew `{other_name}`. You cannot switch crews once you join one."
                            ),
                            ephemeral=True
                        )
                        return
        
                # Add to crew
                crew["members"].append(member.id)
                
                # Log the action
                self.cog.enhanced_logger.log_user_action(
                    "joined_crew_via_button", member.id, interaction.guild_id,
                    crew_name=self.crew_name
                )
                
                # Assign crew role
                crew_role = interaction.guild.get_role(crew["crew_role"])
                role_assigned = False
                
                if crew_role:
                    try:
                        await member.add_roles(crew_role)
                        role_assigned = True
                    except discord.Forbidden:
                        pass  # Handle below
                
                # Update nickname using enhanced manager
                nickname_success = False
                nickname_error = ""
                
                if hasattr(self.cog, 'nickname_manager'):
                    nickname_success, nickname_error = await self.cog.nickname_manager.set_crew_nickname(
                        member, self.crew_emoji, crew.get("tag"), CrewRole.MEMBER
                    )
                
                # Save crew data
                await self.cog.save_crews(interaction.guild)
                
                # Create response embed
                embed = EmbedBuilder.create_success_embed(
                    "Successfully Joined Crew",
                    f"Welcome to **{self.crew_name}**! {self.crew_emoji}"
                )
                
                # Add warnings if needed
                warnings = []
                if not role_assigned:
                    warnings.append("⚠️ Couldn't assign crew role due to permission issues")
                if not nickname_success and nickname_error:
                    warnings.append(f"⚠️ Couldn't update nickname: {nickname_error}")
                
                if warnings:
                    embed.add_field(
                        name="Warnings",
                        value="\n".join(warnings),
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            self.cog.enhanced_logger.log_error_with_context(
                e, "crew_join_button_callback", 
                interaction.guild_id, interaction.user.id,
                crew_name=self.crew_name
            )
            
            try:
                await interaction.followup.send(
                    embed=EmbedBuilder.create_error_embed(
                        "Unexpected Error",
                        "An unexpected error occurred. Please try again later or contact an administrator."
                    ),
                    ephemeral=True
                )
            except:
                pass  # Response might already be sent


class CrewManagementView(discord.ui.View):
    """Enhanced view for crew management with multiple buttons"""
    
    def __init__(self, crew_name: str, crew_emoji: str, cog: 'CrewManagement'):
        super().__init__(timeout=None)
        self.crew_name = crew_name
        self.crew_emoji = crew_emoji
        self.cog = cog
        
        # Add join button
        self.add_item(EnhancedCrewButton(crew_name, crew_emoji, cog))
        
        # Add info button
        self.add_item(CrewInfoButton(crew_name, cog))


class CrewInfoButton(discord.ui.Button):
    """Button to view detailed crew information"""
    
    def __init__(self, crew_name: str, cog: 'CrewManagement'):
        super().__init__(
            label="View Info",
            style=discord.ButtonStyle.secondary,
            custom_id=f"crew_info_{crew_name}",
            emoji="ℹ️"
        )
        self.crew_name = crew_name
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        """Show detailed crew information"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            guild_id = str(interaction.guild_id)
            crew_data = self.cog.crews.get(guild_id, {}).get(self.crew_name)
            
            if not crew_data:
                await interaction.followup.send(
                    embed=EmbedBuilder.create_error_embed(
                        "Crew Not Found",
                        "This crew no longer exists."
                    ),
                    ephemeral=True
                )
                return
            
            # Create detailed info embed
            if hasattr(self.cog, 'create_enhanced_crew_embed'):
                embed = await self.cog.create_enhanced_crew_embed(
                    interaction.guild, self.crew_name, crew_data
                )
            else:
                # Fallback basic embed
                embed = EmbedBuilder.create_crew_embed(
                    f"{crew_data.get('emoji', '🏴‍☠️')} {self.crew_name}",
                    f"Members: {len(crew_data.get('members', []))}",
                    crew_name=self.crew_name
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.cog.enhanced_logger.log_error_with_context(
                e, "crew_info_button_callback",
                interaction.guild_id, interaction.user.id,
                crew_name=self.crew_name
            )
            
            await interaction.followup.send(
                embed=EmbedBuilder.create_error_embed(
                    "Error",
                    "Failed to load crew information."
                ),
                ephemeral=True
            )


class CrewInviteView(discord.ui.View):
    """View for crew invitation responses"""
    
    def __init__(self, invite_data: dict, cog: 'CrewManagement'):
        super().__init__(timeout=300)  # 5 minute timeout
        self.invite_data = invite_data
        self.cog = cog
    
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle invitation acceptance"""
        try:
            await interaction.response.defer()
            
            # Verify this is the invited user
            if interaction.user.id != self.invite_data["invitee_id"]:
                await interaction.followup.send(
                    embed=EmbedBuilder.create_error_embed(
                        "Not Your Invitation",
                        "This invitation is not for you."
                    ),
                    ephemeral=True
                )
                return
            
            # Process the invitation acceptance
            success = await self._process_invitation_acceptance(interaction)
            
            if success:
                # Update the embed to show acceptance
                embed = EmbedBuilder.create_success_embed(
                    "Invitation Accepted",
                    f"{interaction.user.mention} has joined the crew **{self.invite_data['crew_name']}**!"
                )
                
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                await interaction.edit_original_response(embed=embed, view=self)
            
        except Exception as e:
            self.cog.enhanced_logger.log_error_with_context(
                e, "accept_invite_callback",
                interaction.guild_id, interaction.user.id
            )
    
    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle invitation decline"""
        try:
            await interaction.response.defer()
            
            # Verify this is the invited user
            if interaction.user.id != self.invite_data["invitee_id"]:
                await interaction.followup.send(
                    embed=EmbedBuilder.create_error_embed(
                        "Not Your Invitation",
                        "This invitation is not for you."
                    ),
                    ephemeral=True
                )
                return
            
            # Update the embed to show decline
            embed = EmbedBuilder.create_error_embed(
                "Invitation Declined",
                f"{interaction.user.mention} has declined the invitation to join **{self.invite_data['crew_name']}**."
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.edit_original_response(embed=embed, view=self)
            
            self.cog.enhanced_logger.log_user_action(
                "declined_crew_invitation", interaction.user.id, interaction.guild_id,
                crew_name=self.invite_data['crew_name']
            )
            
        except Exception as e:
            self.cog.enhanced_logger.log_error_with_context(
                e, "decline_invite_callback",
                interaction.guild_id, interaction.user.id
            )
    
    async def _process_invitation_acceptance(self, interaction: discord.Interaction) -> bool:
        """Process invitation acceptance logic"""
        try:
            guild_id = self.invite_data["guild_id"]
            crew_name = self.invite_data["crew_name"]
            member = interaction.user
            
            # Get crew data
            crews = self.cog.crews.get(guild_id, {})
            if crew_name not in crews:
                await interaction.followup.send(
                    embed=EmbedBuilder.create_error_embed(
                        "Crew Not Found",
                        f"The crew `{crew_name}` no longer exists."
                    ),
                    ephemeral=True
                )
                return False
            
            crew = crews[crew_name]
            
            # Check if user is already in a crew
            for other_crew_name, other_crew in crews.items():
                if member.id in other_crew["members"]:
                    await interaction.followup.send(
                        embed=EmbedBuilder.create_warning_embed(
                            "Already in a Crew",
                            f"You are already in the crew `{other_crew_name}`."
                        ),
                        ephemeral=True
                    )
                    return False
            
            # Add to crew
            async with self.cog.get_guild_lock(guild_id):
                crew["members"].append(member.id)
                
                # Assign crew role
                crew_role = interaction.guild.get_role(crew["crew_role"])
                if crew_role:
                    try:
                        await member.add_roles(crew_role)
                    except discord.Forbidden:
                        pass
                
                # Update nickname
                if hasattr(self.cog, 'nickname_manager'):
                    await self.cog.nickname_manager.set_crew_nickname(
                        member, crew["emoji"], crew.get("tag"), CrewRole.MEMBER
                    )
                
                await self.cog.save_crews(interaction.guild)
            
            self.cog.enhanced_logger.log_user_action(
                "accepted_crew_invitation", member.id, interaction.guild_id,
                crew_name=crew_name
            )
            
            return True
            
        except Exception as e:
            self.cog.enhanced_logger.log_error_with_context(
                e, "process_invitation_acceptance",
                interaction.guild_id, interaction.user.id
            )
            return False
    
    async def on_timeout(self):
        """Handle view timeout"""
        try:
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Update embed to show expiration
            embed = EmbedBuilder.create_warning_embed(
                "Invitation Expired",
                "This crew invitation has expired."
            )
            
            # Try to edit the original message
            # Note: This might fail if the message was deleted
            # The actual implementation would need a reference to the original message
            
        except Exception as e:
            # Log error but don't raise it
            if hasattr(self, 'cog') and hasattr(self.cog, 'enhanced_logger'):
                self.cog.enhanced_logger.error(f"Error in invite view timeout: {e}")


# Legacy UI Components for backward compatibility
class CrewButton(discord.ui.Button):
    """Original crew button for backward compatibility"""
    
    def __init__(self, crew_name, crew_emoji, cog):
        super().__init__(
            label=f"Join {crew_name}", 
            style=discord.ButtonStyle.primary, 
            custom_id=f"crew_join_{crew_name}"
        )
        self.crew_name = crew_name
        self.crew_emoji = crew_emoji
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        """Original callback implementation"""
        member = interaction.user
        guild_id = str(interaction.guild_id)
        crew = self.cog.crews.get(guild_id, {}).get(self.crew_name)
        
        if not crew:
            await interaction.response.send_message(
                "❌ This crew no longer exists.", ephemeral=True
            )
            return
    
        if member.id in crew["members"]:
            await interaction.response.send_message(
                "❌ You are already in this crew.", ephemeral=True
            )
            return
    
        # Check if already in another crew
        for other_name, other_crew in self.cog.crews.get(guild_id, {}).items():
            if member.id in other_crew["members"]:
                await interaction.response.send_message(
                    "❌ You cannot switch crews once you join one.", ephemeral=True
                )
                return
    
        # Add to crew
        crew["members"].append(member.id)
        
        # Assign crew role
        crew_role = interaction.guild.get_role(crew["crew_role"])
        if crew_role:
            try:
                await member.add_roles(crew_role)
            except discord.Forbidden:
                await interaction.response.send_message(
                    f"✅ You have joined the crew `{self.crew_name}`! "
                    "Note: I couldn't assign you the crew role due to permission issues.", 
                    ephemeral=True
                )
                await self.cog.save_crews(interaction.guild)
                return
        
        # Update nickname with truncation
        try:
            original_nick = member.display_name
            if not original_nick.startswith(self.crew_emoji):
                truncated_name = self.cog.truncate_nickname(original_nick, self.crew_emoji)
                await member.edit(nick=f"{self.crew_emoji} {truncated_name}")
        except discord.Forbidden:
            await interaction.response.send_message(
                f"✅ You have joined the crew `{self.crew_name}`! "
                "Note: I couldn't update your nickname due to permission issues.", 
                ephemeral=True
            )
            await self.cog.save_crews(interaction.guild)
            return
            
        await self.cog.save_crews(interaction.guild)
        await interaction.response.send_message(
            f"✅ You have joined the crew `{self.crew_name}`!", 
            ephemeral=True
        )


class CrewView(discord.ui.View):
    """Original crew view for backward compatibility"""
    
    def __init__(self, crew_name, crew_emoji, cog):
        super().__init__(timeout=None)
        self.add_item(CrewButton(crew_name, crew_emoji, cog))