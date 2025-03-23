from redbot.core import commands, Config
from redbot.core.data_manager import cog_data_path
from asyncio import Lock
import pathlib
import discord
import random
import asyncio
import aiohttp
import json
import os
import datetime
import io 

from .tournament import TournamentSystem

# --- Helper Classes for UI Elements ---
class CrewButton(discord.ui.Button):
    def __init__(self, crew_name, crew_emoji, cog):
        super().__init__(label=f"Join {crew_name}", style=discord.ButtonStyle.primary, custom_id=f"crew_join_{crew_name}")
        self.crew_name = crew_name
        self.crew_emoji = crew_emoji
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild_id = str(interaction.guild_id)
        crew = self.cog.crews.get(guild_id, {}).get(self.crew_name)
        
        if not crew:
            await interaction.response.send_message("❌ This crew no longer exists.", ephemeral=True)
            return
    
        if member.id in crew["members"]:
            await interaction.response.send_message("❌ You are already in this crew.", ephemeral=True)
            return
    
        # Check if already in another crew
        for other_name, other_crew in self.cog.crews.get(guild_id, {}).items():
            if member.id in other_crew["members"]:
                await interaction.response.send_message("❌ You cannot switch crews once you join one.", ephemeral=True)
                return
    
        # Add to crew
        crew["members"].append(member.id)
        
        # Assign crew role
        crew_role = interaction.guild.get_role(crew["crew_role"])
        if crew_role:
            try:
                await member.add_roles(crew_role)
            except discord.Forbidden:
                await interaction.response.send_message(f"✅ You have joined the crew `{self.crew_name}`! Note: I couldn't assign you the crew role due to permission issues.", ephemeral=True)
                await self.cog.save_crews(interaction.guild)
                return
        
        # Update nickname with truncation
        try:
            original_nick = member.display_name
            # Make sure we don't add the emoji twice
            if not original_nick.startswith(self.crew_emoji):
                truncated_name = self.cog.truncate_nickname(original_nick, self.crew_emoji)
                await member.edit(nick=f"{self.crew_emoji} {truncated_name}")
        except discord.Forbidden:
            await interaction.response.send_message(f"✅ You have joined the crew `{self.crew_name}`! Note: I couldn't update your nickname due to permission issues.", ephemeral=True)
            await self.cog.save_crews(interaction.guild)
            return
            
        await self.cog.save_crews(interaction.guild)
        await interaction.response.send_message(f"✅ You have joined the crew `{self.crew_name}`!", ephemeral=True)

class CrewView(discord.ui.View):
    def __init__(self, crew_name, crew_emoji, cog):
        super().__init__(timeout=None)
        self.add_item(CrewButton(crew_name, crew_emoji, cog))


