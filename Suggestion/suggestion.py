import discord
from redbot.core import commands, Config
from .views import SuggestionVotingView, SuggestionStaffView
from .utils import error_embed, make_embed
from .constants import DEFAULT_CONFIG, EMBED_COLOR_OK

class Suggestions(commands.Cog):
    """Suggestion system with voting."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6969696969, force_registration=True)
        self.config.register_guild(**DEFAULT_CONFIG)

    async def cog_load(self):
        self.bot.add_view(SuggestionVotingView(self, suggestion_id=0))
        self.bot.add_view(SuggestionStaffView(self, suggestion_id=0))

    @commands.guild_only()
    @commands.command(name="suggest")
    async def suggest(self, ctx: commands.Context, *, text: str):
        """Submit a suggestion."""
        settings = await self.config.guild(ctx.guild).all()
        channel_id = settings.get("suggestion_channel")
        if not channel_id:
            return await ctx.send(embed=error_embed("No suggestion channel set."))

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send(embed=error_embed("Configured suggestion channel not found."))

        embed = make_embed(
            title="💡 New Suggestion",
            description=text,
            color=EMBED_COLOR_OK
        )
        embed.set_footer(text="👍 0 | 👎 0")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        view = SuggestionVotingView(self, suggestion_id=123)  # Replace 123 with real ID logic
        await channel.send(embed=embed, view=view)
        await ctx.tick()
