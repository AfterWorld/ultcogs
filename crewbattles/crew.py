from redbot.core import commands, Config
from redbot.core.data_manager import cog_data_path
import pathlib
import discord
import random
import asyncio
import aiohttp
import json
import os

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


class JoinTournamentButton(discord.ui.Button):
    def __init__(self, tournament_name, cog):
        super().__init__(label="Join Tournament", style=discord.ButtonStyle.primary)
        self.tournament_name = tournament_name
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        tournament = self.cog.tournaments.get(self.tournament_name)
        
        if not tournament:
            await interaction.response.send_message("❌ This tournament no longer exists.", ephemeral=True)
            return

        if tournament["started"]:
            await interaction.response.send_message("❌ This tournament has already started.", ephemeral=True)
            return

        user_crew = None
        for crew_name, crew in self.cog.crews.items():
            if member.id in crew["members"]:
                user_crew = crew_name
                break

        if not user_crew:
            await interaction.response.send_message("❌ You are not in any crew. Join a crew first to participate in tournaments.", ephemeral=True)
            return

        if user_crew in tournament["crews"]:
            await interaction.response.send_message(f"❌ Your crew `{user_crew}` is already registered for this tournament.", ephemeral=True)
            return

        # Check if user is captain or vice captain of their crew
        crew = self.cog.crews[user_crew]
        captain_role = interaction.guild.get_role(crew["captain_role"])
        vice_captain_role = interaction.guild.get_role(crew["vice_captain_role"])
        
        if not (captain_role in member.roles or vice_captain_role in member.roles):
            await interaction.response.send_message("❌ Only the captain or vice captain can register a crew for tournaments.", ephemeral=True)
            return

        tournament["crews"].append(user_crew)
        await self.cog.save_tournaments(interaction.guild)
        await interaction.response.send_message(f"✅ Your crew `{user_crew}` has joined the tournament `{self.tournament_name}`!", ephemeral=True)
        await self.cog.update_tournament_message(interaction.message, self.tournament_name)


class StartTournamentButton(discord.ui.Button):
    def __init__(self, tournament_name, cog):
        super().__init__(label="Start Tournament", style=discord.ButtonStyle.success)
        self.tournament_name = tournament_name
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        tournament = self.cog.tournaments.get(self.tournament_name)
        
        if not tournament:
            await interaction.response.send_message("❌ This tournament no longer exists.", ephemeral=True)
            return

        if tournament["started"]:
            await interaction.response.send_message("❌ This tournament has already started.", ephemeral=True)
            return

        if tournament["creator"] != interaction.user.id:
            await interaction.response.send_message("❌ Only the creator of the tournament can start it.", ephemeral=True)
            return

        if len(tournament["crews"]) < 2:
            await interaction.response.send_message("❌ Tournament needs at least 2 crews to start.", ephemeral=True)
            return

        tournament["started"] = True
        await self.cog.save_tournaments(interaction.guild)
        await interaction.response.send_message(f"✅ Tournament `{self.tournament_name}` has started!", ephemeral=True)
        await self.cog.run_tournament(interaction.channel, self.tournament_name)


class TournamentView(discord.ui.View):
    def __init__(self, tournament_name, cog):
        super().__init__(timeout=None)
        self.add_item(JoinTournamentButton(tournament_name, cog))
        self.add_item(StartTournamentButton(tournament_name, cog))


