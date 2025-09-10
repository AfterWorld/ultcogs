import discord
import asyncio
import logging
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number, pagify
from redbot.core.i18n import Translator, cog_i18n

from .views import SuggestionVotingView, SuggestionStaffView
from .utils import create_status_embed, can_moderate_suggestions
from .constants import DEFAULT_GUILD_CONFIG, DEFAULT_USER_CONFIG, DEFAULT_COOLDOWN

log = logging.getLogger("red.suggestion")
_ = Translator("Suggestion", __file__)
cog_i18n(_)


class Suggestion(commands.Cog):
    """Modular Suggestion Box with voting, staff review, and logging."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9258471035622, force_registration=True)
        self.config.register_guild(**DEFAULT_GUILD_CONFIG)
        self.config.register_user(**DEFAULT_USER_CONFIG)
        self.cache = {}  # guild_id -> config
        self.cooldowns = {}

        # Register persistent views on restart
        self.bot.add_view(SuggestionVotingView(self, 0))
        self.bot.add_view(SuggestionStaffView(self, 0))

    async def cog_load(self):
        await self._load_views()

    async def _load_views(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            conf = await self.get_guild_config(guild)
            for sid, data in conf.get("suggestions", {}).items():
                if data["status"] == "pending":
                    view = SuggestionVotingView(self, int(sid))
                    votes = data.get("votes", {"upvotes": [], "downvotes": []})
                    view.update_vote_counts(len(votes["upvotes"]), len(votes["downvotes"]))
                    self.bot.add_view(view)

                elif data.get("staff_message_id"):
                    self.bot.add_view(SuggestionStaffView(self, int(sid)))

    async def get_guild_config(self, guild: discord.Guild) -> dict:
        if guild.id in self.cache:
            return self.cache[guild.id]
        conf = await self.config.guild(guild).all()
        self.cache[guild.id] = conf
        return conf

    async def update_guild_config(self, guild: discord.Guild, **kwargs):
        for k, v in kwargs.items():
            await self.config.guild(guild).set_raw(k, value=v)
        self.cache.pop(guild.id, None)

    @commands.command()
    @commands.guild_only()
    async def suggest(self, ctx: commands.Context, *, text: str):
        """Submit a suggestion to the suggestion channel."""

        guild = ctx.guild
        conf = await self.get_guild_config(guild)

        if conf["suggestion_channel"] is None:
            return await ctx.send("Suggestions are not set up yet.")

        # Cooldown check
        cd = conf.get("cooldown", DEFAULT_COOLDOWN)
        last_time = self.cooldowns.get(ctx.author.id, 0)
        now = discord.utils.utcnow().timestamp()
        if now - last_time < cd:
            left = int(cd - (now - last_time))
            return await ctx.send(f"⏳ You're on cooldown for {left}s.")
        self.cooldowns[ctx.author.id] = now

        # Validate length
        if len(text) < conf["min_length"]:
            return await ctx.send(f"❌ Suggestion too short ({len(text)} chars).")
        if len(text) > conf["max_length"]:
            return await ctx.send(f"❌ Suggestion too long ({len(text)} chars).")

        sid = conf["suggestion_count"] + 1
        embed = discord.Embed(
            title=f"Suggestion #{sid}",
            description=text,
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )

        if not conf.get("anonymous_suggestions", False):
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text=f"ID: {ctx.author.id}")
        else:
            embed.set_footer(text="Anonymous")

        embed.add_field(name="Votes", value="👍 0 | 👎 0", inline=True)

        suggestion_channel = guild.get_channel(conf["suggestion_channel"])
        if not suggestion_channel:
            return await ctx.send("Configured suggestion channel no longer exists.")

        view = SuggestionVotingView(self, sid)
        view.update_vote_counts(0, 0)
        msg = await suggestion_channel.send(embed=embed, view=view)

        # Save
        suggestion_data = {
            "id": sid,
            "author_id": ctx.author.id,
            "content": text,
            "channel_id": suggestion_channel.id,
            "message_id": msg.id,
            "status": "pending",
            "created_at": now,
            "votes": {"upvotes": [], "downvotes": []},
            "staff_message_id": None,
        }

        async with self.config.guild(guild).suggestions() as suggestions:
            suggestions[str(sid)] = suggestion_data
        await self.config.guild(guild).suggestion_count.set(sid)

        await ctx.send("✅ Suggestion posted!")

    async def _update_suggestion_status(
        self,
        ctx: commands.Context,
        suggestion_id: int,
        status: str,
        reason: str = None,
        interaction: discord.Interaction = None,
    ):
        guild = ctx.guild
        conf = await self.get_guild_config(guild)
        sid = str(suggestion_id)

        suggestions = conf.get("suggestions", {})
        data = suggestions.get(sid)
        if not data:
            return await ctx.send("❌ Suggestion not found.")

        data["status"] = status
        data["moderator_id"] = ctx.author.id
        data["updated_at"] = discord.utils.utcnow().timestamp()
        if reason:
            data["reason"] = reason

        author = guild.get_member(data["author_id"])
        channel = guild.get_channel(data["channel_id"])

        embed = create_status_embed(suggestion_id, data["content"], status, ctx.author, reason, author)

        try:
            message = await channel.fetch_message(data["message_id"])
            await message.edit(embed=embed, view=None)

            if status == "denied" and conf.get("auto_delete_denied", False):
                await asyncio.sleep(10)
                await message.delete()
        except Exception:
            log.warning(f"Could not edit/delete suggestion message {data['message_id']}")

        await self.config.guild(guild).suggestions.set(suggestions)

        # DM notification
        if author and conf.get("dm_notifications", True):
            try:
                await author.send(embed=embed)
            except Exception:
                pass

        await ctx.send(f"✅ Suggestion #{suggestion_id} marked **{status}**.")
