"""Special form commands for the Pokemon cog."""
import asyncio
import random
import discord
from datetime import datetime
from typing import Dict, Optional, Any

from redbot.core import commands
from redbot.core.bot import Red

from ..utils.api import fetch_pokemon
from ..utils.formatters import format_pokemon_name
from ..constants import MEGA_STONES, PRIMAL_ORBS

async def setup(bot: Red):
    """This is called when the cog is loaded via load_extension"""
    # This setup function is required for cogs in subdirectories
    pass

class FormCommands:
    """Class to handle Pokemon special form commands."""
    
    @commands.command(name="mega")
    async def mega_evolve(self, ctx: commands.Context, pokemon_id: int):
        """Mega evolve a Pokemon using a Mega Stone."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Check if user has this Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
        
        # Get Pokemon data to check if it can mega evolve
        pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id)
        if not pokemon_data:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
            
        # Check if the Pokemon can mega evolve
        if not pokemon_data.get("mega_evolution", False):
            await ctx.send(f"{format_pokemon_name(pokemon_data['name'])} cannot Mega Evolve!")
            return
        
        # Find the correct mega stone for this Pokemon
        required_stone = None
        
        # Check for standard mega stones
        if pokemon_id in MEGA_STONES:
            required_stone = MEGA_STONES[pokemon_id]
        elif str(pokemon_id) in MEGA_STONES:
            required_stone = MEGA_STONES[str(pokemon_id)]
        
        # Check for X/Y variants
        if not required_stone:
            if (pokemon_id, "X") in MEGA_STONES:
                required_stone = MEGA_STONES[(pokemon_id, "X")]
            elif (pokemon_id, "Y") in MEGA_STONES:
                required_stone = MEGA_STONES[(pokemon_id, "Y")]
        
        if not required_stone:
            await ctx.send(f"Could not find a Mega Stone for {format_pokemon_name(pokemon_data['name'])}!")
            return
        
        # Check if user has the required stone
        user_items = await self.config.user(user).items()
        if required_stone not in user_items or user_items[required_stone] <= 0:
            await ctx.send(f"You need a {required_stone} to Mega Evolve {format_pokemon_name(pokemon_data['name'])}!")
            return
        
        # Determine the correct form (X/Y variants)
        form_key = "mega"
        
        # Special handling for Pokemon with multiple mega forms
        if pokemon_id in [6, 150]:  # Charizard, Mewtwo
            # Ask user which form they want to use
            if (pokemon_id, "X") in MEGA_STONES and (pokemon_id, "Y") in MEGA_STONES:
                embed = discord.Embed(
                    title="Mega Evolution",
                    description=f"Which Mega Evolution form would you like to use for {format_pokemon_name(pokemon_data['name'])}?",
                    color=0xff00ff
                )
                
                embed.add_field(
                    name="Option 1",
                    value=f"Mega {format_pokemon_name(pokemon_data['name'])} X",
                    inline=True
                )
                
                embed.add_field(
                    name="Option 2",
                    value=f"Mega {format_pokemon_name(pokemon_data['name'])} Y",
                    inline=True
                )
                
                embed.set_footer(text="Reply with 'X' or 'Y' to choose.")
                
                await ctx.send(embed=embed)
                
                try:
                    def check(message):
                        return message.author == ctx.author and message.channel == ctx.channel and message.content.upper() in ["X", "Y"]
                        
                    response = await self.bot.wait_for("message", check=check, timeout=30)
                    
                    form_key = f"mega-{response.content.lower()}"
                except asyncio.TimeoutError:
                    await ctx.send("You took too long to respond. Using the standard Mega Evolution form.")
        
        # Get the mega form data
        mega_data = await fetch_pokemon(self.session, self.config, pokemon_id, form_key)
        if not mega_data:
            await ctx.send("Error fetching Mega Evolution data. Please try again.")
            return
        
        # Create the temporary mega form
        async with self.config.user(user).pokemon() as user_pokemon_data:
            # Get base Pokemon data
            base_pokemon = user_pokemon_data[pokemon_id_str]
            
            # Create a temporary ID for the mega form
            mega_id = f"{pokemon_id}-mega"
            
            # Create the mega form
            user_pokemon_data[mega_id] = {
                "name": mega_data["name"],
                "level": base_pokemon["level"],
                "xp": base_pokemon["xp"],
                "caught_at": datetime.now().timestamp(),
                "count": 1,
                "form_type": form_key,
                "base_pokemon": pokemon_id_str,
                "temporary": True,  # Mark as temporary
                "expires_at": datetime.now().timestamp() + 3600  # 1 hour duration
            }
            
            # Set as active Pokemon
            await self.config.user(user).active_pokemon.set(mega_id)
        
        # Use up the mega stone
        async with self.config.user(user).items() as items:
            items[required_stone] -= 1
            if items[required_stone] <= 0:
                del items[required_stone]
        
        # Calculate stat changes
        stat_changes = []
        for stat_name, mega_val in mega_data["stats"].items():
            if stat_name in pokemon_data["stats"]:
                base_val = pokemon_data["stats"][stat_name]
                diff = mega_val - base_val
                if diff != 0:
                    stat_changes.append(f"{stat_name.capitalize()}: {base_val} → {mega_val} ({'+' if diff > 0 else ''}{diff})")
        
        # Create success embed
        embed = discord.Embed(
            title="Mega Evolution",
            description=f"Your {format_pokemon_name(pokemon_data['name'])} has Mega Evolved into {format_pokemon_name(mega_data['name'], form_key)}!",
            color=0xff00ff
        )
        
        if stat_changes:
            embed.add_field(
                name="Stat Changes",
                value="\n".join(stat_changes),
                inline=False
            )
        
        embed.add_field(
            name="Duration",
            value="Mega Evolution lasts for 1 hour, or until you switch to another Pokemon.",
            inline=False
        )
        
        # Set thumbnail
        embed.set_thumbnail(url=mega_data["sprite"])
        
        await ctx.send(embed=embed)
    
    @commands.command(name="primal")
    async def primal_reversion(self, ctx: commands.Context, pokemon_id: int):
        """Trigger Primal Reversion for Kyogre or Groudon."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Check if user has this Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
        
        # Check if this is Kyogre or Groudon
        if pokemon_id not in PRIMAL_ORBS and str(pokemon_id) not in PRIMAL_ORBS:
            await ctx.send("Only Kyogre and Groudon can undergo Primal Reversion!")
            return
        
        # Get the required orb
        required_orb = PRIMAL_ORBS.get(pokemon_id) or PRIMAL_ORBS.get(str(pokemon_id))
        
        # Check if user has the required orb
        user_items = await self.config.user(user).items()
        if required_orb not in user_items or user_items[required_orb] <= 0:
            await ctx.send(f"You need a {required_orb} to trigger Primal Reversion!")
            return
        
        # Get Pokemon data
        pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id)
        if not pokemon_data:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
        
        # Get primal form data
        primal_data = await fetch_pokemon(self.session, self.config, pokemon_id, "primal")
        if not primal_data:
            await ctx.send("Error fetching Primal Reversion data. Please try again.")
            return
        
        # Create the temporary primal form
        async with self.config.user(user).pokemon() as user_pokemon_data:
            # Get base Pokemon data
            base_pokemon = user_pokemon_data[pokemon_id_str]
            
            # Create a temporary ID for the primal form
            primal_id = f"{pokemon_id}-primal"
            
            # Create the primal form
            user_pokemon_data[primal_id] = {
                "name": primal_data["name"],
                "level": base_pokemon["level"],
                "xp": base_pokemon["xp"],
                "caught_at": datetime.now().timestamp(),
                "count": 1,
                "form_type": "primal",
                "base_pokemon": pokemon_id_str,
                "temporary": True,  # Mark as temporary
                "expires_at": datetime.now().timestamp() + 3600  # 1 hour duration
            }
            
            # Set as active Pokemon
            await self.config.user(user).active_pokemon.set(primal_id)
        
        # Use up the orb
        async with self.config.user(user).items() as items:
            items[required_orb] -= 1
            if items[required_orb] <= 0:
                del items[required_orb]
        
        # Calculate stat changes
        stat_changes = []
        for stat_name, primal_val in primal_data["stats"].items():
            if stat_name in pokemon_data["stats"]:
                base_val = pokemon_data["stats"][stat_name]
                diff = primal_val - base_val
                if diff != 0:
                    stat_changes.append(f"{stat_name.capitalize()}: {base_val} → {primal_val} ({'+' if diff > 0 else ''}{diff})")
        
        # Create success embed
        embed = discord.Embed(
            title="Primal Reversion",
            description=f"Your {format_pokemon_name(pokemon_data['name'])} has reverted to its ancient form: {format_pokemon_name(primal_data['name'], 'primal')}!",
            color=0xff0000
        )
        
        if stat_changes:
            embed.add_field(
                name="Stat Changes",
                value="\n".join(stat_changes),
                inline=False
            )
        
        embed.add_field(
            name="Duration",
            value="Primal Reversion lasts for 1 hour, or until you switch to another Pokemon.",
            inline=False
        )
        
        # Set thumbnail
        embed.set_thumbnail(url=primal_data["sprite"])
        
        await ctx.send(embed=embed)
    
    @commands.command(name="dynamax")
    async def dynamax_pokemon(self, ctx: commands.Context, pokemon_id: int):
        """Dynamax or Gigantamax a Pokemon."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Check if user has this Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
        
        # Check if user has a Dynamax Band
        user_items = await self.config.user(user).items()
        if "Dynamax Band" not in user_items or user_items["Dynamax Band"] <= 0:
            await ctx.send("You need a Dynamax Band to Dynamax or Gigantamax your Pokemon!")
            return
        
        # Get Pokemon data
        pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id)
        if not pokemon_data:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
        
        # Check if this Pokemon can Gigantamax
        can_gmax = pokemon_data.get("gigantamax", False)
        form_key = "gmax" if can_gmax else "dynamax"
        
        # Get special form data for Gigantamax
        gmax_data = None
        if can_gmax:
            gmax_data = await fetch_pokemon(self.session, self.config, pokemon_id, "gmax")
            if not gmax_data:
                # Fallback to regular Dynamax
                can_gmax = False
                form_key = "dynamax"
        
        # Create the temporary dynamax/gigantamax form
        async with self.config.user(user).pokemon() as user_pokemon_data:
            # Get base Pokemon data
            base_pokemon = user_pokemon_data[pokemon_id_str]
            
            # Create a temporary ID
            temp_id = f"{pokemon_id}-{form_key}"
            
            # Create the form with modified stats
            temp_form = {
                "name": f"{pokemon_data['name']}-{form_key}",
                "level": base_pokemon["level"],
                "xp": base_pokemon["xp"],
                "caught_at": datetime.now().timestamp(),
                "count": 1,
                "form_type": form_key,
                "base_pokemon": pokemon_id_str,
                "temporary": True,
                "expires_at": datetime.now().timestamp() + 1800,  # 30 minutes duration
                "stats": {}
            }
            
            # Double the HP and slightly increase other stats
            for stat_name, stat_value in pokemon_data["stats"].items():
                if stat_name == "hp":
                    temp_form["stats"][stat_name] = stat_value * 2
                else:
                    temp_form["stats"][stat_name] = int(stat_value * 1.5)
            
            # Add the temporary form
            user_pokemon_data[temp_id] = temp_form
            
            # Set as active Pokemon
            await self.config.user(user).active_pokemon.set(temp_id)
        
        # Use the dynamax band (it doesn't get consumed, just used)
        
        # Create success embed
        form_name = "Gigantamax" if can_gmax else "Dynamax"
        display_name = format_pokemon_name(pokemon_data["name"])
        
        embed = discord.Embed(
            title=f"{form_name} Form",
            description=f"Your {display_name} has {form_name}ed and grown to an enormous size!",
            color=0xff0000
        )
        
        # Add stat boosts
        embed.add_field(
            name="Stat Boosts",
            value="HP: ×2\nOther stats: ×1.5",
            inline=False
        )
        
        if can_gmax:
            embed.add_field(
                name="G-Max Move",
                value=f"Your {display_name} can now use special G-Max moves in battle!",
                inline=False
            )
        
        embed.add_field(
            name="Duration",
            value=f"{form_name} lasts for 30 minutes, or until you switch to another Pokemon.",
            inline=False
        )
        
        # Set thumbnail - use gmax sprite if available
        if can_gmax and gmax_data:
            embed.set_thumbnail(url=gmax_data["sprite"])
        else:
            embed.set_thumbnail(url=pokemon_data["sprite"])
        
        await ctx.send(embed=embed)
    
    @commands.command(name="forms", aliases=["f"])
    async def view_available_forms(self, ctx: commands.Context, pokemon_id: int):
        """View all available forms for a Pokemon."""
        # Get Pokemon data
        pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id)
        if not pokemon_data:
            await ctx.send(f"Pokemon #{pokemon_id} not found.")
            return
        
        # Check if user has this Pokemon (to determine what forms are available to them)
        user = ctx.author
        user_pokemon = await self.config.user(user).pokemon()
        has_pokemon = str(pokemon_id) in user_pokemon
        
        # Get potential form information
        forms = []
        
        # Check for mega evolution
        if pokemon_data.get("mega_evolution", False):
            # Find the mega stone
            mega_stone = None
            if pokemon_id in MEGA_STONES:
                mega_stone = MEGA_STONES[pokemon_id]
            elif str(pokemon_id) in MEGA_STONES:
                mega_stone = MEGA_STONES[str(pokemon_id)]
            elif (pokemon_id, "X") in MEGA_STONES:
                mega_stone = MEGA_STONES[(pokemon_id, "X")]
                forms.append({
                    "name": f"Mega {format_pokemon_name(pokemon_data['name'])} X",
                    "type": "mega-x",
                    "requirement": f"{MEGA_STONES[(pokemon_id, 'X')]}",
                    "available": has_pokemon and user.items.get(MEGA_STONES[(pokemon_id, "X")], 0) > 0
                })
                
                mega_stone = MEGA_STONES[(pokemon_id, "Y")]
                forms.append({
                    "name": f"Mega {format_pokemon_name(pokemon_data['name'])} Y",
                    "type": "mega-y",
                    "requirement": f"{MEGA_STONES[(pokemon_id, 'Y')]}",
                    "available": has_pokemon and user.items.get(MEGA_STONES[(pokemon_id, "Y")], 0) > 0
                })
            
            # If there's a standard mega evolution
            if mega_stone and not forms:
                forms.append({
                    "name": f"Mega {format_pokemon_name(pokemon_data['name'])}",
                    "type": "mega",
                    "requirement": mega_stone,
                    "available": has_pokemon and user.items.get(mega_stone, 0) > 0
                })
        
        # Check for primal reversion
        if pokemon_data.get("primal_reversion", False) or pokemon_id in PRIMAL_ORBS or str(pokemon_id) in PRIMAL_ORBS:
            primal_orb = PRIMAL_ORBS.get(pokemon_id) or PRIMAL_ORBS.get(str(pokemon_id))
            if primal_orb:
                forms.append({
                    "name": f"Primal {format_pokemon_name(pokemon_data['name'])}",
                    "type": "primal",
                    "requirement": primal_orb,
                    "available": has_pokemon and user.items.get(primal_orb, 0) > 0
                })
        
        # Check for Gigantamax
        if pokemon_data.get("gigantamax", False):
            forms.append({
                "name": f"Gigantamax {format_pokemon_name(pokemon_data['name'])}",
                "type": "gmax",
                "requirement": "Dynamax Band",
                "available": has_pokemon and user.items.get("Dynamax Band", 0) > 0
            })
        # All Pokemon can Dynamax
        elif has_pokemon:
            forms.append({
                "name": f"Dynamax {format_pokemon_name(pokemon_data['name'])}",
                "type": "dynamax",
                "requirement": "Dynamax Band",
                "available": user.items.get("Dynamax Band", 0) > 0
            })
        
        # Create embed
        embed = discord.Embed(
            title=f"Forms Available for {format_pokemon_name(pokemon_data['name'])}",
            color=0x9b59b6
        )
        
        embed.set_thumbnail(url=pokemon_data["sprite"])
        
        if not forms:
            embed.description = f"{format_pokemon_name(pokemon_data['name'])} doesn't have any special forms."
        else:
            for form in forms:
                status = "✅ Available" if form["available"] else "❌ Unavailable"
                embed.add_field(
                    name=form["name"],
                    value=f"Type: {form['type'].capitalize()}\nRequirement: {form['requirement']}\nStatus: {status}",
                    inline=False
                )
            
            # Add usage information
            commands_text = []
            if any(form["type"].startswith("mega") for form in forms):
                commands_text.append(f"`{ctx.clean_prefix}p mega {pokemon_id}`")
            if any(form["type"] == "primal" for form in forms):
                commands_text.append(f"`{ctx.clean_prefix}p primal {pokemon_id}`")
            if any(form["type"] in ["dynamax", "gmax"] for form in forms):
                commands_text.append(f"`{ctx.clean_prefix}p dynamax {pokemon_id}`")
            
            if commands_text:
                embed.add_field(
                    name="Usage",
                    value="Use the following commands to transform your Pokemon:\n" + "\n".join(commands_text),
                    inline=False
                )
        
        await ctx.send(embed=embed)