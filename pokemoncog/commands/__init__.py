"""Command modules for the Pokemon cog."""
import discord
from redbot.core import commands
from redbot.core.bot import Red

from .catch import CatchCommands
from .settings import SettingsCommands
from .team import TeamCommands
from .info import InfoCommands
from .forms import FormCommands

async def setup(bot: Red):
    """Load command modules."""
    # This is a placeholder for future functionality
    # Could register global commands here if needed
    pass

def create_pokemon_help_embed(ctx):
    """Create a help embed for Pokemon commands."""
    embed = discord.Embed(
        title="Pokemon Commands",
        description="Use these commands to catch and train Pokemon!",
        color=0x3498db
    )
    
    embed.add_field(
        name="Getting Started",
        value=f"Use `{ctx.clean_prefix}pokemon settings channel #channel-name` to set where Pokemon will spawn.\n"
              f"Pokemon will randomly appear in that channel, and you can catch them with `{ctx.clean_prefix}p catch <pokemon-name>`.",
        inline=False
    )
    
    embed.add_field(
        name="Basic Commands",
        value=f"• `{ctx.clean_prefix}p catch <pokemon>` - Catch a spawned Pokemon\n"
              f"• `{ctx.clean_prefix}p list` - View your Pokemon collection\n"
              f"• `{ctx.clean_prefix}p info <id>` - View Pokemon details\n"
              f"• `{ctx.clean_prefix}p active <id>` - Set your active Pokemon",
        inline=False
    )
    
    embed.add_field(
        name="Team Management",
        value=f"• `{ctx.clean_prefix}p team` - View your team\n"
              f"• `{ctx.clean_prefix}p team add <id>` - Add a Pokemon to your team\n"
              f"• `{ctx.clean_prefix}p team remove <id>` - Remove a Pokemon from your team",
        inline=False
    )
    
    embed.add_field(
        name="Items & Shop",
        value=f"• `{ctx.clean_prefix}p shop` - Browse the shop\n"
              f"• `{ctx.clean_prefix}p buy <item>` - Buy an item\n"
              f"• `{ctx.clean_prefix}p items` - View your items\n"
              f"• `{ctx.clean_prefix}p use <item> <id>` - Use an item on a Pokemon",
        inline=False
    )
    
    embed.add_field(
        name="Special Forms",
        value=f"• `{ctx.clean_prefix}p forms <id>` - View available forms for a Pokemon\n"
              f"• `{ctx.clean_prefix}p mega <id>` - Mega evolve a Pokemon\n"
              f"• `{ctx.clean_prefix}p dynamax <id>` - Dynamax a Pokemon\n"
              f"• `{ctx.clean_prefix}p primal <id>` - Primal reversion for Kyogre/Groudon",
        inline=False
    )
    
    embed.add_field(
        name="Admin Settings",
        value=f"• `{ctx.clean_prefix}p settings channel` - Set spawn channel\n"
              f"• `{ctx.clean_prefix}p settings spawnrate` - Adjust spawn rate\n"
              f"• `{ctx.clean_prefix}p settings cooldown` - Set spawn cooldown\n"
              f"• `{ctx.clean_prefix}p settings forms` - Enable special forms",
        inline=False
    )
    
    return embed