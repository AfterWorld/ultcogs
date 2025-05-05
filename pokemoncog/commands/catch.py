"""Catch command for the Pokemon cog."""
import asyncio
import random
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

# Fix the import paths
from ..utils.formatting.spawn import is_correct_catch, add_pokemon_to_user
from ..utils.formatters import format_pokemon_name

async def setup(bot: Red):
    """This is called when the cog is loaded via load_extension"""
    # This setup function is required for cogs in subdirectories
    pass

class CatchCommands:
    """Class to handle Pokemon catching commands."""
    
    @commands.command(name="catch", aliases=["c"])
    async def catch_pokemon(self, ctx: commands.Context, *, pokemon_name: str):
        """Catch a wild Pokemon that has spawned."""
        # Shortcut access to bot and config
        bot = self.bot
        config = self.config
        
        # Check if there's an active spawn
        if ctx.guild.id not in self.spawns_active:
            await ctx.send("There's no wild Pokemon to catch right now!")
            return

        # Add lock to prevent race conditions
        if ctx.guild.id not in self.pokemon_locks:
            self.pokemon_locks[ctx.guild.id] = asyncio.Lock()

        async with self.pokemon_locks[ctx.guild.id]:
            # Check again inside the lock in case it was caught/fled while waiting
            if ctx.guild.id not in self.spawns_active:
                await ctx.send("There's no wild Pokemon to catch right now!")
                return

            spawn = self.spawns_active[ctx.guild.id]
            pokemon_data = spawn["pokemon"]

            # Check if the catch attempt is correct
            if is_correct_catch(pokemon_data, pokemon_name):
                # Caught!
                del self.spawns_active[ctx.guild.id]

                # Add to user's collection and get rewards
                result = await add_pokemon_to_user(self.session, config, ctx.author, pokemon_data)

                # Format display name properly
                display_name = format_pokemon_name(pokemon_data["name"], 
                                                  "-" in pokemon_data["name"] and pokemon_data["name"].split("-", 1)[1])

                # Create success embed
                embed = discord.Embed(
                    title=f"{ctx.author.name} caught a {display_name}!",
                    description=f"The Pokémon has been added to your collection.\nYou received ${result['money_reward']} for catching it!",
                    color=0x00ff00
                )
                embed.set_thumbnail(url=pokemon_data["sprite"])
                
                # Add special item info if one was found
                if "special_item" in result:
                    embed.add_field(
                        name="Special Item Found!",
                        value=f"You found a {result['special_item']} with the Pokemon!",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
            else:
                # Helper message for forms
                help_msg = ""
                if "-" in pokemon_data["name"]:
                    base_name, form = pokemon_data["name"].split("-", 1)
                    if form == "mega":
                        help_msg = f"\nHint: Try catching Mega {base_name.capitalize()}"
                    elif form.startswith("mega-"):
                        form_type = form.split("-")[1].upper()
                        help_msg = f"\nHint: Try catching Mega {base_name.capitalize()} {form_type}"
                    elif form == "gmax":
                        help_msg = f"\nHint: Try catching Gigantamax {base_name.capitalize()}"
                
                await ctx.send(f"That's not the right Pokemon name! Try again.{help_msg}")