# --- Main Cog ---
class CrewTournament(commands.Cog):
    """A cog for managing crews and tournaments in your server."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        # Default configuration
        default_guild = {
            "finished_setup": False,
            "separator_roles": None
        }
        
        self.config.register_guild(**default_guild)
        self.crews = {}
        self.tournaments = {}
        self.active_channels = set()
        
        # Define battle moves
        self.MOVES = [
            {"name": "Strike", "type": "regular", "description": "A basic attack", "effect": None},
            {"name": "Slash", "type": "regular", "description": "A quick sword slash", "effect": None},
            {"name": "Punch", "type": "regular", "description": "A direct hit", "effect": None},
            {"name": "Fireball", "type": "strong", "description": "A ball of fire", "effect": "burn", "burn_chance": 0.5},
            {"name": "Thunder Strike", "type": "strong", "description": "A bolt of lightning", "effect": "stun", "stun_chance": 0.3},
            {"name": "Heavy Blow", "type": "strong", "description": "A powerful attack", "effect": None},
            {"name": "Critical Smash", "type": "critical", "description": "A devastating attack", "effect": None},
            {"name": "Ultimate Strike", "type": "critical", "description": "An ultimate power move", "effect": None}
        ]
        
        # Task to load data on bot startup 
        self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        """Initialize the cog by loading data from all guilds."""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.load_data(guild)

    async def save_data(self, guild):
        """Save both crew and tournament data for a specific guild."""
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
                "crews": self.crews.get(str(guild.id), {}),
                "tournaments": self.tournaments.get(str(guild.id), {})
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"Saved crew data for guild {guild.name} ({guild.id}) to {file_path}")
        except Exception as e:
            print(f"Error saving crew data for guild {guild.name}: {e}")
    
    async def load_data(self, guild):
        """Load crew and tournament data for a specific guild."""
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
                    if str(guild.id) not in self.tournaments:
                        self.tournaments[str(guild.id)] = {}
                    
                    # Load the data into memory
                    self.crews[str(guild.id)] = data.get("crews", {})
                    self.tournaments[str(guild.id)] = data.get("tournaments", {})
                    
                    print(f"Loaded crew data for guild {guild.name} ({guild.id}) from {file_path}")
            else:
                print(f"No data file found for guild {guild.name} ({guild.id})")
                # Directory will be created in save_data if needed
        except Exception as e:
            print(f"Error loading crew data for guild {guild.name}: {e}")

    async def save_crews(self, guild):
        """Save only crew data for a specific guild."""
        await self.save_data(guild)

    async def save_tournaments(self, guild):
        """Save only tournament data for a specific guild."""
        await self.save_data(guild)

    def truncate_nickname(self, original_name, prefix):
        """Truncate a nickname to ensure it fits within Discord's 32 character limit when a prefix is added."""
        max_length = 32 - len(prefix) - 1  
        if len(original_name) > max_length:
            return original_name[:max_length-3] + "..." 
        return original_name

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

    def get_crew_for_guild(self, guild_id):
        """Get crews for a specific guild."""
        return self.crews.get(str(guild_id), {})

    def get_tournaments_for_guild(self, guild_id):
        """Get tournaments for a specific guild."""
        return self.tournaments.get(str(guild_id), {})
        
    def generate_health_bar(self, hp, max_hp=100, bar_length=10):
        """Generate a visual health bar."""
        filled_length = int(hp / max_hp * bar_length)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        return bar

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
        if guild_id not in self.tournaments:
            self.tournaments[guild_id] = {}
        
        # Create data directory if it doesn't exist
        data_path = cog_data_path(self)
        crews_dir = data_path / "Crews"
        if not os.path.exists(crews_dir):
            os.makedirs(crews_dir, exist_ok=True)
        
        await self.config.guild(ctx.guild).finished_setup.set(True)
        await self.save_data(ctx.guild)
        await ctx.send("✅ Crew system initialized for this server. You can now create crews and tournaments.")

    @crew_setup.command(name="reset")
    async def setup_reset(self, ctx):
        """Reset all crew and tournament data for this server."""
        guild_id = str(ctx.guild.id)
        
        # Clear data
        if guild_id in self.crews:
            self.crews[guild_id] = {}
        if guild_id in self.tournaments:
            self.tournaments[guild_id] = {}
        
        await self.save_data(ctx.guild)
        await ctx.send("✅ All crew and tournament data has been reset for this server.")

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
            captain = None
            for member_id in crew_data["members"]:
                member = ctx.guild.get_member(member_id)
                if member and captain_role in member.roles:
                    captain = member
                    break
            
            embed.add_field(
                name=f"{crew_data['emoji']} {crew_name}",
                value=f"Captain: {captain.mention if captain else 'None'}\nMembers: {len(crew_data['members'])}",
                inline=True
            )
        
        # Create a view with buttons for each crew
        view = discord.ui.View(timeout=None)
        for crew_name, crew_data in crews.items():
            view.add_item(CrewButton(crew_name, crew_data["emoji"], self))
        
        # Send the interactive message
        await ctx.send("✅ Crew setup has been finalized! Here are the available crews:", embed=embed, view=view)
        await ctx.send("Users can now join crews using the buttons above or by using the `crew join` command.")

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
        remaining = args_parts[2].strip()
        
        # Extract emoji and captain from remaining text
        remaining_parts = remaining.split()
        if not remaining_parts:
            await ctx.send("❌ Missing emoji. Example: `crew create \"The Shadow Armada\" 🏴‍☠️ @Captain`")
            return
        
        crew_emoji = remaining_parts[0]
        
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
        crews = self.crews.get(guild_id, {})
        
        if crew_name in crews:
            await ctx.send(f"❌ A crew with the name `{crew_name}` already exists.")
            return
    
        guild = ctx.guild
    
        # Check if the emoji is a custom emoji
        if crew_emoji.startswith("<:") and crew_emoji.endswith(">"):
            try:
                emoji_id = crew_emoji.split(":")[-1][:-1]
                emoji = self.bot.get_emoji(int(emoji_id))
                if not emoji:
                    # Fetch and upload the custom emoji to the guild
                    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                    crew_emoji = await self.fetch_custom_emoji(emoji_url, guild)
                else:
                    crew_emoji = str(emoji)
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
    
        # Initialize guild namespace if not exists
        if guild_id not in self.crews:
            self.crews[guild_id] = {}
            
        # Store crew data
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
                truncated_name = self.truncate_nickname(original_nick, crew_emoji)
                await captain.edit(nick=f"{crew_emoji} {truncated_name}")
        except discord.Forbidden:
            await ctx.send(f"⚠️ I couldn't update {captain.display_name}'s nickname due to permission issues, but the crew was created successfully.")
            
        await self.save_crews(ctx.guild)
        await ctx.send(f"✅ Crew `{crew_name}` created with {captain.mention} as captain!")

    @crew_commands.command(name="join")
    async def crew_join(self, ctx, crew_name: str):
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
    
        # Update nickname with crew emoji and truncation
        try:
            original_nick = member.display_name
            # Make sure we don't add the emoji twice
            if not original_nick.startswith(crew["emoji"]):
                truncated_name = self.truncate_nickname(original_nick, crew["emoji"])
                await member.edit(nick=f"{crew['emoji']} {truncated_name}")
        except discord.Forbidden:
            await ctx.send("⚠️ I don't have permission to change your nickname, but you've joined the crew.")
            
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
    async def crew_delete(self, ctx, crew_name: str):
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

        # Remove crew from tournaments
        tournaments = self.tournaments.get(guild_id, {})
        for tournament_name, tournament in tournaments.items():
            if crew_name in tournament["crews"]:
                tournament["crews"].remove(crew_name)

        # Delete crew
        del self.crews[guild_id][crew_name]
        await self.save_data(ctx.guild)
        await ctx.send(f"✅ Crew `{crew_name}` has been deleted.")

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
            captain_role = ctx.guild.get_role(crew_data["captain_role"])
            captain = None
            
            for member_id in crew_data["members"]:
                member = ctx.guild.get_member(member_id)
                if member and captain_role in member.roles:
                    captain = member
                    break
                    
            embed.add_field(
                name=f"{crew_data['emoji']} {crew_name}",
                value=f"Captain: {captain.mention if captain else 'None'}\nMembers: {len(crew_data['members'])}\nWins: {crew_data['stats']['wins']} | Losses: {crew_data['stats']['losses']}",
                inline=True
            )

        await ctx.send(embed=embed)

    @crew_commands.command(name="view")
    async def crew_view(self, ctx, crew_name: str):
        """View the details of a crew."""
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
        members = [ctx.guild.get_member(mid) for mid in crew["members"]]
        members = [m for m in members if m is not None]  # Filter out None values
        
        captain_role = ctx.guild.get_role(crew["captain_role"])
        vice_captain_role = ctx.guild.get_role(crew["vice_captain_role"])
        
        captain = next((m for m in members if captain_role in m.roles), None)
        vice_captain = next((m for m in members if vice_captain_role in m.roles), None)
        
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
            
        # Add statistics
        stats = crew["stats"]
        embed.add_field(
            name="Statistics",
            value=f"Wins: {stats['wins']}\nLosses: {stats['losses']}\nTournaments Won: {stats['tournaments_won']}\nTournaments Participated: {stats['tournaments_participated']}",
            inline=False
        )
        
        # Create a button to join this crew
        view = CrewView(crew_name, crew["emoji"], self)
        await ctx.send(embed=embed, view=view)

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

    @crew_commands.command(name="rename")
    @commands.admin_or_permissions(administrator=True)
    async def crew_rename(self, ctx, old_name: str, new_name: str):
        """Rename a crew. Only admins can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        crews = self.crews.get(guild_id, {})
        
        if old_name not in crews:
            await ctx.send(f"❌ No crew found with the name `{old_name}`.")
            return
            
        if new_name in crews:
            await ctx.send(f"❌ A crew with the name `{new_name}` already exists.")
            return
            
        # Get the crew and its emoji
        crew = crews[old_name]
        crew_emoji = crew["emoji"]
        
        # Update role names
        for role_key, role_suffix in [
            ("captain_role", "Captain"),
            ("vice_captain_role", "Vice Captain"),
            ("crew_role", "Member")
        ]:
            role = ctx.guild.get_role(crew[role_key])
            if role:
                try:
                    await role.edit(name=f"{crew_emoji} {new_name} {role_suffix}")
                except discord.Forbidden:
                    await ctx.send(f"⚠️ Couldn't rename {role.name} due to permission issues.")
                    
        # Update the crew name in any tournaments
        tournaments = self.tournaments.get(guild_id, {})
        for tournament in tournaments.values():
            if old_name in tournament["crews"]:
                tournament["crews"].remove(old_name)
                tournament["crews"].append(new_name)
                
        # Update the crew name in the crews dictionary
        crews[new_name] = crews.pop(old_name)
        crews[new_name]["name"] = new_name
        
        await self.save_data(ctx.guild)
        await ctx.send(f"✅ Crew `{old_name}` has been renamed to `{new_name}`.")

    @crew_commands.command(name="stats")
    async def crew_stats(self, ctx, crew_name: str = None):
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
            members = [guild.get_member(mid) for mid in crew["members"]]
            members = [m for m in members if m is not None]  # Filter out None values
            
            captain_role = guild.get_role(crew["captain_role"])
            vice_captain_role = guild.get_role(crew["vice_captain_role"])
            
            captain = next((m for m in members if captain_role in m.roles), None)
            vice_captain = next((m for m in members if vice_captain_role in m.roles), None)
            
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

    # --- Tournament Command Group ---
    @commands.group(name="tournament")
    @commands.guild_only()
    async def tournament_commands(self, ctx):
        """Commands for managing tournaments."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `help tournament` for more information.")

    @tournament_commands.command(name="create")
    @commands.admin_or_permissions(administrator=True)
    async def tournament_create(self, ctx, name: str):
        """Create a new tournament. Only admins can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if name in tournaments:
            await ctx.send(f"❌ A tournament with the name `{name}` already exists.")
            return
            
        # Initialize guild namespace if not exists
        if guild_id not in self.tournaments:
            self.tournaments[guild_id] = {}
            
        # Create tournament
        self.tournaments[guild_id][name] = {
            "name": name,
            "creator": ctx.author.id,
            "crews": [],
            "started": False,
            "created_at": ctx.message.created_at.isoformat()
        }
        
        await self.save_tournaments(ctx.guild)
        await self.send_tournament_message(ctx, name)

    @tournament_commands.command(name="delete")
    @commands.admin_or_permissions(administrator=True)
    async def tournament_delete(self, ctx, name: str):
        """Delete a tournament. Only admins can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if name not in tournaments:
            await ctx.send(f"❌ No tournament found with the name `{name}`.")
            return
            
        # Delete tournament
        del tournaments[name]
        await self.save_tournaments(ctx.guild)
        await ctx.send(f"✅ Tournament `{name}` has been deleted.")

    @tournament_commands.command(name="list")
    async def tournament_list(self, ctx):
        """List all available tournaments."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if not tournaments:
            await ctx.send("❌ No tournaments available. Ask an admin to create some with `tournament create`.")
            return
            
        embed = discord.Embed(
            title="Available Tournaments",
            description="Here's a list of all tournaments in this server.",
            color=0x00FF00,
        )
        
        for name, tournament in tournaments.items():
            creator = ctx.guild.get_member(tournament["creator"])
            status = "In Progress" if tournament["started"] else "Recruiting"
            
            embed.add_field(
                name=name,
                value=f"Creator: {creator.mention if creator else 'Unknown'}\nStatus: {status}\nCrews: {len(tournament['crews'])}",
                inline=True
            )
            
        await ctx.send(embed=embed)

    @tournament_commands.command(name="view")
    async def tournament_view(self, ctx, name: str):
        """View the details of a tournament."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if name not in tournaments:
            await ctx.send(f"❌ No tournament found with the name `{name}`.")
            return
            
        tournament = tournaments[name]
        creator = ctx.guild.get_member(tournament["creator"])
        
        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=f"Creator: {creator.mention if creator else 'Unknown'}\nStatus: {'In Progress' if tournament['started'] else 'Recruiting'}",
            color=0x00FF00,
        )
        
        # Add crew information
        crews_text = ""
        for crew_name in tournament["crews"]:
            crew = self.crews.get(guild_id, {}).get(crew_name)
            if crew:
                crews_text += f"• {crew['emoji']} {crew_name}\n"
                
        embed.add_field(
            name=f"Participating Crews ({len(tournament['crews'])})",
            value=crews_text if crews_text else "No crews yet",
            inline=False
        )
        
        # Show join buttons if tournament hasn't started
        if not tournament["started"]:
            view = TournamentView(name, self)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed)

    @tournament_commands.command(name="start")
    async def tournament_start(self, ctx, name: str):
        """Start a tournament. Only the creator or admins can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Crew system is not set up yet. Ask an admin to run `crewsetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if name not in tournaments:
            await ctx.send(f"❌ No tournament found with the name `{name}`.")
            return
            
        tournament = tournaments[name]
        
        # Check if user is the creator or an admin
        is_admin = await self.bot.is_admin(ctx.author)
        if tournament["creator"] != ctx.author.id and not is_admin:
            await ctx.send("❌ Only the creator or admins can start this tournament.")
            return
            
        if tournament["started"]:
            await ctx.send("❌ This tournament has already started.")
            return
            
        if len(tournament["crews"]) < 2:
            await ctx.send("❌ Tournament needs at least 2 crews to start.")
            return
            
        tournament["started"] = True
        await self.save_tournaments(ctx.guild)
        await ctx.send(f"✅ Tournament `{name}` has started!")
        await self.run_tournament(ctx.channel, name)

    async def send_tournament_message(self, ctx, name):
        """Send a message with tournament information and join buttons."""
        tournament = self.tournaments.get(str(ctx.guild.id), {}).get(name)
        if not tournament:
            return
            
        creator = ctx.guild.get_member(tournament["creator"])
        
        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=f"Creator: {creator.mention if creator else 'Unknown'}\nStatus: Recruiting",
            color=0x00FF00,
        )
        
        embed.add_field(
            name="Participating Crews (0)",
            value="Be the first to join!",
            inline=False
        )
        
        view = TournamentView(name, self)
        await ctx.send(embed=embed, view=view)

    async def update_tournament_message(self, message, name):
        """Update a tournament message with current information."""
        try:
            guild = message.guild
            guild_id = str(guild.id)
            tournaments = self.tournaments.get(guild_id, {})
            
            if name not in tournaments:
                return
                
            tournament = tournaments[name]
            creator = guild.get_member(tournament["creator"])
            
            embed = discord.Embed(
                title=f"Tournament: {name}",
                description=f"Creator: {creator.mention if creator else 'Unknown'}\nStatus: {'In Progress' if tournament['started'] else 'Recruiting'}",
                color=0x00FF00,
            )
            
            # Add crew information
            crews_text = ""
            for crew_name in tournament["crews"]:
                crew = self.crews.get(guild_id, {}).get(crew_name)
                if crew:
                    crews_text += f"• {crew['emoji']} {crew_name}\n"
                    
            embed.add_field(
                name=f"Participating Crews ({len(tournament['crews'])})",
                value=crews_text if crews_text else "No crews yet",
                inline=False
            )
            
            await message.edit(embed=embed)
        except discord.NotFound:
            pass  # Message was deleted
        except Exception as e:
            print(f"Error updating tournament message: {e}")

    async def run_tournament(self, channel, name):
        """Run the tournament matches."""
        if channel.id in self.active_channels:
            await channel.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")
            return
            
        # Mark channel as active
        self.active_channels.add(channel.id)
        
        try:
            guild = channel.guild
            guild_id = str(guild.id)
            tournaments = self.tournaments.get(guild_id, {})
            crews_dict = self.crews.get(guild_id, {})
            
            if name not in tournaments:
                await channel.send(f"❌ Tournament `{name}` not found.")
                self.active_channels.remove(channel.id)
                return
                
            tournament = tournaments[name]
            
            # Update tournament participation stats for all crews
            for crew_name in tournament["crews"]:
                if crew_name in crews_dict:
                    crews_dict[crew_name]["stats"]["tournaments_participated"] += 1
            
            # Get participating crews
            participating_crews = []
            for crew_name in tournament["crews"]:
                if crew_name in crews_dict:
                    participating_crews.append(crews_dict[crew_name])
            
            if len(participating_crews) < 2:
                await channel.send("❌ Not enough crews are participating in this tournament.")
                self.active_channels.remove(channel.id)
                return
                
            # Announce tournament start
            crew_mentions = [f"{crew['emoji']} **{crew['name']}**" for crew in participating_crews]
            await channel.send(
                f"🏆 **Tournament {name} has begun!**\n\n"
                f"Participating crews: {', '.join(crew_mentions)}\n\n"
                f"Let the battles begin!"
            )
            await asyncio.sleep(3)
            
            # Create tournament bracket
            random.shuffle(participating_crews)
            remaining_crews = participating_crews.copy()
            round_num = 1
            
            # Run tournament rounds until we have a winner
            while len(remaining_crews) > 1:
                await channel.send(f"🔄 **Round {round_num}**")
                await asyncio.sleep(2)
                
                next_round_crews = []
                
                # Create matches for this round
                matches = []
                for i in range(0, len(remaining_crews), 2):
                    if i + 1 < len(remaining_crews):
                        matches.append((remaining_crews[i], remaining_crews[i+1]))
                    else:
                        # Odd number of crews, one gets a bye
                        next_round_crews.append(remaining_crews[i])
                        await channel.send(f"🎟️ **{remaining_crews[i]['emoji']} {remaining_crews[i]['name']}** gets a bye to the next round!")
                
                # Run all matches for this round
                for match_num, (crew1, crew2) in enumerate(matches, 1):
                    await channel.send(f"⚔️ **Match {match_num}:** {crew1['emoji']} **{crew1['name']}** vs {crew2['emoji']} **{crew2['name']}**")
                    await asyncio.sleep(2)
                    
                    # Run the match
                    winner = await self.run_match(channel, crew1, crew2)
                    next_round_crews.append(winner)
                    
                    # Update crew stats
                    winner["stats"]["wins"] += 1
                    loser = crew1 if winner == crew2 else crew2
                    loser["stats"]["losses"] += 1
                    
                    await asyncio.sleep(2)
                
                # Prepare for next round
                remaining_crews = next_round_crews
                round_num += 1
                
                if len(remaining_crews) > 1:
                    await channel.send(f"🔄 **Round {round_num-1} complete!** {len(remaining_crews)} crews advancing to the next round.")
                    await asyncio.sleep(3)
            
            # We have a tournament winner
            winner = remaining_crews[0]
            winner["stats"]["tournaments_won"] += 1
            
            await channel.send(
                f"🎉 **TOURNAMENT WINNER: {winner['emoji']} {winner['name']}**\n\n"
                f"Congratulations to all participants! The tournament has concluded."
            )
            
            # Remove the tournament
            del tournaments[name]
            await self.save_data(guild)
            
        except Exception as e:
            await channel.send(f"❌ An error occurred during the tournament: {e}")
            print(f"Tournament error: {e}")
        finally:
            # Mark channel as inactive
            self.active_channels.remove(channel.id)

    async def run_match(self, channel, crew1, crew2):
        """Run a battle between two crews."""
        # Initialize crew data
        crew1_hp = 100
        crew2_hp = 100
        crew1_status = {"burn": 0, "stun": False}
        crew2_status = {"burn": 0, "stun": False}
        
        # Create the initial embed
        embed = discord.Embed(
            title="🏴‍☠️ Crew Battle ⚔️",
            description=f"Battle begins between **{crew1['emoji']} {crew1['name']}** and **{crew2['emoji']} {crew2['name']}**!",
            color=0x00FF00,
        )
        embed.add_field(
            name="Health Bars",
            value=(
                f"**{crew1['emoji']} {crew1['name']}:** {self.generate_health_bar(crew1_hp)} {crew1_hp}/100\n"
                f"**{crew2['emoji']} {crew2['name']}:** {self.generate_health_bar(crew2_hp)} {crew2_hp}/100"
            ),
            inline=False,
        )
        message = await channel.send(embed=embed)
        
        # Crew battle data
        crews = [
            {"name": crew1["name"], "emoji": crew1["emoji"], "hp": crew1_hp, "status": crew1_status, "data": crew1},
            {"name": crew2["name"], "emoji": crew2["emoji"], "hp": crew2_hp, "status": crew2_status, "data": crew2},
        ]
        turn_index = 0
        turn_count = 0
        
        # Battle loop
        while crews[0]["hp"] > 0 and crews[1]["hp"] > 0 and turn_count < 20:  # Cap at 20 turns to prevent infinite battles
            turn_count += 1
            attacker = crews[turn_index]
            defender = crews[1 - turn_index]
            
            # Apply burn damage at start of turn
            if defender["status"]["burn"] > 0:
                burn_damage = 5 * defender["status"]["burn"]
                defender["hp"] = max(0, defender["hp"] - burn_damage)
                defender["status"]["burn"] -= 1
                
                embed.description = f"🔥 **{defender['emoji']} {defender['name']}** takes {burn_damage} burn damage from fire stacks!"
                embed.set_field_at(
                    0,
                    name="Health Bars",
                    value=(
                        f"**{crews[0]['emoji']} {crews[0]['name']}:** {self.generate_health_bar(crews[0]['hp'])} {crews[0]['hp']}/100\n"
                        f"**{crews[1]['emoji']} {crews[1]['name']}:** {self.generate_health_bar(crews[1]['hp'])} {crews[1]['hp']}/100"
                    ),
                    inline=False,
                )
                await message.edit(embed=embed)
                await asyncio.sleep(2)
                
                # Check if defender died from burn
                if defender["hp"] <= 0:
                    break
            
            # Skip turn if stunned
            if attacker["status"]["stun"]:
                attacker["status"]["stun"] = False
                embed.description = f"⚡ **{attacker['emoji']} {attacker['name']}** is stunned and cannot act!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)
                turn_index = 1 - turn_index
                continue
            
            # Select a random move
            move = random.choice(self.MOVES)
            
            # Calculate damage
            damage = self.calculate_damage(move["type"])
            
            # Apply special effects
            effect_text = ""
            if move["effect"] == "burn" and random.random() < move.get("burn_chance", 0):
                defender["status"]["burn"] += 1
                effect_text = f"🔥 Setting {defender['emoji']} {defender['name']} on fire!"
            elif move["effect"] == "stun" and random.random() < move.get("stun_chance", 0):
                defender["status"]["stun"] = True
                effect_text = f"⚡ Stunning {defender['emoji']} {defender['name']}!"
                
            # Apply damage
            defender["hp"] = max(0, defender["hp"] - damage)
            
            # Update embed
            embed.description = (
                f"**{attacker['emoji']} {attacker['name']}** used **{move['name']}**: {move['description']} "
                f"and dealt **{damage}** damage to **{defender['emoji']} {defender['name']}**!"
            )
            
            if effect_text:
                embed.description += f"\n{effect_text}"
                
            embed.set_field_at(
                0,
                name="Health Bars",
                value=(
                    f"**{crews[0]['emoji']} {crews[0]['name']}:** {self.generate_health_bar(crews[0]['hp'])} {crews[0]['hp']}/100\n"
                    f"**{crews[1]['emoji']} {crews[1]['name']}:** {self.generate_health_bar(crews[1]['hp'])} {crews[1]['hp']}/100"
                ),
                inline=False,
            )
            
            await message.edit(embed=embed)
            await asyncio.sleep(2)
            
            # Switch turns
            turn_index = 1 - turn_index
        
        # Determine the winner
        winner = None
        if crews[0]["hp"] <= 0:
            winner = crews[1]["data"]
            embed.description = f"🏆 **{crews[1]['emoji']} {crews[1]['name']}** wins the battle!"
        elif crews[1]["hp"] <= 0:
            winner = crews[0]["data"]
            embed.description = f"🏆 **{crews[0]['emoji']} {crews[0]['name']}** wins the battle!"
        else:
            # If we hit the turn limit, the crew with more HP wins
            if crews[0]["hp"] > crews[1]["hp"]:
                winner = crews[0]["data"]
                embed.description = f"🏆 **{crews[0]['emoji']} {crews[0]['name']}** wins the battle by having more health!"
            elif crews[1]["hp"] > crews[0]["hp"]:
                winner = crews[1]["data"]
                embed.description = f"🏆 **{crews[1]['emoji']} {crews[1]['name']}** wins the battle by having more health!"
            else:
                # It's a tie, randomly select winner
                winner_index = random.randint(0, 1)
                winner = crews[winner_index]["data"]
                embed.description = f"It's a tie! 🎲 Random selection: **{crews[winner_index]['emoji']} {crews[winner_index]['name']}** wins!"
        
        await message.edit(embed=embed)
        return winner

    def calculate_damage(self, move_type):
        """Calculate damage based on move type."""
        if move_type == "regular":
            # Regular attacks: 5-10 damage
            return random.randint(5, 10)
        elif move_type == "strong":
            # Strong attacks: 10-15 damage
            return random.randint(10, 15)
        elif move_type == "critical":
            # Critical attacks: 15-25 damage with chance of critical hit
            damage = random.randint(15, 25)
            if random.random() < 0.2:  # 20% chance of critical hit
                damage *= 1.5  # Critical hit multiplier
                damage = int(damage)  # Convert to integer
            return damage
        else:
            return 0

    # --- Cog Setup ---
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Initialize data storage when bot joins a guild."""
        if guild.id not in self.crews:
            self.crews[str(guild.id)] = {}
        if guild.id not in self.tournaments:
            self.tournaments[str(guild.id)] = {}
            
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
                
def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(CrewTournament(bot))
