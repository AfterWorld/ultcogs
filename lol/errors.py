# lol/errors.py - Custom error handling
import logging
from typing import Optional

import discord
from redbot.core import commands

logger = logging.getLogger(__name__)

class LoLError(commands.CommandError):
    """Base exception for LoL cog errors"""
    pass

class APIError(LoLError):
    """Exception raised for API-related errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)

class RateLimitError(APIError):
    """Exception raised when rate limit is exceeded"""
    pass

class SummonerNotFoundError(LoLError):
    """Exception raised when summoner is not found"""
    pass

class InvalidRegionError(LoLError):
    """Exception raised for invalid region"""
    pass

class ErrorHandler:
    """Centralized error handling for the LoL cog"""
    
    @staticmethod
    async def handle_command_error(ctx: commands.Context, error: Exception):
        """Handle command errors with user-friendly messages"""
        
        # Don't handle if error is already handled
        if hasattr(ctx.command, 'on_error'):
            return
        
        # Get the original error if it's wrapped
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        
        # Create error embed
        embed = discord.Embed(color=0xFF0000, timestamp=ctx.message.created_at)
        
        if isinstance(error, commands.CommandOnCooldown):
            embed.title = "⏱️ Command on Cooldown"
            embed.description = f"Try again in {error.retry_after:.2f} seconds."
            
        elif isinstance(error, commands.MissingRequiredArgument):
            embed.title = "❓ Missing Argument"
            embed.description = f"Missing required argument: `{error.param.name}`"
            embed.add_field(
                name="Usage",
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
                inline=False
            )
            
        elif isinstance(error, commands.BadArgument):
            embed.title = "❌ Invalid Argument"
            embed.description = str(error)
            
        elif isinstance(error, commands.CheckFailure):
            embed.title = "🚫 Permission Denied"
            if isinstance(error, commands.MissingPermissions):
                embed.description = f"You need the following permissions: {', '.join(error.missing_permissions)}"
            elif isinstance(error, commands.NotOwner):
                embed.description = "This command is only available to the bot owner."
            else:
                embed.description = "You don't have permission to use this command."
                
        elif isinstance(error, APIError):
            embed.title = "🔧 API Error"
            embed.description = str(error)
            if error.status_code:
                embed.add_field(name="Status Code", value=error.status_code, inline=True)
                
        elif isinstance(error, SummonerNotFoundError):
            embed.title = "👤 Summoner Not Found"
            embed.description = str(error)
            embed.add_field(
                name="💡 Tip",
                value="Make sure to include the tag (e.g., `Faker#KR1`) and check the spelling!",
                inline=False
            )
            
        elif isinstance(error, InvalidRegionError):
            embed.title = "🌍 Invalid Region"
            embed.description = str(error)
            
        elif isinstance(error, RateLimitError):
            embed.title = "⏳ Rate Limited"
            embed.description = "Too many requests. Please wait a moment and try again."
            
        else:
            # Log unexpected errors
            logger.error(f"Unexpected error in {ctx.command}: {type(error).__name__}: {error}", exc_info=error)
            
            embed.title = "💥 Unexpected Error"
            embed.description = "An unexpected error occurred. The error has been logged."
            
            # Add error details for debugging (only for bot owner)
            if await ctx.bot.is_owner(ctx.author):
                embed.add_field(
                    name="Error Details",
                    value=f"```python\n{type(error).__name__}: {str(error)[:900]}```",
                    inline=False
                )
        
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            # Fallback to plain text if embed fails
            try:
                await ctx.send(f"❌ {embed.title}: {embed.description}")
            except discord.HTTPException:
                pass

class LoLErrorHandler:
    """Mixin class for error handling in commands"""
    
    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors that occur in cog commands"""
        await ErrorHandler.handle_command_error(ctx, error)