# --- Main Cog ---
class CrewManagement(commands.Cog):
    """A cog for managing crews in your server."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        print("CrewManagement cog initialized!")
        
        # Default configuration
        default_guild = {
            "finished_setup": False,
            "separator_roles": None
        }
        
        self.config.register_guild(**default_guild)
        self.crews = {}
        self.guild_locks = {}  # Dict to store locks for each guild
        
        # Task to load data on bot startup 
        self.bot.loop.create_task(self.initialize())
    
    # Add a method to get a lock for a specific guild
    def get_guild_lock(self, guild_id):
        """Get a lock for a specific guild, creating it if it doesn't exist."""
        if guild_id not in self.guild_locks:
            self.guild_locks[guild_id] = Lock()
        return self.guild_locks[guild_id]

    async def initialize(self):
        """Initialize the cog by loading data from all guilds."""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.load_data(guild)

    async def save_data(self, guild):
        """Save crew data for a specific guild."""
        finished_setup = await self.config.guild(guild).finished_setup()
        if not finished_setup:
            return
    
        # Use Red-Bot's data path structure
        data_path = cog_data_path(self)
        # Create 'Crews' directory if it doesn't exist
        crews_dir = data_path / "Crews"
        if not os.path.exists(crews_dir):
            os.makedirs(crews_dir, exist_ok=True)
        
        # Save to Crews.json in the proper directory
        file_path = crews_dir / f"{guild.id}.json"
        
        try:
            data = {
                "crews": self.crews.get(str(guild.id), {})
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"Saved crew data for guild {guild.name} ({guild.id}) to {file_path}")
        except Exception as e:
            print(f"Error saving crew data for guild {guild.name}: {e}")
    
    async def load_data(self, guild):
        """Load crew data for a specific guild."""
        if not guild:
            return
    
        finished_setup = await self.config.guild(guild).finished_setup()
        if not finished_setup:
            return
    
        # Use Red-Bot's data path structure
        data_path = cog_data_path(self)
        crews_dir = data_path / "Crews"
        file_path = crews_dir / f"{guild.id}.json"
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Ensure guild has its own namespace in memory
                    if str(guild.id) not in self.crews:
                        self.crews[str(guild.id)] = {}
                    
                    # Load the data into memory
                    self.crews[str(guild.id)] = data.get("crews", {})
                    
                    print(f"Loaded crew data for guild {guild.name} ({guild.id}) from {file_path}")
            else:
                print(f"No data file found for guild {guild.name} ({guild.id})")
                # Directory will be created in save_data if needed
        except Exception as e:
            print(f"Error loading crew data for guild {guild.name}: {e}")

    async def save_crews(self, guild):
        """Save only crew data for a specific guild."""
        await self.save_data(guild)

    def truncate_nickname(self, original_name, emoji_prefix):
        """
        Truncate a nickname to ensure it fits within Discord's 32 character limit.
        This version is more conservative and handles custom emojis better.
        """
        # For safety, limit the emoji representation to a smaller size
        # Some custom emojis can have very long string representations
        emoji_len = min(len(emoji_prefix), 8)  # Cap emoji length for calculation purposes
        
        # Maximum length available for the name (accounting for emoji and space)
        max_name_length = 30 - emoji_len  # Using 30 instead of 32 for safety
        
        # If original name is already short enough, return it as is
        if len(original_name) <= max_name_length:
            return original_name
        
        # Otherwise, truncate the name and add "..." to indicate truncation
        return original_name[:max_name_length-3] + "..."
    
    async def set_nickname_safely(self, member, emoji, name_base, is_captain=False):
        """
        Safely set a nickname for a crew member accounting for Discord's 32 character limit.
        Falls back to simpler nicknames if needed.
        
        Returns:
            bool: True if nickname was set successfully, False otherwise
        """
        try:
            # Try with the full emoji and truncated name
            truncated_name = self.truncate_nickname(name_base, emoji)
            nickname = f"{emoji} {truncated_name}"
            
            # Check if the complete nickname would be too long
            if len(nickname) > 31:  # Using 31 as a safety margin
                # If the emoji is a custom emoji (starts with <:), use a standard one
                if emoji.startswith("<:") or emoji.startswith("<a:"):
                    emoji = "🏴‍☠️"
                    nickname = f"{emoji} {truncated_name}"
            
            # If still too long, use an even simpler version
            if len(nickname) > 31:
                role_text = "Captain" if is_captain else "Crew"
                nickname = f"🏴‍☠️ {role_text}"
                
            # One last check before applying
            if len(nickname) > 31:
                # Ultimate fallback - just use a very short nickname
                nickname = f"🏴‍☠️ Crew"
                
            await member.edit(nick=nickname)
            return True
        except discord.Forbidden:
            # No permission to change nickname
            return False
        except discord.HTTPException as e:
            # Something went wrong with the request
            print(f"Error setting nickname: {str(e)}")
            return False
        except Exception as e:
            # Catch any other exceptions
            print(f"Unexpected error setting nickname: {str(e)}")
            return False

    def log_message(self, level, message):
        """
        Log a message with the specified level.
        
        Parameters:
        level (str): The log level - "INFO", "WARNING", "ERROR"
        message (str): The message to log
        """
        # Format the log message with a timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] [CrewTournament]: {message}"
        
        # Print to console
        print(formatted_message)
        
        # Additional logging to file if needed
        try:
            # Log to a file in the cog data directory
            data_path = cog_data_path(self)
            log_dir = data_path / "Logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            log_file = log_dir / "crew.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{formatted_message}\n")
        except Exception as e:
            # Don't let logging errors disrupt the bot
            print(f"Error writing to log file: {e}")
    
    # --- Utility Methods ---
    async def fetch_custom_emoji(self, emoji_url, guild):
        """Fetch and upload a custom emoji to the guild."""
        async with aiohttp.ClientSession() as session:
            async with session.get(emoji_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    try:
                        emoji = await guild.create_custom_emoji(name="crew_emoji", image=image_data)
                        return str(emoji)
                    except discord.Forbidden:
                        return "🏴‍☠️"  # Default emoji if permission denied
                    except Exception as e:
                        print(f"Error creating custom emoji: {e}")
                        return "🏴‍☠️"  # Default emoji on error
                return "🏴‍☠️"  # Default emoji if fetch fails

    def get_crews_for_guild(self, guild_id):
        """Get crews for a specific guild."""
        return self.crews.get(str(guild_id), {})

    # --- Setup Command Group ---
    @commands.group(name="crewsetup")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def crew_setup(self, ctx):
        """Commands for setting up the crew system."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `help crewsetup` for more information.")

    @crew_setup.command(name="init")
    async def setup_init(self, ctx):
        """Initialize the crew system for this server."""
        guild_id = str(ctx.guild.id)
        
        # Initialize guild namespaces if they don't exist
        if guild_id not in self.crews:
            self.crews[guild_id] = {}
        
        # Create data directory if it doesn't exist
        data_path = cog_data_path(self)
        crews_dir = data_path / "Crews"
        if not os.path.exists(crews_dir):
            os.makedirs(crews_dir, exist_ok=True)
        
        await self.config.guild(ctx.guild).finished_setup.set(True)
        await self.save_data(ctx.guild)
        await ctx.send("✅ Crew system initialized for this server. You can now create crews.")

    @crew_setup.command(name="reset")
    async def setup_reset(self, ctx):
        """Reset all crew data for this server."""
        guild_id = str(ctx.guild.id)
        
        # Clear data
        if guild_id in self.crews:
            self.crews[guild_id] = {}
        
        await self.save_data(ctx.guild)
        await ctx.send("✅ All crew data has been reset for this server.")

    @crew_setup.command(name="roles")
    async def setup_roles(self, ctx):
        """Create separator roles to organize crew roles in the role list."""
        guild = ctx.guild
        try:
            # Create separator roles
            top_separator = await guild.create_role(
                name="═════════ CREWS ═════════",
                color=discord.Color.dark_theme(),
                hoist=True,  # Makes the role show as a separator in the member list
                mentionable=False
            )
            
            bottom_separator = await guild.create_role(
                name="═════════════════════════",
                color=discord.Color.dark_theme(),
                mentionable=False
            )
            
            # Store separator role IDs in config
            await self.config.guild(guild).set_raw("separator_roles", value={
                "top": top_separator.id,
                "bottom": bottom_separator.id
            })
            
            await ctx.send("✅ Crew role separators created successfully!")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles.")
        except Exception as e:
            await ctx.send(f"❌ Error creating separator roles: {e}")

    @crew_setup.command(name="reorganize")
    @commands.admin_or_permissions(administrator=True)
    async def reorganize_roles(self, ctx):
        """Reorganize all crew roles between separators."""
        guild = ctx.guild
        guild_id = str(guild.id)
        crews = self.crews.get(guild_id, {})
        
        # Check if separator roles exist
        separator_roles = await self.config.guild(guild).get_raw("separator_roles", default=None)
        if not separator_roles:
            await ctx.send("❌ Separator roles don't exist. Creating them now...")
            await ctx.invoke(self.setup_roles)
            separator_roles = await self.config.guild(guild).get_raw("separator_roles", default={})
        
        top_separator = guild.get_role(separator_roles.get("top"))
        bottom_separator = guild.get_role(separator_roles.get("bottom"))
        
        if not top_separator or not bottom_separator:
            await ctx.send("❌ Separator roles couldn't be found. Please run `crewsetup roles` first.")
            return
        
        try:
            bottom_position = guild.roles.index(bottom_separator)
            
            # Collect all crew roles
            all_roles = []
            for crew_name, crew in crews.items():
                captain_role = guild.get_role(crew["captain_role"])
                vice_captain_role = guild.get_role(crew["vice_captain_role"])
                crew_role = guild.get_role(crew["crew_role"])
                
                if captain_role:
                    all_roles.append(captain_role)
                if vice_captain_role:
                    all_roles.append(vice_captain_role)
                if crew_role:
                    all_roles.append(crew_role)
            
            # Move all roles above the bottom separator
            for role in all_roles:
                await role.edit(position=bottom_position+1)
            
            await ctx.send("✅ All crew roles have been reorganized between the separators.")
        except Exception as e:
            await ctx.send(f"❌ Error reorganizing roles: {e}")

    @commands.command(name="debugcrews")
    @commands.admin_or_permissions(administrator=True)
    async def debug_crews(self, ctx):
        """Debug command to show the raw crew data and fix any formatting issues."""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews found.")
            return
        
        # Show the raw data
        crew_data_text = ""
        for crew_name, crew_data in crews.items():
            # Get member count by role
            crew_role_id = crew_data.get("crew_role")
            crew_role = ctx.guild.get_role(crew_role_id) if crew_role_id else None
            role_member_count = len(crew_role.members) if crew_role else 0
            
            crew_data_text += f"Crew: '{crew_name}'\n"
            crew_data_text += f"- Stored name: '{crew_data['name']}'\n"
            crew_data_text += f"- Emoji: {crew_data['emoji']}\n"
            crew_data_text += f"- Members in array: {len(crew_data['members'])}\n"
            crew_data_text += f"- Members in role: {role_member_count}\n\n"
        
        # Check for mention-like crew names and offer to fix them
        has_mention_format = any("<@" in name for name in crews.keys())
        
        if has_mention_format:
            crew_data_text += "\nDetected mention formatting in crew names. Use `fixcrewnames` to fix this issue."
        
        # Send the debug info in chunks if needed
        if len(crew_data_text) > 1900:
            chunks = [crew_data_text[i:i+1900] for i in range(0, len(crew_data_text), 1900)]
            for chunk in chunks:
                await ctx.send(f"```\n{chunk}\n```")
        else:
            await ctx.send(f"```\n{crew_data_text}\n```")
    
    @commands.command(name="fixcrewemoji")
    @commands.admin_or_permissions(administrator=True)
    async def fix_crew_emoji(self, ctx):
        """Fix crew emojis that have user IDs stored instead of actual emojis."""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews found.")
            return
        
        fixed_count = 0
        
        for crew_name, crew_data in crews.items():
            emoji = crew_data["emoji"]
            
            # Check if the emoji is actually a user ID
            if emoji and emoji.startswith("<@") and emoji.endswith(">"):
                # It's a user ID, not an emoji - set a default emoji
                crew_data["emoji"] = "🏴‍☠️"  # Default fallback emoji
                fixed_count += 1
                
                # Print debug info
                await ctx.send(f"Fixed crew `{crew_name}`: Changed emoji from `{emoji}` to 🏴‍☠️")
                
            # Also check if we have a proper crew name or if it's user ID
            if "<@" in crew_name:
                # The crew name has a user ID in it - need to create a new entry
                # Extract the actual name after the mention
                parts = crew_name.split()
                if len(parts) > 1:
                    # The first part is the mention, remaining parts form the actual name
                    new_name = " ".join(parts[1:])
                    
                    # Create a new entry with the fixed name
                    crews[new_name] = crew_data.copy()
                    crews[new_name]["name"] = new_name
                    
                    # Delete the old entry
                    del crews[crew_name]
                    
                    await ctx.send(f"Fixed crew name from `{crew_name}` to `{new_name}`")
                    fixed_count += 1
        
        # Save the changes
        if fixed_count > 0:
            await self.save_crews(ctx.guild)
            await ctx.send(f"✅ Fixed {fixed_count} crew emojis/names.")
        else:
            await ctx.send("✅ No crews needed fixing.")

    # --- Crew Command Group ---
    @commands.group(name="crew")
    @commands.guild_only()
    async def crew_commands(self, ctx):
        """Commands for managing crews."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `help crew` for more information.")

    @crew_commands.command(name="create")
    @commands.admin_or_permissions(administrator=True)
    async def crew_create(self, ctx, *, args):
        """Create a new crew with multi-word name.
        
        Usage:
        [p]crew create "The Shadow Armada" 🏴‍☠️ @Captain
        [p]crew create "Blue Pirates" 🔵
        
        Args:
            args: A string containing the crew name in quotes, 
                  followed by an emoji and optionally @Captain
        """
        # Parse arguments
        args_parts = args.split('"')
        
        if len(args_parts) < 3:
            await ctx.send("❌ Crew name must be in quotes. Example: `crew create \"The Shadow Armada\" 🏴‍☠️ @Captain`")
            return
        
        crew_name = args_parts[1].strip()
        
        # Ensure the crew name doesn't start with a mention or have unexpected formatting
        if crew_name.startswith('<@') or '@' in crew_name:
            await ctx.send("❌ Crew name should not include mentions or @ symbols.")
            return
            
        remaining = args_parts[2].strip()
        
        # Extract emoji and captain from remaining text
        remaining_parts = remaining.split()
        if not remaining_parts:
            await ctx.send("❌ Missing emoji. Example: `crew create \"The Shadow Armada\" 🏴‍☠️ @Captain`")
            return
        
        crew_emoji = remaining_parts[0]
        
        # Validate that the emoji is actually an emoji and not a user mention
        if crew_emoji.startswith("<@"):
            await ctx.send("❌ The first parameter after the crew name should be an emoji, not a user mention.")
            return
        
        # Find captain mention if it exists
        captain = ctx.author  # Default to command user
        if len(remaining_parts) > 1 and remaining_parts[1].startswith('<@') and remaining_parts[1].endswith('>'):
            try:
                captain_id = int(remaining_parts[1].strip('<@!&>'))
                mentioned_captain = ctx.guild.get_member(captain_id)
                if mentioned_captain:
                    captain = mentioned_captain
            except ValueError:
                pass  # Invalid ID format, use default captain
        
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Initialize guild namespace if not exists
        if guild_id not in self.crews:
            self.crews[guild_id] = {}
        
        # Now check if the crew already exists
        if crew_name in self.crews[guild_id]:
            await ctx.send(f"❌ A crew with the name `{crew_name}` already exists.")
            return
    
        guild = ctx.guild
    
        # Check if the emoji is a custom emoji
        if crew_emoji.startswith("<:") and crew_emoji.endswith(">"):
            try:
                # For custom emojis like <:emojiname:12345>
                emoji_parts = crew_emoji.split(":")
                if len(emoji_parts) >= 3:
                    emoji_id = emoji_parts[2][:-1]  # Remove the trailing '>'
                    emoji = self.bot.get_emoji(int(emoji_id))
                    if emoji:
                        crew_emoji = str(emoji)
                    else:
                        # If we can't find the emoji, use a default
                        await ctx.send(f"⚠️ Couldn't find the custom emoji. Using default emoji instead.")
                        crew_emoji = "🏴‍☠️"
            except Exception as e:
                await ctx.send(f"❌ Error processing custom emoji: {e}")
                crew_emoji = "🏴‍☠️"  # Default fallback
    
        # Check if separator roles exist, if not create them
        separator_roles = await self.config.guild(guild).get_raw("separator_roles", default=None)
        if not separator_roles:
            await ctx.invoke(self.setup_roles)
            separator_roles = await self.config.guild(guild).get_raw("separator_roles", default={})
        
        # Get position for new roles
        position_reference = None
        if separator_roles:
            top_separator = guild.get_role(separator_roles.get("top"))
            bottom_separator = guild.get_role(separator_roles.get("bottom"))
            position_reference = bottom_separator
        
        try:
            # Create roles with updated naming format (without emoji)
            captain_role = await guild.create_role(
                name=f"{crew_name} Captain",
                color=discord.Color.gold(),
                mentionable=True
            )
            vice_captain_role = await guild.create_role(
                name=f"{crew_name} Vice Captain",
                color=discord.Color(0xC0C0C0),  # Silver color using hex code
                mentionable=True
            )
            crew_role = await guild.create_role(
                name=f"{crew_name} Member",
                color=discord.Color.blue(),
                mentionable=True
            )
            
            # Position roles between separators
            if position_reference:
                positions = guild.roles.index(position_reference)
                await captain_role.edit(position=positions+1)
                await vice_captain_role.edit(position=positions+1)
                await crew_role.edit(position=positions+1)
                
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create roles.")
            return
        except Exception as e:
            await ctx.send(f"❌ Error creating roles: {e}")
            return
        
        # Add the new crew to the existing crews dictionary
        self.crews[guild_id][crew_name] = {
            "name": crew_name,
            "emoji": crew_emoji,
            "members": [captain.id],
            "captain_role": captain_role.id,
            "vice_captain_role": vice_captain_role.id,
            "crew_role": crew_role.id,
            "stats": {
                "wins": 0,
                "losses": 0,
                "tournaments_won": 0,
                "tournaments_participated": 0
            },
            "created_at": ctx.message.created_at.isoformat()
        }
        
        # Give only captain role to captain (not member role)
        await captain.add_roles(captain_role)
        
        # Update nickname with truncation
        try:
            original_nick = captain.display_name
            # Make sure we don't add the emoji twice
            if not original_nick.startswith(crew_emoji):
                success = await self.set_nickname_safely(captain, crew_emoji, original_nick, is_captain=True)
                if not success:
                    await ctx.send(f"⚠️ I couldn't update {captain.display_name}'s nickname due to technical issues, but the crew was created successfully.")
        except Exception as e:
            await ctx.send(f"⚠️ I couldn't update {captain.display_name}'s nickname: {str(e)}, but the crew was created successfully.")
            
        await self.save_crews(ctx.guild)
        await ctx.send(f"✅ Crew `{crew_name}` created with {captain.mention} as captain!")
    
    @crew_commands.command(name="join")
    async def crew_join(self, ctx, *, crew_name: str):
        """Join a crew."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if crew_name not in crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return
    
        member = ctx.author
        crew = crews[crew_name]
    
        # Check if already in this crew
        if member.id in crew["members"]:
            await ctx.send("❌ You are already in this crew.")
            return
    
        # Check if already in another crew
        for other_crew_name, other_crew in crews.items():
            if member.id in other_crew["members"]:
                await ctx.send("❌ You cannot switch crews once you join one.")
                return
    
        # Add to crew
        crew["members"].append(member.id)
        
        # Assign crew role
        crew_role = ctx.guild.get_role(crew["crew_role"])
        if crew_role:
            try:
                await member.add_roles(crew_role)
            except discord.Forbidden:
                await ctx.send("⚠️ I don't have permission to assign roles, but you've been added to the crew.")
    
        # Update nickname with crew emoji
        try:
            original_nick = member.display_name
            # Make sure we don't add the emoji twice
            if not original_nick.startswith(crew["emoji"]):
                success = await self.set_nickname_safely(member, crew["emoji"], original_nick)
                if not success:
                    await ctx.send("⚠️ I don't have permission to change your nickname, but you've joined the crew.")
        except Exception as e:
            await ctx.send(f"⚠️ I couldn't update your nickname, but you've joined the crew. Error: {str(e)}")
            
        await self.save_crews(ctx.guild)
        await ctx.send(f"✅ You have joined the crew `{crew_name}`!")
    
    @crew_commands.command(name="leave")
    async def crew_leave(self, ctx):
        """Leave your current crew."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        member = ctx.author
        user_crew = None
        
        # Find the crew the user is in
        for crew_name, crew in crews.items():
            if member.id in crew["members"]:
                user_crew = crew_name
                break
                
        if not user_crew:
            await ctx.send("❌ You are not in any crew.")
            return
            
        crew = crews[user_crew]
        
        # Check if user is captain
        captain_role = ctx.guild.get_role(crew["captain_role"])
        if captain_role in member.roles:
            await ctx.send("❌ As the captain, you cannot leave the crew. Transfer captaincy first or ask an admin to delete the crew.")
            return
            
        # Remove from crew
        crew["members"].remove(member.id)
        
        # Remove crew roles
        for role_key in ["vice_captain_role", "crew_role"]:
            if role_key in crew:
                role = ctx.guild.get_role(crew[role_key])
                if role and role in member.roles:
                    try:
                        await member.remove_roles(role)
                    except discord.Forbidden:
                        await ctx.send(f"⚠️ Couldn't remove {role.name} role due to permission issues.")
        
        # Restore original nickname
        try:
            current_nick = member.display_name
            if current_nick.startswith(f"{crew['emoji']} "):
                new_nick = current_nick[len(f"{crew['emoji']} "):]
                await member.edit(nick=new_nick)
        except discord.Forbidden:
            await ctx.send("⚠️ I don't have permission to restore your original nickname.")
            
        await self.save_crews(ctx.guild)
        await ctx.send(f"✅ You have left the crew `{user_crew}`.")
    
    @crew_commands.command(name="delete")
    @commands.admin_or_permissions(administrator=True)
    async def crew_delete(self, ctx, *, crew_name: str):
        """Delete a crew. Only admins can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if crew_name not in crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return

        crew = crews[crew_name]
        
        # Delete roles if they exist
        for role_key in ["captain_role", "vice_captain_role", "crew_role"]:
            if role_key in crew:
                role = ctx.guild.get_role(crew[role_key])
                if role:
                    try:
                        await role.delete()
                    except discord.Forbidden:
                        await ctx.send(f"⚠️ Couldn't delete {role.name} due to permission issues.")
                    except Exception as e:
                        await ctx.send(f"⚠️ Error deleting {role_key}: {e}")

        # Delete crew
        del self.crews[guild_id][crew_name]
        await self.save_data(ctx.guild)
        await ctx.send(f"✅ Crew `{crew_name}` has been deleted.")

    @crew_commands.command(name="invite")
    async def crew_invite(self, ctx, member: discord.Member):
        """Invite a member to your crew. Only captains and vice-captains can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        author = ctx.author
        author_crew = None
        
        # Find the crew the command issuer is in by checking roles instead of member IDs
        for crew_name, crew in crews.items():
            captain_role_id = crew.get("captain_role")
            vice_captain_role_id = crew.get("vice_captain_role")
            crew_role_id = crew.get("crew_role")
            
            captain_role = ctx.guild.get_role(captain_role_id) if captain_role_id else None
            vice_captain_role = ctx.guild.get_role(vice_captain_role_id) if vice_captain_role_id else None
            crew_role = ctx.guild.get_role(crew_role_id) if crew_role_id else None
            
            # Check if author has any of the crew roles
            if (captain_role and captain_role in author.roles) or \
               (vice_captain_role and vice_captain_role in author.roles) or \
               (crew_role and crew_role in author.roles):
                author_crew = crew_name
                break
                
        if not author_crew:
            await ctx.send("❌ You are not in any crew.")
            return
            
        crew = crews[author_crew]
        
        # Check if author is captain or vice captain
        captain_role = ctx.guild.get_role(crew["captain_role"])
        vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])
        
        if not (captain_role in author.roles or vice_captain_role in author.roles):
            await ctx.send("❌ Only the captain or vice-captain can invite members.")
            return
        
        # Check if target is already in a crew by checking roles
        for other_crew_name, other_crew in crews.items():
            crew_role_id = other_crew.get("crew_role")
            captain_role_id = other_crew.get("captain_role")
            vice_captain_role_id = other_crew.get("vice_captain_role")
            
            crew_role = ctx.guild.get_role(crew_role_id) if crew_role_id else None
            captain_role = ctx.guild.get_role(captain_role_id) if captain_role_id else None
            vice_captain_role = ctx.guild.get_role(vice_captain_role_id) if vice_captain_role_id else None
            
            if ((crew_role and crew_role in member.roles) or 
                (captain_role and captain_role in member.roles) or 
                (vice_captain_role and vice_captain_role in member.roles)):
                await ctx.send(f"❌ {member.display_name} is already in the crew `{other_crew_name}`.")
                return
        
        # Send invitation
        crew_emoji = crew["emoji"]
        invite_embed = discord.Embed(
            title=f"{crew_emoji} Crew Invitation",
            description=f"{author.mention} is inviting you to join the crew `{author_crew}`!",
            color=0x00FF00,
        )
        
        # Create buttons for accept/decline
        class InviteView(discord.ui.View):
            def __init__(self, cog, crew_name, crew_emoji):
                super().__init__(timeout=300)  # 5 minute timeout
                self.cog = cog
                self.crew_name = crew_name
                self.crew_emoji = crew_emoji
                
            @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
            async def accept_button(self, button, interaction):
                if interaction.user.id != member.id:
                    await interaction.response.send_message("❌ This invitation is not for you.", ephemeral=True)
                    return
                    
                crew = self.cog.crews.get(guild_id, {}).get(self.crew_name)
                if not crew:
                    await interaction.response.send_message("❌ This crew no longer exists.", ephemeral=True)
                    return
                    
                # Add to crew
                crew["members"].append(member.id)
                
                # Assign crew role
                crew_role = interaction.guild.get_role(crew["crew_role"])
                if crew_role:
                    try:
                        await member.add_roles(crew_role)
                    except discord.Forbidden:
                        await interaction.response.send_message(f"✅ You have joined the crew `{self.crew_name}`! Note: I couldn't assign you the crew role due to permission issues.", ephemeral=True)
                        await self.cog.save_crews(interaction.guild)
                        return
                
                # Update nickname with crew emoji
                try:
                    original_nick = member.display_name
                    # Make sure we don't add the emoji twice
                    if not original_nick.startswith(self.crew_emoji):
                        success = await self.cog.set_nickname_safely(member, self.crew_emoji, original_nick)
                        if not success:
                            await interaction.response.send_message(f"✅ You have joined the crew `{self.crew_name}`! Note: I couldn't update your nickname due to permission issues.", ephemeral=True)
                            await self.cog.save_crews(interaction.guild)
                            return
                except Exception as e:
                    await interaction.response.send_message(f"✅ You have joined the crew `{self.crew_name}`! Note: I couldn't update your nickname. Error: {str(e)}", ephemeral=True)
                    await self.cog.save_crews(interaction.guild)
                    return
                    
                await self.cog.save_crews(interaction.guild)
                await interaction.response.send_message(f"✅ You have joined the crew `{self.crew_name}`!", ephemeral=True)
                
                # Notify the channel
                try:
                    await interaction.message.edit(content=f"✅ {member.mention} has accepted the invitation to join `{self.crew_name}`!", embed=None, view=None)
                except:
                    pass
                    
            @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
            async def decline_button(self, button, interaction):
                if interaction.user.id != member.id:
                    await interaction.response.send_message("❌ This invitation is not for you.", ephemeral=True)
                    return
                    
                await interaction.response.send_message(f"You have declined the invitation to join the crew `{self.crew_name}`.", ephemeral=True)
                
                # Notify the channel
                try:
                    await interaction.message.edit(content=f"❌ {member.mention} has declined the invitation to join `{self.crew_name}`.", embed=None, view=None)
                except:
                    pass
        
        # Send the invitation with buttons
        invite_view = InviteView(self, author_crew, crew_emoji)
        await ctx.send(f"{member.mention}, you've been invited to a crew!", embed=invite_embed, view=invite_view)
        await ctx.send(f"✅ Invitation sent to {member.mention}!")
    
    @crew_commands.command(name="edit")
    @commands.admin_or_permissions(administrator=True)
    async def crew_edit(self, ctx, crew_name: str, property_type: str, *, new_value: str):
        """
        Edit crew properties.
        
        Usage:
        [p]crew edit "Blue Pirates" name "Red Pirates"
        [p]crew edit "Blue Pirates" emoji 🔴
        
        Only administrators can use this command.
        """
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if crew_name not in crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return
        
        crew = crews[crew_name]
        property_type = property_type.lower()
        
        # Handle name change
        if property_type == "name":
            if new_value in crews:
                await ctx.send(f"❌ A crew with the name `{new_value}` already exists.")
                return
                
            # Update role names
            for role_key, role_suffix in [
                ("captain_role", "Captain"),
                ("vice_captain_role", "Vice Captain"),
                ("crew_role", "Member")
            ]:
                role = ctx.guild.get_role(crew[role_key])
                if role:
                    try:
                        await role.edit(name=f"{new_value} {role_suffix}")
                    except discord.Forbidden:
                        await ctx.send(f"⚠️ Couldn't rename {role.name} due to permission issues.")
                        
            # Update the crew name in the crews dictionary
            crews[new_value] = crews.pop(crew_name)
            crews[new_value]["name"] = new_value
            
            await self.save_data(ctx.guild)
            await ctx.send(f"✅ Crew `{crew_name}` has been renamed to `{new_value}`.")
        
        # Handle emoji change
        elif property_type == "emoji":
            old_emoji = crew["emoji"]
            
            # Validate that the emoji is actually an emoji and not a user mention
            if new_value.startswith("<@"):
                await ctx.send("❌ Please provide a valid emoji, not a user mention.")
                return
                
            # Check if the emoji is a custom emoji
            if new_value.startswith("<:") and new_value.endswith(">"):
                try:
                    # For custom emojis like <:emojiname:12345>
                    emoji_parts = new_value.split(":")
                    if len(emoji_parts) >= 3:
                        emoji_id = emoji_parts[2][:-1]  # Remove the trailing '>'
                        emoji = self.bot.get_emoji(int(emoji_id))
                        if emoji:
                            new_value = str(emoji)
                        else:
                            # If we can't find the emoji, use a default
                            await ctx.send(f"⚠️ Couldn't find the custom emoji. Using default emoji instead.")
                            new_value = "🏴‍☠️"
                except Exception as e:
                    await ctx.send(f"❌ Error processing custom emoji: {e}")
                    new_value = "🏴‍☠️"  # Default fallback
                    
            # Update the emoji in the crew data
            crew["emoji"] = new_value
            
            # Update nicknames of crew members
            updated_count = 0
            failed_count = 0
            
            for member_id in crew["members"]:
                member = ctx.guild.get_member(member_id)
                if member:
                    try:
                        current_nick = member.display_name
                        # Check if the nickname starts with the old emoji
                        if current_nick.startswith(f"{old_emoji} "):
                            new_nick = current_nick.replace(f"{old_emoji} ", f"{new_value} ", 1)
                            await member.edit(nick=new_nick)
                            updated_count += 1
                    except Exception:
                        failed_count += 1
                        
            await self.save_data(ctx.guild)
            
            status = f"✅ Crew emoji changed from {old_emoji} to {new_value}."
            if updated_count > 0:
                status += f" Updated {updated_count} member nicknames."
            if failed_count > 0:
                status += f" Failed to update {failed_count} member nicknames due to permission issues."
                
            await ctx.send(status)
        
        else:
            await ctx.send("❌ Invalid property type. Valid options are: `name`, `emoji`.")
    
    @crew_setup.command(name="finish")
    async def setup_finish(self, ctx):
        """Finalizes crew setup and posts an interactive message for users to join crews."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews have been created yet. Create some crews first with `crew create`.")
            return
        
        # Create an embed with all crew information
        embed = discord.Embed(
            title="🏴‍☠️ Available Crews",
            description="Click the buttons below to join a crew!",
            color=0x00FF00,
        )
        
        for crew_name, crew_data in crews.items():
            # Find the captain
            captain_role = ctx.guild.get_role(crew_data["captain_role"])
            crew_role = ctx.guild.get_role(crew_data["crew_role"])
            
            # Get member count by role instead of stored IDs
            member_count = len(crew_role.members) if crew_role else 0
            
            # Find captain by role across all guild members
            captain = next((m for m in ctx.guild.members if captain_role and captain_role in m.roles), None)
            
            embed.add_field(
                name=f"{crew_data['emoji']} {crew_name}",
                value=f"Captain: {captain.mention if captain else 'None'}\nMembers: {member_count}",
                inline=True
            )
        
        # Create a view with buttons for each crew
        view = discord.ui.View(timeout=None)
        for crew_name, crew_data in crews.items():
            view.add_item(CrewButton(crew_name, crew_data["emoji"], self))
        
        # Send the interactive message
        await ctx.send("✅ Crew setup has been finalized! Here are the available crews:", embed=embed, view=view)
        await ctx.send("Users can now join crews using the buttons above or by using the `crew join` command.")

    @crew_commands.command(name="finish")
    @commands.admin_or_permissions(administrator=True)
    async def crew_finish(self, ctx, channel_id: int = None):
        """
        Posts all crews with join buttons in the specified channel.
        If no channel is specified, posts in the current channel.
        
        Usage:
        [p]crew finish
        [p]crew finish 123456789012345678
        """
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews have been created yet. Create some crews first with `crew create`.")
            return
        
        # Determine the target channel
        target_channel = None
        if channel_id:
            target_channel = ctx.guild.get_channel(channel_id)
            if not target_channel:
                await ctx.send(f"❌ Could not find a channel with ID {channel_id}.")
                return
        else:
            target_channel = ctx.channel
        
        # Check permissions in the target channel
        if not target_channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(f"❌ I don't have permission to send messages in {target_channel.mention}.")
            return
        
        # Create an eye-catching header
        header_embed = discord.Embed(
            title="🏴‍☠️ Join a Crew Today! 🏴‍☠️",
            description="Select a crew below to join. Choose wisely - you can't switch once you join!",
            color=discord.Color.gold()
        )
        await target_channel.send(embed=header_embed)
        
        # Post each crew with its own join button
        for crew_name, crew_data in crews.items():
            # Find the captain
            captain_role = ctx.guild.get_role(crew_data["captain_role"])
            crew_role = ctx.guild.get_role(crew_data["crew_role"])
            
            # Get member count by role instead of stored IDs
            member_count = len(crew_role.members) if crew_role else 0
            
            # Find captain by role across all guild members
            captain = next((m for m in ctx.guild.members if captain_role and captain_role in m.roles), None)
            
            # Create the crew embed
            crew_embed = discord.Embed(
                title=f"{crew_data['emoji']} {crew_name}",
                description=f"Captain: {captain.mention if captain else 'None'}\nMembers: {member_count}",
                color=discord.Color.blue()
            )
            
            # Add stats if they exist
            if "stats" in crew_data:
                stats = crew_data["stats"]
                crew_embed.add_field(
                    name="Statistics",
                    value=f"Wins: {stats['wins']}\nLosses: {stats['losses']}\nTournaments Won: {stats.get('tournaments_won', 0)}",
                    inline=True
                )
            
            # Create and send the view with a join button
            view = CrewView(crew_name, crew_data["emoji"], self)
            await target_channel.send(embed=crew_embed, view=view)
        
        # Confirmation message
        await ctx.send(f"✅ Successfully posted all crews in {target_channel.mention}!")

    @crew_commands.command(name="list")
    async def crew_list(self, ctx):
        """List all available crews for users to join."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews available. Ask an admin to create some with `crew create`.")
            return
    
        embed = discord.Embed(
            title="Available Crews",
            description="Here's a list of all crews in this server.",
            color=0x00FF00,
        )
        
        for crew_name, crew_data in crews.items():
            # Safely get role IDs, using None as default
            captain_role_id = crew_data.get("captain_role")
            crew_role_id = crew_data.get("crew_role")
            
            captain_role = ctx.guild.get_role(captain_role_id) if captain_role_id else None
            crew_role = ctx.guild.get_role(crew_role_id) if crew_role_id else None
            
            # Count members by role instead of by stored member IDs
            member_count = len(crew_role.members) if crew_role else len(crew_data.get("members", []))
            
            # Find captain from all guild members
            captain = next((m for m in ctx.guild.members if captain_role and captain_role in m.roles), None)
            
            # Get stats safely
            stats = crew_data.get("stats", {"wins": 0, "losses": 0})
            
            # Get emoji safely
            emoji = crew_data.get("emoji", "🏴‍☠️")
                    
            embed.add_field(
                name=f"{emoji} {crew_name}",
                value=f"Captain: {captain.mention if captain else 'None'}\nMembers: {member_count}\nWins: {stats.get('wins', 0)} | Losses: {stats.get('losses', 0)}",
                inline=True
            )
    
        await ctx.send(embed=embed)
    
    @crew_commands.command(name="view")
    async def crew_view(self, ctx, *, crew_name: str):
        """View the details of a crew with a clean, formatted display."""
        import datetime  # Add this import for the timestamp
        import hashlib  # For creating a consistent color from crew name
        
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews available.")
            return
        
        # Try different methods to find the crew
        crew_data = None
        matched_crew = None
        
        # Method 1: Direct dictionary lookup (exact match)
        if crew_name in crews:
            crew_data = crews[crew_name]
            matched_crew = crew_name
        else:
            # Method 2: Case-insensitive match on keys
            for key in crews.keys():
                if key.lower() == crew_name.lower():
                    crew_data = crews[key]
                    matched_crew = key
                    break
                    
            # Method 3: Match on internal 'name' field
            if not crew_data:
                for key, data in crews.items():
                    internal_name = data.get('name', '')
                    if internal_name and internal_name.lower() == crew_name.lower():
                        crew_data = data
                        matched_crew = key
                        break
            
            # Method 4: Partial match on keys
            if not crew_data:
                for key in crews.keys():
                    if crew_name.lower() in key.lower():
                        crew_data = crews[key]
                        matched_crew = key
                        break
                        
            # Method 5: Partial match on internal 'name' field
            if not crew_data:
                for key, data in crews.items():
                    internal_name = data.get('name', '')
                    if internal_name and crew_name.lower() in internal_name.lower():
                        crew_data = data
                        matched_crew = key
                        break
                        
        # If still not found, show an error with available crews
        if not crew_data:
            crew_list = ", ".join([f"`{key}`" for key in crews.keys()])
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.\n\nAvailable crews: {crew_list}")
            return

        # Continue with creating the embed using the found crew_data
        try:
            # Get role objects
            captain_role_id = crew_data.get("captain_role")
            vice_captain_role_id = crew_data.get("vice_captain_role")
            crew_role_id = crew_data.get("crew_role")
            
            captain_role = ctx.guild.get_role(captain_role_id) if captain_role_id else None
            vice_captain_role = ctx.guild.get_role(vice_captain_role_id) if vice_captain_role_id else None
            crew_role = ctx.guild.get_role(crew_role_id) if crew_role_id else None
            
            # Get members by role instead of stored IDs
            member_objects = crew_role.members if crew_role else []
            
            # Find captain and vice captain using roles
            # First look for members with the specific roles
            captain = next((m for m in ctx.guild.members if captain_role and captain_role in m.roles), None)
            vice_captain = next((m for m in ctx.guild.members if vice_captain_role and vice_captain_role in m.roles), None)
            
            # Get regular members (exclude captain and vice captain)
            regular_members = [m for m in member_objects if m not in [captain, vice_captain]]
            
            # Create the embed with a nicer appearance
            emoji = crew_data.get("emoji", "🏴‍☠️")
            
            # Get a color based on the crew name or use a default color
            # This creates a consistent color for each crew based on its name
            color_hash = int(hashlib.md5(matched_crew.encode()).hexdigest()[:6], 16)
            
            embed = discord.Embed(
                title=f"{emoji} Crew: {matched_crew}",
                description=f"**{len(member_objects)} Members**",
                color=color_hash,
            )
            
            # Add leadership section with both captain and vice captain in one field
            leadership = []
            if captain:
                leadership.append(f"**Captain:** {captain.display_name}")
            else:
                leadership.append("**Captain:** *None assigned*")
                
            if vice_captain:
                leadership.append(f"**Vice Captain:** {vice_captain.display_name}")
            else:
                leadership.append("**Vice Captain:** *None assigned*")
                
            embed.add_field(
                name="👑 Leadership",
                value="\n".join(leadership),
                inline=False
            )
            
            # Add regular members with better formatting
            if regular_members:
                # First add all members we could resolve using display_name
                member_strings = [m.display_name for m in regular_members[:15]]
                
                # Format the member list as a bulleted list if there are members
                if member_strings:
                    member_list = "\n".join([f"• {name}" for name in member_strings])
                    
                    total_remaining = len(regular_members) - len(member_strings)
                    if total_remaining > 0:
                        member_list += f"\n*...and {total_remaining} more*"
                else:
                    member_list = "*No regular members yet*"
                    
                embed.add_field(
                    name="👥 Members", 
                    value=member_list, 
                    inline=False
                )
            else:
                embed.add_field(
                    name="👥 Members", 
                    value="*No regular members yet*", 
                    inline=False
                )
            
            # Add statistics with icons and better formatting
            stats = crew_data.get("stats", {})
            if not stats:
                stats = {"wins": 0, "losses": 0, "tournaments_won": 0, "tournaments_participated": 0}
            
            # Calculate win rate
            total_matches = stats.get('wins', 0) + stats.get('losses', 0)
            win_rate = round((stats.get('wins', 0) / total_matches) * 100) if total_matches > 0 else 0
            
            # Format stats with emojis
            embed.add_field(
                name="📊 Statistics",
                value=(
                    f"🏆 **Wins:** {stats.get('wins', 0)}\n"
                    f"❌ **Losses:** {stats.get('losses', 0)}\n"
                    f"🏅 **Tournaments Won:** {stats.get('tournaments_won', 0)}\n"
                    f"🏟️ **Tournaments Entered:** {stats.get('tournaments_participated', 0)}"
                ),
                inline=False
            )
            
            # Add footer with timestamp
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url if hasattr(ctx.author, 'display_avatar') else None)
            embed.timestamp = datetime.datetime.now()
            
            # Send the embed without any view/buttons
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error displaying crew information: {str(e)}")
            
    @commands.command(name="cleancrewids")
    @commands.admin_or_permissions(administrator=True)
    async def clean_crew_ids(self, ctx):
        """Clean up crew member IDs and replace unresolvable mentions with usernames."""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews found.")
            return
        
        fixed_count = 0
        username_replacements = 0
        
        for crew_name, crew_data in crews.items():
            clean_members = []
            usernames_added = []
            
            # Process each member ID
            for mid in crew_data.get("members", []):
                try:
                    # Handle raw mentions and string IDs
                    if isinstance(mid, str):
                        if mid.isdigit():
                            # Convert string ID to int
                            clean_members.append(int(mid))
                            fixed_count += 1
                        elif mid.startswith("<@") and mid.endswith(">"):
                            # Extract ID from mention
                            user_id = int(mid.strip("<@!&>"))
                            clean_members.append(user_id)
                            fixed_count += 1
                        else:
                            # Check if it might be a username
                            member = discord.utils.get(ctx.guild.members, display_name=mid)
                            if member:
                                clean_members.append(member.id)
                                usernames_added.append(f"{mid} → {member.id}")
                                username_replacements += 1
                            else:
                                # Keep the string if we can't resolve it
                                clean_members.append(mid)
                    else:
                        # Already an int ID
                        clean_members.append(mid)
                except Exception as e:
                    await ctx.send(f"⚠️ Error cleaning ID in crew `{crew_name}`: `{mid}` - {str(e)}")
                    # Keep the original ID if we can't clean it
                    clean_members.append(mid)
            
            # Update the crew with clean member IDs
            crew_data["members"] = clean_members
        
        # Save the changes
        await self.save_crews(ctx.guild)
        
        status = f"✅ Cleaned {fixed_count} member IDs and resolved {username_replacements} usernames."
        if usernames_added:
            status += "\n\nResolved usernames:"
            for entry in usernames_added[:10]:  # Show first 10 to avoid overly long messages
                status += f"\n- {entry}"
            if len(usernames_added) > 10:
                status += f"\n- and {len(usernames_added) - 10} more..."
        
        await ctx.send(status)
    
    @crew_commands.command(name="kick")
    async def crew_kick(self, ctx, member: discord.Member):
        """Kick a member from your crew. Only captains and vice-captains can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        author = ctx.author
        author_crew = None
        
        # Find the crew the command issuer is in
        for crew_name, crew in crews.items():
            if author.id in crew["members"]:
                author_crew = crew_name
                break
                
        if not author_crew:
            await ctx.send("❌ You are not in any crew.")
            return
            
        crew = crews[author_crew]
        
        # Check if author is captain or vice captain
        captain_role = ctx.guild.get_role(crew["captain_role"])
        vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])
        
        if not (captain_role in author.roles or vice_captain_role in author.roles):
            await ctx.send("❌ Only the captain or vice-captain can kick members.")
            return
            
        # Check if target is in the same crew
        if member.id not in crew["members"]:
            await ctx.send(f"❌ {member.display_name} is not a member of your crew.")
            return
            
        # Check if target is the captain
        if captain_role in member.roles and author != member:
            await ctx.send("❌ You cannot kick the captain.")
            return
            
        # Remove from crew
        crew["members"].remove(member.id)
        
        # Remove crew roles
        for role_key in ["captain_role", "vice_captain_role", "crew_role"]:
            if role_key in crew:
                role = ctx.guild.get_role(crew[role_key])
                if role and role in member.roles:
                    try:
                        await member.remove_roles(role)
                    except discord.Forbidden:
                        await ctx.send(f"⚠️ Couldn't remove {role.name} role due to permission issues.")
        
        # Update nickname
        try:
            # Remove crew emoji from nickname
            new_nick = member.display_name
            if crew["emoji"] in new_nick:
                new_nick = new_nick.replace(f"{crew['emoji']} ", "")
                await member.edit(nick=new_nick)
        except discord.Forbidden:
            pass
            
        await self.save_crews(ctx.guild)
        await ctx.send(f"✅ {member.display_name} has been kicked from the crew `{author_crew}`.")

    @crew_commands.command(name="promote")
    async def crew_promote(self, ctx, member: discord.Member):
        """Promote a crew member to vice-captain. Only the captain can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        author = ctx.author
        author_crew = None
        
        # Find the crew the command issuer is in
        for crew_name, crew in crews.items():
            if author.id in crew["members"]:
                author_crew = crew_name
                break
                
        if not author_crew:
            await ctx.send("❌ You are not in any crew.")
            return
            
        crew = crews[author_crew]
        
        # Check if author is captain
        captain_role = ctx.guild.get_role(crew["captain_role"])
        if captain_role not in author.roles:
            await ctx.send("❌ Only the captain can promote members to vice-captain.")
            return
            
        # Check if target is in the same crew
        if member.id not in crew["members"]:
            await ctx.send(f"❌ {member.display_name} is not a member of your crew.")
            return
            
        # Check if target is already a vice-captain
        vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])
        if vice_captain_role in member.roles:
            await ctx.send(f"❌ {member.display_name} is already a vice-captain.")
            return
            
        # Promote to vice-captain
        try:
            await member.add_roles(vice_captain_role)
            await ctx.send(f"✅ {member.display_name} has been promoted to vice-captain of `{author_crew}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to assign roles.")
            
    @crew_commands.command(name="demote")
    async def crew_demote(self, ctx, member: discord.Member):
        """Demote a vice-captain to regular member. Only the captain can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        author = ctx.author
        author_crew = None
        
        # Find the crew the command issuer is in
        for crew_name, crew in crews.items():
            if author.id in crew["members"]:
                author_crew = crew_name
                break
                
        if not author_crew:
            await ctx.send("❌ You are not in any crew.")
            return
            
        crew = crews[author_crew]
        
        # Check if author is captain
        captain_role = ctx.guild.get_role(crew["captain_role"])
        if captain_role not in author.roles:
            await ctx.send("❌ Only the captain can demote vice-captains.")
            return
            
        # Check if target is in the same crew
        if member.id not in crew["members"]:
            await ctx.send(f"❌ {member.display_name} is not a member of your crew.")
            return
            
        # Check if target is a vice-captain
        vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])
        if vice_captain_role not in member.roles:
            await ctx.send(f"❌ {member.display_name} is not a vice-captain.")
            return
            
        # Demote from vice-captain
        try:
            await member.remove_roles(vice_captain_role)
            await ctx.send(f"✅ {member.display_name} has been demoted from vice-captain of `{author_crew}`.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles.")
            
    @crew_commands.command(name="transfer")
    async def crew_transfer(self, ctx, member: discord.Member):
        """Transfer crew captaincy to another member. Only the captain can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        author = ctx.author
        author_crew = None
        
        # Find the crew the command issuer is in
        for crew_name, crew in crews.items():
            if author.id in crew["members"]:
                author_crew = crew_name
                break
                
        if not author_crew:
            await ctx.send("❌ You are not in any crew.")
            return
            
        crew = crews[author_crew]
        
        # Check if author is captain
        captain_role = ctx.guild.get_role(crew["captain_role"])
        if captain_role not in author.roles:
            await ctx.send("❌ Only the captain can transfer captaincy.")
            return
            
        # Check if target is in the same crew
        if member.id not in crew["members"]:
            await ctx.send(f"❌ {member.display_name} is not a member of your crew.")
            return
            
        # Check if target is already the captain
        if captain_role in member.roles:
            await ctx.send(f"❌ {member.display_name} is already the captain.")
            return
            
        # Remove captain role from current captain
        try:
            await author.remove_roles(captain_role)
            
            # If the target was a vice-captain, remove that role
            vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])
            if vice_captain_role in member.roles:
                await member.remove_roles(vice_captain_role)
                
            # Add captain role to new captain
            await member.add_roles(captain_role)
            await ctx.send(f"✅ Captaincy of `{author_crew}` has been transferred from {author.display_name} to {member.display_name}.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles.")

    @crew_commands.command(name="stats")
    async def crew_stats(self, ctx, *, crew_name: str = None):
        """View crew statistics. If no crew is specified, shows stats for your crew."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        # If no crew specified, try to find the user's crew
        if crew_name is None:
            for name, crew in crews.items():
                if ctx.author.id in crew["members"]:
                    crew_name = name
                    break
                    
            if crew_name is None:
                await ctx.send("❌ You are not in any crew. Please specify a crew name.")
                return
                
        if crew_name not in crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return
            
        crew = crews[crew_name]
        stats = crew["stats"]
        
        # Calculate win rate
        total_battles = stats["wins"] + stats["losses"]
        win_rate = (stats["wins"] / total_battles * 100) if total_battles > 0 else 0
        
        embed = discord.Embed(
            title=f"{crew['emoji']} {crew_name} Statistics",
            color=0x00FF00,
        )
        
        embed.add_field(name="Battles", value=f"Wins: {stats['wins']}\nLosses: {stats['losses']}\nWin Rate: {win_rate:.1f}%", inline=False)
        embed.add_field(name="Tournaments", value=f"Participated: {stats['tournaments_participated']}\nWon: {stats['tournaments_won']}", inline=False)
        
        await ctx.send(embed=embed)

    async def update_crew_message(self, message, crew_name):
        """Update a crew message with current information."""
        try:
            guild = message.guild
            guild_id = str(guild.id)
            crews = self.crews.get(guild_id, {})
            
            if crew_name not in crews:
                return
                
            crew = crews[crew_name]
            
            # Get crew role
            crew_role = guild.get_role(crew["crew_role"])
            
            # Get members by role instead of stored IDs
            members = crew_role.members if crew_role else []
            
            captain_role = guild.get_role(crew["captain_role"])
            vice_captain_role = guild.get_role(crew["vice_captain_role"])
            
            # Look for captain and vice-captain across all guild members
            captain = next((m for m in guild.members if captain_role and captain_role in m.roles), None)
            vice_captain = next((m for m in guild.members if vice_captain_role and vice_captain_role in m.roles), None)
            
            regular_members = [m for m in members if m not in [captain, vice_captain]]
            
            embed = discord.Embed(
                title=f"Crew: {crew_name} {crew['emoji']}",
                description=f"Total Members: {len(members)}",
                color=0x00FF00,
            )
            
            embed.add_field(name="Captain", value=captain.mention if captain else "None", inline=False)
            embed.add_field(name="Vice Captain", value=vice_captain.mention if vice_captain else "None", inline=False)
            
            if regular_members:
                member_list = ", ".join([m.mention for m in regular_members[:10]])
                if len(regular_members) > 10:
                    member_list += f" and {len(regular_members) - 10} more..."
                embed.add_field(name="Members", value=member_list, inline=False)
            else:
                embed.add_field(name="Members", value="No regular members yet", inline=False)
                
            await message.edit(embed=embed)
        except discord.NotFound:
            pass  # Message was deleted
        except Exception as e:
            print(f"Error updating crew message: {e}")

    @commands.command(name="synccrew")
    @commands.admin_or_permissions(administrator=True)
    async def sync_crew(self, ctx, *, crew_name: str):
        """Sync the crew members list with the actual role members."""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if crew_name not in crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return
            
        crew = crews[crew_name]
        crew_role = ctx.guild.get_role(crew["crew_role"])
        
        if not crew_role:
            await ctx.send(f"❌ Could not find the crew role for `{crew_name}`.")
            return
            
        # Get all members with the crew role
        role_members = crew_role.members
        
        # Create a new members list from the role members
        new_members = [member.id for member in role_members]
        
        # Update the crew's members list
        old_count = len(crew["members"])
        crew["members"] = new_members
        new_count = len(new_members)
        
        await self.save_crews(ctx.guild)
        await ctx.send(f"✅ Crew `{crew_name}` members list synced with role members. Updated from {old_count} to {new_count} members.")

    @commands.command(name="syncallcrews")
    @commands.admin_or_permissions(administrator=True)
    async def sync_all_crews(self, ctx):
        """Sync all crews' members lists with their actual role members."""
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews found.")
            return
            
        results = []
        
        for crew_name, crew in crews.items():
            crew_role = ctx.guild.get_role(crew["crew_role"])
            
            if not crew_role:
                results.append(f"❌ `{crew_name}`: Could not find crew role")
                continue
                
            # Get all members with the crew role
            role_members = crew_role.members
            
            # Create a new members list from the role members
            new_members = [member.id for member in role_members]
            
            # Update the crew's members list
            old_count = len(crew["members"])
            crew["members"] = new_members
            new_count = len(new_members)
            
            results.append(f"✅ `{crew_name}`: Updated from {old_count} to {new_count} members")
            
        await self.save_crews(ctx.guild)
        
        # Send results in chunks if needed
        results_text = "\n".join(results)
        if len(results_text) > 1900:
            chunks = [results_text[i:i+1900] for i in range(0, len(results_text), 1900)]
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send(results_text)

    # --- Cog Setup ---
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Initialize data storage when bot joins a guild."""
        if guild.id not in self.crews:
            self.crews[str(guild.id)] = {}
            
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle members leaving the server."""
        guild = member.guild
        guild_id = str(guild.id)
        
        if guild_id not in self.crews:
            return
            
        for crew_name, crew in self.crews[guild_id].items():
            if member.id in crew["members"]:
                crew["members"].remove(member.id)
                await self.save_crews(guild)
                break

    @commands.command()
    async def crewtest(self, ctx):
        """Test if crew commands are working."""
        await ctx.send("Crew test command works!")

    @commands.command(name="importcrewjson")
    @commands.admin_or_permissions(administrator=True)
    async def import_crew_json(self, ctx):
        """
        Import crew data from an uploaded JSON file.
        
        Upload a JSON file with your message when using this command.
        The file should contain valid crew data in the format used by the bot.
        """
        # Check if a file was attached
        if not ctx.message.attachments:
            await ctx.send("❌ No file attached. Please upload a JSON file with your command.")
            return
            
        attachment = ctx.message.attachments[0]
        
        # Check if it's a JSON file
        if not attachment.filename.endswith('.json'):
            await ctx.send("❌ The attached file must be a JSON file (ending with .json).")
            return
            
        # Download the file
        try:
            json_content = await attachment.read()
            json_str = json_content.decode('utf-8')
            json_data = json.loads(json_str)
            
            # Check if the file has the expected top-level structure
            if "crews" not in json_data:
                await ctx.send("❌ Invalid crew data format. File should have a 'crews' key at the top level.")
                return
                
            # Extract actual crew data
            crew_data = json_data["crews"]
            
            # Get current guild ID
            guild_id = str(ctx.guild.id)
            
            # Confirm with user
            crew_count = len(crew_data)
            confirm_msg = await ctx.send(
                f"⚠️ This will import {crew_count} crews from the JSON file to this server. "
                f"Any existing crew data in this server will be overwritten. Are you sure? (yes/no)"
            )
            
            # Wait for confirmation
            try:
                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
                    
                msg = await self.bot.wait_for("message", check=check, timeout=30.0)
                
                if msg.content.lower() != "yes":
                    await ctx.send("❌ Import canceled.")
                    return
                    
            except asyncio.TimeoutError:
                await ctx.send("❌ Import timed out. Please try again.")
                return
            
            # Initialize guild namespace if needed
            if guild_id not in self.crews:
                self.crews[guild_id] = {}
            
            # Import the crew data
            self.crews[guild_id] = crew_data
            
            # Update guild setup status
            await self.config.guild(ctx.guild).finished_setup.set(True)
            
            # Save the data
            await self.save_data(ctx.guild)
            
            await ctx.send(f"✅ Successfully imported {crew_count} crews from the JSON file!")
            
            # Suggest next steps
            await ctx.send(
                "Note: The imported data includes role IDs, but you'll need to recreate these roles. "
                "Run `crewsetup roles` to create separator roles, then use `crew create` to recreate each crew."
            )
            
        except json.JSONDecodeError as e:
            await ctx.send(f"❌ Invalid JSON file: {str(e)}")
        except UnicodeDecodeError:
            await ctx.send("❌ Could not decode the file. Make sure it's a valid UTF-8 encoded JSON file.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred during import: {str(e)}")

    @commands.command(name="crews")
    async def list_crews_with_emojis(self, ctx):
        """Display all crews with their emojis and allow users to join by clicking the emoji reactions."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if not crews:
            await ctx.send("❌ No crews available. Ask an admin to create some with `crew create`.")
            return
    
        # Create an embed listing all crews
        embed = discord.Embed(
            title="🏴‍☠️ Available Crews 🏴‍☠️",
            description="React with the emoji below to join a crew!\n**Note:** You can only join one crew and cannot switch later.",
            color=discord.Color.gold()
        )
        
        # Add crew information to the embed
        for crew_name, crew_data in crews.items():
            emoji = crew_data.get("emoji", "🏴‍☠️")
            
            # Find the captain
            captain_role_id = crew_data.get("captain_role")
            crew_role_id = crew_data.get("crew_role")
            
            captain_role = ctx.guild.get_role(captain_role_id) if captain_role_id else None
            crew_role = ctx.guild.get_role(crew_role_id) if crew_role_id else None
            
            # Find captain and get member count
            captain = next((m for m in ctx.guild.members if captain_role and captain_role in m.roles), None)
            member_count = len(crew_role.members) if crew_role else 0
            
            embed.add_field(
                name=f"{emoji} {crew_name}",
                value=f"Captain: {captain.mention if captain else 'None'}\nMembers: {member_count}",
                inline=False
            )
        
        # Send the embed
        message = await ctx.send(embed=embed)
        
        # Add emoji reactions for each crew
        emoji_to_crew = {}
        for crew_name, crew_data in crews.items():
            emoji = crew_data.get("emoji", "🏴‍☠️")
            
            # Handle Discord custom emojis vs Unicode emojis
            if emoji.startswith('<:') or emoji.startswith('<a:'):
                # Extract emoji ID for custom emojis
                emoji_parts = emoji.split(':')
                if len(emoji_parts) >= 3:
                    emoji_id = emoji_parts[2][:-1]  # Remove the trailing '>'
                    emoji_obj = self.bot.get_emoji(int(emoji_id))
                    if emoji_obj:
                        await message.add_reaction(emoji_obj)
                        emoji_to_crew[str(emoji_obj)] = crew_name
                    else:
                        # Fallback to default emoji if custom emoji not found
                        await message.add_reaction("🏴‍☠️")
                        emoji_to_crew["🏴‍☠️"] = crew_name
            else:
                # Unicode emoji
                await message.add_reaction(emoji)
                emoji_to_crew[emoji] = crew_name
        
        # Store the message ID and emoji mapping for reaction handling
        self.active_crew_messages[message.id] = {
            "guild_id": guild_id,
            "emoji_to_crew": emoji_to_crew
        }
                
async def setup(bot):
    """Add the cog to the bot."""
    await bot.add_cog(CrewManagement(bot))
