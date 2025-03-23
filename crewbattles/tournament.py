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

# --- Helper Classes for UI Elements ---
class JoinTournamentButton(discord.ui.Button):
    def __init__(self, tournament_name, cog):
        super().__init__(label="Join Tournament", style=discord.ButtonStyle.primary)
        self.tournament_name = tournament_name
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild_id = str(interaction.guild_id)
        lock = self.cog.get_guild_lock(guild_id)
    
        async with lock:
            tournament = self.cog.tournaments.get(guild_id, {}).get(self.tournament_name)
        
        if not tournament:
            await interaction.response.send_message("❌ This tournament no longer exists.", ephemeral=True)
            return

        if tournament["started"]:
            await interaction.response.send_message("❌ This tournament has already started.", ephemeral=True)
            return

        user_crew = None
        # Get the crew manager instance
        crew_manager = self.cog.get_crew_manager()
        crews = crew_manager.get_crews_for_guild(guild_id)
        
        for crew_name, crew in crews.items():
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
        crew = crews[user_crew]
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
        guild_id = str(interaction.guild_id)  # Get guild ID from interaction
        tournament = self.cog.tournaments.get(guild_id, {}).get(self.tournament_name)  # Use guild_id namespace
        
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
class TournamentSystem(commands.Cog):
    """A cog for managing tournaments between crews in your server."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=8765432109, force_registration=True)
        
        # Default configuration
        default_guild = {
            "finished_setup": False
        }
        
        self.config.register_guild(**default_guild)
        self.tournaments = {}
        self.active_channels = set()
        self.guild_locks = {}  # Dict to store locks for each guild
        self._crew_manager = None  # Will be set when loaded
        
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
    
    def get_guild_lock(self, guild_id):
        """Get a lock for a specific guild, creating it if it doesn't exist."""
        if guild_id not in self.guild_locks:
            self.guild_locks[guild_id] = Lock()
        return self.guild_locks[guild_id]

    def set_crew_manager(self, crew_manager):
        """Set the crew manager reference."""
        self._crew_manager = crew_manager
        
    def get_crew_manager(self):
        """Get the crew manager reference."""
        return self._crew_manager

    async def initialize(self):
        """Initialize the cog by loading data from all guilds."""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.load_data(guild)

    async def save_data(self, guild):
        """Save tournament data for a specific guild."""
        finished_setup = await self.config.guild(guild).finished_setup()
        if not finished_setup:
            return
    
        # Use Red-Bot's data path structure
        data_path = cog_data_path(self)
        # Create 'Tournaments' directory if it doesn't exist
        tournaments_dir = data_path / "Tournaments"
        if not os.path.exists(tournaments_dir):
            os.makedirs(tournaments_dir, exist_ok=True)
        
        # Save to Tournaments.json in the proper directory
        file_path = tournaments_dir / f"{guild.id}.json"
        
        try:
            data = {
                "tournaments": self.tournaments.get(str(guild.id), {})
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"Saved tournament data for guild {guild.name} ({guild.id}) to {file_path}")
        except Exception as e:
            print(f"Error saving tournament data for guild {guild.name}: {e}")
    
    async def load_data(self, guild):
        """Load tournament data for a specific guild."""
        if not guild:
            return
    
        finished_setup = await self.config.guild(guild).finished_setup()
        if not finished_setup:
            return
    
        # Use Red-Bot's data path structure
        data_path = cog_data_path(self)
        tournaments_dir = data_path / "Tournaments"
        file_path = tournaments_dir / f"{guild.id}.json"
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Ensure guild has its own namespace in memory
                    if str(guild.id) not in self.tournaments:
                        self.tournaments[str(guild.id)] = {}
                    
                    # Load the data into memory
                    self.tournaments[str(guild.id)] = data.get("tournaments", {})
                    
                    print(f"Loaded tournament data for guild {guild.name} ({guild.id}) from {file_path}")
            else:
                print(f"No tournament data file found for guild {guild.name} ({guild.id})")
                # Directory will be created in save_data if needed
        except Exception as e:
            print(f"Error loading tournament data for guild {guild.name}: {e}")

    async def save_tournaments(self, guild):
        """Save tournament data for a specific guild with lock protection."""
        guild_id = str(guild.id)
        lock = self.get_guild_lock(guild_id)
        
        async with lock:
            await self.save_data(guild)
    
    def generate_health_bar(self, hp, max_hp=100, bar_length=10):
        """Generate a visual health bar."""
        filled_length = int(hp / max_hp * bar_length)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        return bar
        
    def log_message(self, level, message):
        """
        Log a message with the specified level.
        
        Parameters:
        level (str): The log level - "INFO", "WARNING", "ERROR"
        message (str): The message to log
        """
        # Format the log message with a timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] [TournamentSystem]: {message}"
        
        # Print to console
        print(formatted_message)
        
        # Additional logging to file if needed
        try:
            # Log to a file in the cog data directory
            data_path = cog_data_path(self)
            log_dir = data_path / "Logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            log_file = log_dir / "tournament.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{formatted_message}\n")
        except Exception as e:
            # Don't let logging errors disrupt the bot
            print(f"Error writing to log file: {e}")

    def get_tournaments_for_guild(self, guild_id):
        """Get tournaments for a specific guild."""
        return self.tournaments.get(str(guild_id), {})

    # --- Setup Command Group ---
    @commands.group(name="tournysetup")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def tournament_setup(self, ctx):
        """Commands for setting up the tournament system."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `help tournysetup` for more information.")

    @tournament_setup.command(name="init")
    async def setup_init(self, ctx):
        """Initialize the tournament system for this server."""
        guild_id = str(ctx.guild.id)
        
        # Initialize guild namespaces if they don't exist
        if guild_id not in self.tournaments:
            self.tournaments[guild_id] = {}
        
        # Create data directory if it doesn't exist
        data_path = cog_data_path(self)
        tournaments_dir = data_path / "Tournaments"
        if not os.path.exists(tournaments_dir):
            os.makedirs(tournaments_dir, exist_ok=True)
        
        await self.config.guild(ctx.guild).finished_setup.set(True)
        await self.save_data(ctx.guild)
        await ctx.send("✅ Tournament system initialized for this server. You can now create tournaments.")

    @tournament_setup.command(name="reset")
    async def setup_reset(self, ctx):
        """Reset all tournament data for this server."""
        guild_id = str(ctx.guild.id)
        
        # Clear data
        if guild_id in self.tournaments:
            self.tournaments[guild_id] = {}
        
        await self.save_data(ctx.guild)
        await ctx.send("✅ All tournament data has been reset for this server.")

    # --- Tournament Command Group ---
    @commands.group(name="tourny")
    @commands.guild_only()
    async def tournament_commands(self, ctx):
        """Commands for managing tournaments."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `help tourny` for more information.")

    @tournament_commands.command(name="create")
    @commands.admin_or_permissions(administrator=True)
    async def tournament_create(self, ctx, *, name: str):
        """Create a new tournament. Only admins can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if name in tournaments:
            await ctx.send(f"❌ A tournament with the name `{name}` already exists.")
            self.log_message("WARNING", f"Tournament creation failed: name '{name}' already exists in guild {guild_id}")
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
        self.log_message("INFO", f"Tournament '{name}' created in guild {guild_id} by user {ctx.author.id}")
        await self.send_tournament_message(ctx, name)

    @tournament_commands.command(name="delete")
    @commands.admin_or_permissions(administrator=True)
    async def tournament_delete(self, ctx, *, name: str):
        """Delete a tournament. Only admins can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
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
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if not tournaments:
            await ctx.send("❌ No tournaments available. Ask an admin to create some with `tourny create`.")
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
    async def tournament_view(self, ctx, *, name: str):
        """View the details of a tournament."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
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
        crew_manager = self.get_crew_manager()
        crews = crew_manager.get_crews_for_guild(guild_id)
        
        for crew_name in tournament["crews"]:
            crew = crews.get(crew_name)
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
    async def tournament_start(self, ctx, *, name: str):
        """Start a tournament. Only the creator or admins can use this command."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        lock = self.get_guild_lock(guild_id)
        
        started = False
        
        async with lock:
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
            
            # Mark as started inside the lock to prevent race conditions
            tournament["started"] = True
            started = True
            await self.save_tournaments(ctx.guild)
        
        # Only send the message and run the tournament if we successfully marked it as started
        if started:
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
            crew_manager = self.get_crew_manager()
            crews = crew_manager.get_crews_for_guild(guild_id)
            
            for crew_name in tournament["crews"]:
                crew = crews.get(crew_name)
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
        guild_id = str(channel.guild.id)
        
        if channel.id in self.active_channels:
            await channel.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")
            self.log_message("WARNING", f"Tournament run failed: channel {channel.id} already active in guild {guild_id}")
            return
            
        # Mark channel as active
        self.active_channels.add(channel.id)
        self.log_message("INFO", f"Starting tournament '{name}' in channel {channel.id} (guild {guild_id})")
        
        try:
            guild = channel.guild
            tournaments = self.tournaments.get(guild_id, {})
            
            if name not in tournaments:
                await channel.send(f"❌ Tournament `{name}` not found.")
                self.log_message("ERROR", f"Tournament '{name}' not found in guild {guild_id}")
                self.active_channels.remove(channel.id)
                return
                
            tournament = tournaments[name]
            
            # Get crew manager and crews
            crew_manager = self.get_crew_manager()
            crews_dict = crew_manager.get_crews_for_guild(guild_id)
            
            # Log participating crews
            participating_crew_names = tournament["crews"]
            self.log_message("INFO", f"Tournament '{name}' participating crews: {', '.join(participating_crew_names)}")
            
            # Update tournament participation stats for all crews
            for crew_name in tournament["crews"]:
                if crew_name in crews_dict:
                    # Get crew and update stats
                    if "stats" not in crews_dict[crew_name]:
                        crews_dict[crew_name]["stats"] = {
                            "wins": 0, 
                            "losses": 0,
                            "tournaments_won": 0,
                            "tournaments_participated": 0
                        }
                    
                    crews_dict[crew_name]["stats"]["tournaments_participated"] += 1
            
            # Get participating crews
            participating_crews = []
            for crew_name in tournament["crews"]:
                if crew_name in crews_dict:
                    participating_crews.append(crews_dict[crew_name])
            
            if len(participating_crews) < 2:
                await channel.send("❌ Not enough crews are participating in this tournament.")
                self.log_message("ERROR", f"Tournament '{name}' has fewer than 2 valid crews in guild {guild_id}")
                self.active_channels.remove(channel.id)
                return
                
            # Shuffle participating crews
            random.shuffle(participating_crews)
            
            # Send tournament start message
            crew_list = "\n".join([f"• {crew['emoji']} {crew['name']}" for crew in participating_crews])
            
            embed = discord.Embed(
                title=f"🏆 Tournament: {name} 🏆",
                description=f"The tournament has begun with {len(participating_crews)} crews!",
                color=0xFFD700,  # Gold color
            )
            
            embed.add_field(
                name="Participating Crews",
                value=crew_list,
                inline=False
            )
            
            await channel.send(embed=embed)
            await asyncio.sleep(2)
            
            # Run tournament rounds
            round_number = 1
            remaining_crews = participating_crews.copy()
            
            while len(remaining_crews) > 1:
                # Announce the round
                await channel.send(f"**Round {round_number}** of the tournament begins!")
                await asyncio.sleep(1)
                
                # Pair crews and run matches
                new_remaining_crews = []
                pairs = []
                
                # Create pairs
                for i in range(0, len(remaining_crews), 2):
                    if i + 1 < len(remaining_crews):
                        pairs.append((remaining_crews[i], remaining_crews[i+1]))
                    else:
                        # If odd number of crews, give a bye to the last crew
                        new_remaining_crews.append(remaining_crews[i])
                        await channel.send(f"{remaining_crews[i]['emoji']} **{remaining_crews[i]['name']}** advances to the next round with a bye!")
                
                # Run each match in the round
                for crew1, crew2 in pairs:
                    # Add a delay between matches
                    await asyncio.sleep(2)
                    
                    # Run the match
                    await channel.send(f"**Match:** {crew1['emoji']} {crew1['name']} vs {crew2['emoji']} {crew2['name']}")
                    winner = await self.run_match(channel, crew1, crew2)
                    
                    # Add winner to next round
                    new_remaining_crews.append(winner)
                    
                    # Update stats
                    loser = crew2 if winner == crew1 else crew1
                    winner["stats"]["wins"] += 1
                    loser["stats"]["losses"] += 1
                
                # Update remaining crews for next round
                remaining_crews = new_remaining_crews
                round_number += 1
                
                # If we have more than 1 crew remaining, announce the next round
                if len(remaining_crews) > 1:
                    next_round_crews = "\n".join([f"• {crew['emoji']} {crew['name']}" for crew in remaining_crews])
                    
                    next_round_embed = discord.Embed(
                        title=f"Round {round_number-1} Complete",
                        description=f"The following crews advance to Round {round_number}:",
                        color=0x00FF00,
                    )
                    
                    next_round_embed.add_field(
                        name="Advancing Crews",
                        value=next_round_crews,
                        inline=False
                    )
                    
                    await channel.send(embed=next_round_embed)
                    await asyncio.sleep(3)
            
            # We have a winner!
            winner = remaining_crews[0]
            
            # Update tournament win stats
            winner["stats"]["tournaments_won"] += 1
            
            # Final announcement
            final_embed = discord.Embed(
                title=f"🏆 Tournament Champion: {winner['name']} 🏆",
                description=f"{winner['emoji']} **{winner['name']}** has won the tournament!",
                color=0xFFD700,  # Gold color
            )
            
            # Show some stats
            final_embed.add_field(
                name="Champion Stats",
                value=f"Wins: {winner['stats']['wins']}\nLosses: {winner['stats']['losses']}\nTournaments Won: {winner['stats']['tournaments_won']}",
                inline=False
            )
            
            await channel.send(embed=final_embed)
            
            # Save updated crew statistics
            await crew_manager.save_crews(guild)
            
            # Remove the tournament from the list
            if name in tournaments:
                del tournaments[name]
                await self.save_tournaments(guild)
            
            self.log_message("INFO", f"Tournament '{name}' completed successfully in guild {guild_id}")
                
        except Exception as e:
            self.log_message("ERROR", f"Exception in tournament '{name}', guild {guild_id}: {str(e)}")
            await channel.send(f"❌ An error occurred during the tournament: {e}")
        finally:
            if channel.id in self.active_channels:
                self.active_channels.remove(channel.id)
                self.log_message("INFO", f"Channel {channel.id} removed from active channels (guild {guild_id})")
            else:
                self.log_message("WARNING", f"Channel {channel.id} not found in active_channels when trying to remove it")

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

    # --- Tournament Administration Commands ---
    @tournament_commands.command(name="add")
    @commands.admin_or_permissions(administrator=True)
    async def add_crew_to_tournament(self, ctx, tournament_name: str, *, crew_name: str):
        """Add a crew to a tournament. Admin only."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if tournament_name not in tournaments:
            await ctx.send(f"❌ No tournament found with the name `{tournament_name}`.")
            return
            
        tournament = tournaments[tournament_name]
        
        if tournament["started"]:
            await ctx.send("❌ This tournament has already started.")
            return
            
        # Get crew manager and crews
        crew_manager = self.get_crew_manager()
        crews = crew_manager.get_crews_for_guild(guild_id)
        
        if crew_name not in crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return
            
        if crew_name in tournament["crews"]:
            await ctx.send(f"❌ Crew `{crew_name}` is already in this tournament.")
            return
            
        # Add crew to tournament
        tournament["crews"].append(crew_name)
        await self.save_tournaments(ctx.guild)
        await ctx.send(f"✅ Crew `{crew_name}` has been added to tournament `{tournament_name}`.")

    @tournament_commands.command(name="remove")
    @commands.admin_or_permissions(administrator=True)
    async def remove_crew_from_tournament(self, ctx, tournament_name: str, *, crew_name: str):
        """Remove a crew from a tournament. Admin only."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if tournament_name not in tournaments:
            await ctx.send(f"❌ No tournament found with the name `{tournament_name}`.")
            return
            
        tournament = tournaments[tournament_name]
        
        if tournament["started"]:
            await ctx.send("❌ This tournament has already started.")
            return
            
        if crew_name not in tournament["crews"]:
            await ctx.send(f"❌ Crew `{crew_name}` is not in this tournament.")
            return
            
        # Remove crew from tournament
        tournament["crews"].remove(crew_name)
        await self.save_tournaments(ctx.guild)
        await ctx.send(f"✅ Crew `{crew_name}` has been removed from tournament `{tournament_name}`.")

    @tournament_commands.command(name="invite")
    @commands.admin_or_permissions(administrator=True)
    async def invite_all_crews(self, ctx, *, tournament_name: str):
        """Invite all crews to a tournament. Admin only."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        tournaments = self.tournaments.get(guild_id, {})
        
        if tournament_name not in tournaments:
            await ctx.send(f"❌ No tournament found with the name `{tournament_name}`.")
            return
            
        tournament = tournaments[tournament_name]
        
        if tournament["started"]:
            await ctx.send("❌ This tournament has already started.")
            return
            
        # Get crew manager and crews
        crew_manager = self.get_crew_manager()
        crews = crew_manager.get_crews_for_guild(guild_id)
        
        if not crews:
            await ctx.send("❌ No crews found to invite.")
            return
            
        # Track crews added
        crews_added = []
        
        # Add all crews that aren't already in the tournament
        for crew_name in crews.keys():
            if crew_name not in tournament["crews"]:
                tournament["crews"].append(crew_name)
                crews_added.append(crew_name)
                
        if not crews_added:
            await ctx.send("❌ All crews are already in this tournament.")
            return
            
        await self.save_tournaments(ctx.guild)
        await ctx.send(f"✅ Added {len(crews_added)} crews to tournament `{tournament_name}`:\n" + "\n".join([f"• `{name}`" for name in crews_added]))

    @tournament_commands.command(name="stats")
    async def tournament_stats(self, ctx, *, crew_name: str = None):
        """View tournament statistics for a crew. If no crew specified, shows overall stats."""
        # Validate setup
        finished_setup = await self.config.guild(ctx.guild).finished_setup()
        if not finished_setup:
            await ctx.send("❌ Tournament system is not set up yet. Ask an admin to run `tournysetup init` first.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Get crew manager and crews
        crew_manager = self.get_crew_manager()
        crews = crew_manager.get_crews_for_guild(guild_id)
        
        # If no crew specified, show overall stats
        if crew_name is None:
            # Try to find the user's crew
            user_crew = None
            for name, crew in crews.items():
                if ctx.author.id in crew["members"]:
                    user_crew = name
                    break
                    
            if user_crew:
                crew_name = user_crew
            else:
                # Show overall tournament stats
                tournaments = self.tournaments.get(guild_id, {})
                active_tournaments = [t for t in tournaments.values() if not t["started"]]
                in_progress_tournaments = [t for t in tournaments.values() if t["started"]]
                
                # Get crew statistics
                crew_stats = {}
                for crew_name, crew in crews.items():
                    if "stats" in crew and "tournaments_won" in crew["stats"]:
                        crew_stats[crew_name] = {
                            "tournaments_won": crew["stats"]["tournaments_won"],
                            "tournaments_participated": crew["stats"].get("tournaments_participated", 0)
                        }
                
                # Sort crews by tournaments won
                top_crews = sorted(crew_stats.items(), key=lambda x: x[1]["tournaments_won"], reverse=True)[:5]
                
                embed = discord.Embed(
                    title="🏆 Tournament Statistics",
                    description="Overall tournament statistics for this server.",
                    color=0xFFD700,
                )
                
                embed.add_field(
                    name="Tournament Status",
                    value=(
                        f"Active Tournaments: {len(active_tournaments)}\n"
                        f"In Progress: {len(in_progress_tournaments)}"
                    ),
                    inline=False
                )
                
                if top_crews:
                    top_crews_text = "\n".join([
                        f"• {crews[name]['emoji']} **{name}**: {stats['tournaments_won']} wins ({stats['tournaments_participated']} entries)"
                        for name, stats in top_crews
                    ])
                    
                    embed.add_field(
                        name="Top Tournament Winners",
                        value=top_crews_text,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Top Tournament Winners",
                        value="No tournament winners yet.",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                return
        
        # If crew name specified or user's crew found, show that crew's stats
        if crew_name not in crews:
            await ctx.send(f"❌ No crew found with the name `{crew_name}`.")
            return
            
        crew = crews[crew_name]
        
        if "stats" not in crew:
            crew["stats"] = {
                "wins": 0, 
                "losses": 0,
                "tournaments_won": 0,
                "tournaments_participated": 0
            }
            
        stats = crew["stats"]
        
        # Calculate win rate for matches
        match_win_rate = 0
        if stats["wins"] + stats["losses"] > 0:
            match_win_rate = (stats["wins"] / (stats["wins"] + stats["losses"])) * 100
            
        # Calculate win rate for tournaments
        tourny_win_rate = 0
        if stats.get("tournaments_participated", 0) > 0:
            tourny_win_rate = (stats.get("tournaments_won", 0) / stats.get("tournaments_participated", 0)) * 100
        
        embed = discord.Embed(
            title=f"{crew['emoji']} {crew_name} - Tournament Statistics",
            color=0xFFD700,
        )
        
        embed.add_field(
            name="Tournament Record",
            value=(
                f"🏆 **Tournaments Won:** {stats.get('tournaments_won', 0)}\n"
                f"🏟️ **Tournaments Entered:** {stats.get('tournaments_participated', 0)}\n"
                f"📊 **Tournament Win Rate:** {tourny_win_rate:.1f}%"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Match Record",
            value=(
                f"✅ **Wins:** {stats['wins']}\n"
                f"❌ **Losses:** {stats['losses']}\n"
                f"📊 **Win Rate:** {match_win_rate:.1f}%"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    # --- Cog Setup ---
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Initialize data storage when bot joins a guild."""
        if guild.id not in self.tournaments:
            self.tournaments[str(guild.id)] = {}

    @commands.command()
    async def tournamenttest(self, ctx):
        """Test if tournament commands are working."""
        await ctx.send("Tournament test command works!")

async def setup(bot):
     """Add the cog to the bot."""
     await bot.add_cog(TournamentSystem(bot))
