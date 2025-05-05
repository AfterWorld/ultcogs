"""Team management commands for the Pokemon cog."""
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from ..utils.api import fetch_pokemon
from ..utils.formatters import format_pokemon_name, create_team_embed

async def setup(bot: Red):
    """This is called when the cog is loaded via load_extension"""
    # This setup function is required for cogs in subdirectories
    pass

class TeamCommands:
    """Class to handle Pokemon team management commands."""
    
    @commands.group(name="team")
    async def pokemon_team(self, ctx: commands.Context):
        """Manage your Pokemon team."""
        if ctx.invoked_subcommand is None:
            # Display the user's current team
            return await self._show_team(ctx, ctx.author)
            
    @pokemon_team.command(name="add")
    async def team_add(self, ctx: commands.Context, pokemon_id: int):
        """Add a Pokemon to your team."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Get user's Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
            
        # Get user's team
        async with self.config.user(user).team() as team:
            # Initialize team if not already
            if team is None:
                team = []
                
            # Check if team is full
            if len(team) >= 6:
                await ctx.send("Your team is already full! Remove a Pokemon first.")
                return
                
            # Check if Pokemon is already in team
            if pokemon_id_str in team:
                await ctx.send(f"Pokemon #{pokemon_id} is already in your team!")
                return
                
            # Add to team
            team.append(pokemon_id_str)
            
            # Get Pokemon data
            pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id)
            pokemon_name = pokemon_data["name"].capitalize() if pokemon_data else f"Pokemon #{pokemon_id}"
            
            # Format display name
            form_type = user_pokemon[pokemon_id_str].get("form_type")
            display_name = format_pokemon_name(pokemon_data["name"], form_type) if pokemon_data else f"Pokemon #{pokemon_id}"
            
            await ctx.send(f"{display_name} has been added to your team!")
            
    @pokemon_team.command(name="remove")
    async def team_remove(self, ctx: commands.Context, pokemon_id: int):
        """Remove a Pokemon from your team."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Get user's team
        async with self.config.user(user).team() as team:
            # Initialize team if not already
            if team is None or not team:
                team = []
                await ctx.send("You don't have a team set up yet!")
                return
                
            # Check if Pokemon is in team
            if pokemon_id_str not in team:
                await ctx.send(f"Pokemon #{pokemon_id} is not in your team!")
                return
                
            # Remove from team
            team.remove(pokemon_id_str)
            
            # Get Pokemon data
            user_pokemon = await self.config.user(user).pokemon()
            if pokemon_id_str in user_pokemon:
                form_type = user_pokemon[pokemon_id_str].get("form_type")
                pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id)
                if pokemon_data:
                    display_name = format_pokemon_name(pokemon_data["name"], form_type)
                    await ctx.send(f"{display_name} has been removed from your team!")
                    return
            
            # Fallback if Pokemon data not found
            await ctx.send(f"Pokemon #{pokemon_id} has been removed from your team!")
            
    @pokemon_team.command(name="view")
    async def team_view(self, ctx: commands.Context, user: discord.Member = None):
        """View your or another user's Pokemon team."""
        await self._show_team(ctx, user or ctx.author)
    
    async def _show_team(self, ctx: commands.Context, user: discord.Member):
        """Helper method to show a user's team."""
        # Get user's team
        team = await self.config.user(user).team()

        # If the team is empty, fall back to the user's Pokemon collection
        if not team:
            user_pokemon = await self.config.user(user).pokemon()
            if not user_pokemon:
                await ctx.send(f"{user.name} doesn't have a team set up yet and hasn't caught any Pokémon!")
                return

            # Use the Pokémon collection as a fallback
            team = list(user_pokemon.keys())[:6]  # Limit to 6 Pokémon for display

        # Get Pokemon data for each team member
        team_data = []
        for pokemon_id in team:
            user_pokemon_data = await self.config.user(user).pokemon()
            
            if pokemon_id in user_pokemon_data:
                pokemon = user_pokemon_data[pokemon_id]
                form_type = pokemon.get("form_type")
                
                pokemon_data = await fetch_pokemon(self.session, self.config, int(pokemon_id), form_type)
                
                if pokemon_data:
                    # Add the Pokemon to team data
                    team_data.append({
                        "id": pokemon_id,
                        "name": pokemon_data["name"],
                        "sprite": pokemon_data["sprite"],
                        "types": pokemon_data["types"],
                        "level": pokemon.get("level", 1),
                        "nickname": pokemon.get("nickname"),
                        "form_type": form_type
                    })

        # Create and send the team embed
        if team_data:
            embed = create_team_embed(user, team_data)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{user.name} doesn't have any Pokémon in their team!")