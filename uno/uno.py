"""
Minimal Uno Cog for testing Red-Discord bot compatibility
"""
import discord
from redbot.core import commands


class UnoCog(commands.Cog):
    """Minimal Uno cog for testing"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name="uno", invoke_without_command=True)
    async def uno_group(self, ctx):
        """Uno card game commands"""
        await ctx.send("Uno cog loaded successfully!")
    
    @uno_group.command(name="test")
    async def test_command(self, ctx):
        """Test command"""
        await ctx.send("✅ Uno cog is working!")


async def setup(bot):
    """Setup function for Red-Discord bot"""
    await bot.add_cog(UnoCog(bot))