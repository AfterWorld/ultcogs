"""MrWhite's original commands, upgraded with three-role interactive gameplay."""
import asyncio
import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify

from .engine import RuleError, validate_word
from .session import Session, safe
from .rules import RulesView, rules_page
from .words import DEFAULT_PAIRS, DEFAULT_WORDS

TIMEOUTS = {"joining": 300, "playing": 120, "voting": 90, "guessing": 45}


class MrWhite(commands.Cog):
    """Secret Seas: Civilian, Undercover and Mr. White for 3–25 players."""

    def __init__(self, bot):
        self.bot = bot
        # Preserve the original identifier and legacy words key.
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_guild(words=DEFAULT_WORDS, pairs=DEFAULT_PAIRS, timeouts=TIMEOUTS)
        self.games: dict[int, Session] = {}
        self.lobby_lock = asyncio.Lock()

    async def cog_unload(self):
        sessions = list(self.games.values())
        for session in sessions:
            async with session.lock:
                session.close()
        tasks = [s.timer for s in sessions if s.timer]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for session in sessions:
            if session.message:
                try:
                    await session.io(session.message.edit(content="Voyage closed: cog unloaded.", view=None))
                except (discord.HTTPException, asyncio.TimeoutError):
                    pass

    async def red_delete_data_for_user(self, *, requester, user_id):
        for session in list(self.games.values()):
            async with session.lock:
                if user_id in session.game.players:
                    session.game.finish("Voyage closed for a player data-deletion request.")
                    session.close()
                    session.game.players.clear()
                    session.game.roles.clear()
                    session.game.clues.clear()
                    session.game.votes.clear()
                    if session.message:
                        try:
                            await session.io(session.message.edit(content="Voyage closed.", embed=None,
                                                                   attachments=[], view=None))
                        except (discord.HTTPException, asyncio.TimeoutError):
                            pass

    @commands.group(aliases=["mw"])
    @commands.guild_only()
    async def mrwhite(self, ctx):
        """Play Secret Seas. Start a lobby or read `mrwhite rules`."""

    @mrwhite.command(aliases=["new"])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def start(self, ctx):
        """Create a lobby and join as its captain."""
        async with self.lobby_lock:
            if ctx.channel.id in self.games:
                await ctx.send("A voyage is already running in this channel.")
                return
            settings = await self.config.guild(ctx.guild).all()
            session = Session(self, ctx, settings)
            self.games[ctx.channel.id] = session
        try:
            async with session.lock:
                await session.publish()
        except Exception:
            session.close()
            raise

    async def dispatch(self, ctx, action, value=None):
        session = self.games.get(ctx.channel.id)
        if not session:
            await ctx.send("No voyage here. Use `mrwhite start`.")
            return
        try:
            await session.act(ctx.author, action, value)
        except RuleError as exc:
            await ctx.send(str(exc), allowed_mentions=discord.AllowedMentions.none())
        except (discord.HTTPException, asyncio.TimeoutError):
            await ctx.send("Discord could not update the game. Start a new lobby.")

    @mrwhite.command(aliases=["j"])
    async def join(self, ctx):
        """Join the current lobby."""
        await self.dispatch(ctx, "join")

    @mrwhite.command()
    async def leave(self, ctx):
        """Leave the lobby (captains must transfer first)."""
        await self.dispatch(ctx, "leave")

    @mrwhite.command(aliases=["b"])
    async def begin(self, ctx):
        """Captain/moderator: begin with at least three players."""
        await self.dispatch(ctx, "begin")

    @mrwhite.command(aliases=["s"])
    async def say(self, ctx, *, word: str):
        """Submit exactly one single-word clue during the current round."""
        await self.dispatch(ctx, "say", word)

    @mrwhite.command()
    async def afk(self, ctx, enabled: bool):
        """Captain/moderator: set lobby AFK removal with `afk on` or `afk off`."""
        await self.dispatch(ctx, "afk", enabled)

    @mrwhite.command(aliases=["v"])
    async def vote(self, ctx, member: discord.Member):
        """Vote for a suspect. Use the select menu for a private ballot."""
        await self.dispatch(ctx, "vote", member.id)

    @mrwhite.command(aliases=["g"])
    async def guess(self, ctx, *, word: str):
        """Eliminated Mr. White: make your one final guess."""
        await self.dispatch(ctx, "guess", word)

    @mrwhite.command(aliases=["stop"])
    async def end(self, ctx):
        """Captain/moderator: close this voyage."""
        await self.dispatch(ctx, "end")

    @mrwhite.command()
    async def transfer(self, ctx, member: discord.Member):
        """Captain/moderator: transfer captaincy to a surviving player."""
        await self.dispatch(ctx, "transfer", member.id)

    @mrwhite.command()
    async def kick(self, ctx, member: discord.Member):
        """Captain/moderator: remove a player from the lobby."""
        await self.dispatch(ctx, "kick", member.id)

    @mrwhite.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def role(self, ctx):
        """DM your dossier; the private button also works with closed DMs."""
        session = self.games.get(ctx.channel.id)
        if not session:
            await ctx.send("No active voyage here.")
            return
        try:
            secret = await session.act(ctx.author, "role")
            await session.io(ctx.author.send(secret, allowed_mentions=discord.AllowedMentions.none()))
        except RuleError as exc:
            await ctx.send(str(exc))
        except (discord.HTTPException, asyncio.TimeoutError):
            await ctx.send("I could not DM you. Use **My secret dossier** on the game card for a private reply.")

    @mrwhite.command()
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def status(self, ctx):
        """Link to the current game card."""
        session = self.games.get(ctx.channel.id)
        if session and session.message:
            await ctx.send(session.message.jump_url)
        else:
            await ctx.send("No active voyage here.")

    @mrwhite.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def rules(self, ctx):
        """Open the field guide, with private buttons for detailed rules."""
        prefix = ctx.clean_prefix
        view = RulesView(prefix)
        try:
            view.message = await ctx.send(
                embed=rules_page("overview", prefix), view=view,
                allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            view.stop()
            raise

    @mrwhite.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def addword(self, ctx, *, word: str):
        """Preserve a legacy word, or add a playable `word | related word` pair."""
        if "|" in word:
            await self.edit_pair(ctx, word, remove=False)
            return
        try:
            word = validate_word(word)
        except RuleError as exc:
            await ctx.send(str(exc))
            return
        async with self.config.guild(ctx.guild).words() as words:
            if word in words:
                await ctx.send("That word is already in the legacy list.")
                return
            if len(words) >= 500:
                await ctx.send("Legacy list is full (500 words).")
                return
            words.append(word)
        await ctx.send("Legacy word saved. To use it in games, add a related pair with `mrwhite addpair word | related word`.")

    @mrwhite.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def removeword(self, ctx, *, word: str):
        """Remove a legacy single word. Playable pairs use `removepair`."""
        async with self.config.guild(ctx.guild).words() as words:
            matches = [w for w in words if w.casefold() == word.strip().casefold()]
            if not matches:
                await ctx.send("That word is not in the legacy list.")
                return
            words.remove(matches[0])
        await ctx.send("Legacy word removed.")

    async def edit_pair(self, ctx, text, remove):
        try:
            pair = [validate_word(w) for w in text.split("|")]
            if len(pair) != 2 or pair[0] == pair[1]:
                raise RuleError("Use two distinct related words separated by `|`.")
        except RuleError as exc:
            await ctx.send(str(exc))
            return
        async with self.config.guild(ctx.guild).pairs() as pairs:
            existing = next((p for p in pairs if set(p) == set(pair)), None)
            if remove:
                if existing is None:
                    await ctx.send("That pair is not configured.")
                    return
                pairs.remove(existing)
            else:
                if existing is not None:
                    await ctx.send("That pair is already configured.")
                    return
                if len(pairs) >= 500:
                    await ctx.send("Pair list is full (500 pairs).")
                    return
                pairs.append(pair)
        await ctx.send("Pair removed. Applies to new lobbies." if remove else "Pair saved. Applies to new lobbies.")

    @mrwhite.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def addpair(self, ctx, *, pair: str):
        """Add a related pair: `mrwhite addpair anchor | compass`."""
        await self.edit_pair(ctx, pair, remove=False)

    @mrwhite.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def removepair(self, ctx, *, pair: str):
        """Remove a related pair: `mrwhite removepair anchor | compass`."""
        await self.edit_pair(ctx, pair, remove=True)

    @mrwhite.command()
    @commands.cooldown(1, 15, commands.BucketType.channel)
    async def words(self, ctx, page: int = 1):
        """Show playable pairs and preserved legacy words, 15 entries per page."""
        settings = await self.config.guild(ctx.guild).all()
        entries = [f"Pair: {safe(a)} / {safe(b)}" for a,b in settings["pairs"]]
        entries += [f"Legacy (pair before play): {safe(w)}" for w in settings["words"]]
        pages = max(1, (len(entries)+14)//15)
        if not 1 <= page <= pages:
            await ctx.send(f"Choose a page from 1 to {pages}.")
            return
        body = "\n".join(entries[(page-1)*15:page*15]) or "No words configured."
        for chunk in pagify(body, page_length=1800):
            await ctx.send(f"**Words • {page}/{pages}**\n{chunk}", allowed_mentions=discord.AllowedMentions.none())

    @mrwhite.command(name="timeout")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_timeout(self, ctx, phase: str, seconds: int):
        """Set future lobby deadlines (30–900s): joining, playing, voting, guessing."""
        if phase not in TIMEOUTS or not 30 <= seconds <= 900:
            await ctx.send("Choose joining/playing/voting/guessing and 30–900 seconds.")
            return
        async with self.config.guild(ctx.guild).timeouts() as timeouts:
            timeouts[phase] = seconds
        await ctx.send("Deadline saved for new lobbies.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if session := self.games.get(channel.id):
            session.close()

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        if session := self.games.get(thread.id):
            session.close()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        for session in list(self.games.values()):
            if session.ctx.guild.id == guild.id:
                session.close()
