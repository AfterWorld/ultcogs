"""Settings commands for the Pokemon cog."""
import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
import asyncio

from ..constants import SPAWN_CHANCE, MIN_SPAWN_COOLDOWN

async def setup(bot: Red):
    """This is called when the cog is loaded via load_extension"""
    # This setup function is required for cogs in subdirectories
    pass

class SettingsCommands:
    """Class to handle Pokemon settings commands."""

    @commands.group(name="settings", aliases=["set"])
    @commands.admin_or_permissions(manage_channels=True)
    async def pokemon_settings(self, ctx: commands.Context):
        """Configure Pokemon cog settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            
    @pokemon_settings.command(name="channel")
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the channel where Pokemon will spawn."""
        if not channel:
            channel = ctx.channel
        
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Pokemon will now spawn in {channel.mention}!")
        
    @pokemon_settings.command(name="spawnrate")
    async def set_spawn_rate(self, ctx: commands.Context, rate: float):
        """Set the spawn rate (0.01 to 0.5, default is 0.1)."""
        if rate < 0.01 or rate > 0.5:
            await ctx.send("Spawn rate must be between 0.01 (1%) and 0.5 (50%).")
            return
            
        await self.config.guild(ctx.guild).spawn_chance.set(rate)
        percentage = rate * 100
        await ctx.send(f"Pokemon spawn rate set to {percentage:.1f}%.")
        
    @pokemon_settings.command(name="cooldown")
    async def set_cooldown(self, ctx: commands.Context, seconds: int):
        """Set the spawn cooldown in seconds (10 to 300, default is 60)."""
        if seconds < 10 or seconds > 300:
            await ctx.send("Cooldown must be between 10 and 300 seconds.")
            return
            
        await self.config.guild(ctx.guild).spawn_cooldown.set(seconds)
        await ctx.send(f"Pokemon spawn cooldown set to {seconds} seconds.")
        
    @pokemon_settings.command(name="forms")
    async def toggle_forms(self, ctx: commands.Context, form_type: str = None, enabled: bool = None):
        """Toggle special forms in spawns (mega, gmax, regional)."""
        valid_forms = ["mega", "gmax", "regional", "all"]
        
        if form_type not in valid_forms and form_type is not None:
            await ctx.send(f"Invalid form type! Choose from: {', '.join(valid_forms)}")
            return
        
        async with self.config.guild(ctx.guild).all() as guild_config:
            if form_type is None or enabled is None:
                # Show current settings
                mega_status = guild_config.get("include_mega", False)
                gmax_status = guild_config.get("include_gmax", False)
                forms_status = guild_config.get("include_forms", False)
                
                embed = discord.Embed(
                    title="Special Form Settings",
                    description="Current settings for special Pokemon forms spawns:",
                    color=0x3498db
                )
                
                embed.add_field(name="Mega Evolutions", value="✅ Enabled" if mega_status else "❌ Disabled", inline=True)
                embed.add_field(name="Gigantamax Forms", value="✅ Enabled" if gmax_status else "❌ Disabled", inline=True)
                embed.add_field(name="Regional Forms", value="✅ Enabled" if forms_status else "❌ Disabled", inline=True)
                
                await ctx.send(embed=embed)
                return
            
            # Update settings
            if form_type == "mega" or form_type == "all":
                guild_config["include_mega"] = enabled
            
            if form_type == "gmax" or form_type == "all":
                guild_config["include_gmax"] = enabled
            
            if form_type == "regional" or form_type == "all":
                guild_config["include_forms"] = enabled
            
            # Confirm changes
            status = "enabled" if enabled else "disabled"
            if form_type == "all":
                await ctx.send(f"All special forms have been {status}!")
            else:
                form_name = "Mega Evolutions" if form_type == "mega" else "Gigantamax Forms" if form_type == "gmax" else "Regional Forms"
                await ctx.send(f"{form_name} have been {status}!")
        
    @pokemon_settings.command(name="show")
    async def show_settings(self, ctx: commands.Context):
        """Show current Pokemon settings."""
        guild_config = await self.config.guild(ctx.guild).all()
        
        # Get channel mention if it exists
        channel_id = guild_config.get("channel")
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        channel_mention = channel.mention if channel else "Not set"
        
        # Create embed
        embed = discord.Embed(
            title=f"Pokemon Settings for {ctx.guild.name}",
            color=0x3498db
        )
        
        embed.add_field(
            name="Spawn Channel",
            value=channel_mention,
            inline=False
        )
        
        embed.add_field(
            name="Spawn Rate",
            value=f"{guild_config.get('spawn_chance', SPAWN_CHANCE) * 100:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="Spawn Cooldown",
            value=f"{guild_config.get('spawn_cooldown', MIN_SPAWN_COOLDOWN)} seconds",
            inline=True
        )
        
        # Special forms
        embed.add_field(
            name="Special Forms",
            value=f"Mega Evolutions: {'✅' if guild_config.get('include_mega', False) else '❌'}\n"
                  f"Gigantamax Forms: {'✅' if guild_config.get('include_gmax', False) else '❌'}\n"
                  f"Regional Forms: {'✅' if guild_config.get('include_forms', False) else '❌'}",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @pokemon_settings.command(name="reset")
    async def reset_settings(self, ctx: commands.Context):
        """Reset all Pokemon settings to default."""
        # Ask for confirmation
        confirm_msg = await ctx.send("Are you sure you want to reset all Pokemon settings to default? React with ✅ to confirm.")
        await confirm_msg.add_reaction("✅")
        
        try:
            def check(reaction, reactor):
                return (
                    reaction.message.id == confirm_msg.id
                    and reactor == ctx.author
                    and str(reaction.emoji) == "✅"
                )
                
            # Wait for confirmation (15 second timeout)
            await self.bot.wait_for("reaction_add", check=check, timeout=15)
            
            # Reset settings
            await self.config.guild(ctx.guild).channel.set(None)
            await self.config.guild(ctx.guild).spawn_chance.set(SPAWN_CHANCE)
            await self.config.guild(ctx.guild).spawn_cooldown.set(MIN_SPAWN_COOLDOWN)
            await self.config.guild(ctx.guild).include_mega.set(False)
            await self.config.guild(ctx.guild).include_gmax.set(False)
            await self.config.guild(ctx.guild).include_forms.set(False)
            
            await ctx.send("Pokemon settings have been reset to default values.")
        except asyncio.TimeoutError:
            await ctx.send("Reset settings confirmation timed out. No changes were made.")
            
    @pokemon_settings.command(name="clear_cache")
    @commands.is_owner()
    async def clear_cache(self, ctx: commands.Context):
        """Clear the Pokemon data cache (bot owner only)."""
        await self.config.pokemon_cache.clear()
        await self.config.form_cache.clear()
        await ctx.send("Pokemon data cache has been cleared.")