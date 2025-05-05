"""Pokemon info commands for the Pokemon cog."""
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from ..utils.api import fetch_pokemon
from ..utils.formatters import create_pokemon_info_embed, format_pokemon_name, create_pokedex_embed

async def setup(bot: Red):
    """This is called when the cog is loaded via load_extension"""
    # This setup function is required for cogs in subdirectories
    pass

class InfoCommands:
    """Class to handle Pokemon information commands."""
    
    @commands.command(name="pinfo", aliases=["i"])
    async def pokemon_info(self, ctx: commands.Context, pokemon_id: int = None):
        """Get detailed information about a Pokemon."""
        user = ctx.author
        
        # If no Pokemon ID provided, use active Pokemon
        if pokemon_id is None:
            active_pokemon_id = await self.config.user(user).active_pokemon()
            if not active_pokemon_id:
                await ctx.send("You don't have an active Pokemon! Catch one first or specify a Pokemon ID.")
                return
            pokemon_id = int(active_pokemon_id)
        
        # Get user's Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        pokemon_id_str = str(pokemon_id)
        
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}! Use `{ctx.clean_prefix}pokemon list` to see your Pokemon.")
            return
        
        # Get Pokemon data
        user_pokemon_data = user_pokemon[pokemon_id_str]
        form_type = user_pokemon_data.get("form_type")
        
        pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id, form_type)
        
        if not pokemon_data:
            await ctx.send(f"Error fetching Pokemon data for #{pokemon_id}.")
            return
        
        # Create and send the info embed
        embed = create_pokemon_info_embed(pokemon_data, user_pokemon_data)
        await ctx.send(embed=embed)
    
    @commands.command(name="active", aliases=["setactive"])
    async def set_active(self, ctx: commands.Context, pokemon_id: int):
        """Set a Pokemon as your active Pokemon."""
        user = ctx.author
        user_pokemon = await self.config.user(user).pokemon()
        pokemon_id_str = str(pokemon_id)
        
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}! Use `{ctx.clean_prefix}pokemon list` to see your Pokemon.")
            return
        
        # Set as active
        await self.config.user(user).active_pokemon.set(pokemon_id_str)
        
        # Get proper display name
        form_type = user_pokemon[pokemon_id_str].get("form_type")
        pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id, form_type)
        
        if pokemon_data:
            display_name = format_pokemon_name(pokemon_data["name"], form_type)
        else:
            display_name = user_pokemon[pokemon_id_str]["name"].capitalize()
        
        await ctx.send(f"{display_name} is now your active Pokemon!")
    
    @commands.command(name="list", aliases=["l"])
    async def list_pokemon(self, ctx: commands.Context, user: discord.Member = None):
        """List all Pokemon in your collection."""
        if not user:
            user = ctx.author
        
        user_pokemon = await self.config.user(user).pokemon()
        active_pokemon_id = await self.config.user(user).active_pokemon()
        
        if not user_pokemon:
            await ctx.send(f"{user.name} doesn't have any Pokemon yet!")
            return
        
        # Sort Pokemon by ID
        sorted_pokemon = sorted(user_pokemon.items(), key=lambda x: int(x[0]))
        
        # Create embeds (paginated)
        embeds = []
        
        for i in range(0, len(sorted_pokemon), 10):
            chunk = sorted_pokemon[i:i+10]
            
            embed = discord.Embed(
                title=f"{user.name}'s Pokemon",
                description=f"Total: {len(user_pokemon)} Pokemon",
                color=0x3498db
            )
            
            for pokemon_id, pokemon_data in chunk:
                # Fetch API data for proper name display
                form_type = pokemon_data.get("form_type")
                api_data = await fetch_pokemon(self.session, self.config, int(pokemon_id), form_type)
                
                if api_data:
                    # Format name based on form type
                    display_name = format_pokemon_name(api_data["name"], form_type)
                else:
                    # Fallback if API data not available
                    display_name = pokemon_data["name"].capitalize()
                
                level = pokemon_data["level"]
                count = pokemon_data.get("count", 1)
                
                # Mark active Pokemon
                if pokemon_id == active_pokemon_id:
                    display_name = f"**{display_name} (Active)**"
                
                # Add field
                embed.add_field(
                    name=f"#{pokemon_id}: {display_name}",
                    value=f"Level: {level}\nCount: {count}",
                    inline=True
                )
            
            embeds.append(embed)
        
        # Send paginated embeds
        if embeds:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send(f"{user.name} doesn't have any Pokemon yet!")
    
    @commands.command(name="dex", aliases=["pokedex", "d"])
    async def pokedex(self, ctx: commands.Context, pokemon_id: int = None):
        """View Pokedex information about a Pokemon."""
        if pokemon_id is None:
            # Show user's Pokedex completion
            user_pokemon = await self.config.user(ctx.author).pokemon()
            
            # Count unique base Pokemon (ignore forms)
            unique_pokemon = set()
            for pokemon_id, pokemon_data in user_pokemon.items():
                # Extract base Pokemon ID
                if "-" in pokemon_data["name"]:
                    # This is a form, get the base Pokemon
                    if "base_pokemon" in pokemon_data:
                        unique_pokemon.add(pokemon_data["base_pokemon"])
                    else:
                        # Try to extract base ID from name
                        unique_pokemon.add(pokemon_id)
                else:
                    unique_pokemon.add(pokemon_id)
            
            total_caught = len(unique_pokemon)
            
            embed = discord.Embed(
                title=f"{ctx.author.name}'s Pokedex",
                description=f"You've caught {total_caught}/898 unique Pokemon ({total_caught/8.98:.1f}%)",
                color=0xff0000
            )
            
            await ctx.send(embed=embed)
            return
        
        # Show specific Pokemon info
        pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id)
        
        if not pokemon_data:
            await ctx.send(f"Pokemon #{pokemon_id} not found.")
            return
        
        # Check if user has caught this Pokemon
        user_pokemon = await self.config.user(ctx.author).pokemon()
        
        # Check both direct ID and any forms
        has_caught = str(pokemon_id) in user_pokemon
        
        # Also check for forms of this Pokemon
        if not has_caught:
            for pid, pdata in user_pokemon.items():
                if pdata.get("base_pokemon") == str(pokemon_id):
                    has_caught = True
                    break
        
        # Create and send the embed
        embed = create_pokedex_embed(pokemon_data, has_caught)
        await ctx.send(embed=embed)
        
    @commands.command(name="rename")
    async def rename_pokemon(self, ctx: commands.Context, pokemon_id: int, *, nickname: str):
        """Give a nickname to your Pokemon."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Check if nickname is too long
        if len(nickname) > 20:
            await ctx.send("Nickname must be 20 characters or less.")
            return
            
        async with self.config.user(user).pokemon() as user_pokemon:
            if pokemon_id_str not in user_pokemon:
                await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
                return
                
            # Get Pokemon data
            pokemon_data = user_pokemon[pokemon_id_str]
            form_type = pokemon_data.get("form_type")
            
            # Get API data for proper name display
            api_data = await fetch_pokemon(self.session, self.config, pokemon_id, form_type)
            
            # Format name for display
            if api_data:
                display_name = format_pokemon_name(api_data["name"], form_type)
            else:
                display_name = pokemon_data["name"].capitalize()
                
            # Set nickname
            user_pokemon[pokemon_id_str]["nickname"] = nickname
            
            await ctx.send(f"Your {display_name} is now known as \"{nickname}\"!")