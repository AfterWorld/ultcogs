"""Serialize inputs and manage Discord messages and absolute deadlines."""
import asyncio
from io import BytesIO
import logging
import random
import time

import discord

from .engine import Game, RuleError, role_counts
from .graphics import render_banner
from .views import GameView

log = logging.getLogger("red.ultcogs.mrwhite")


def safe(text):
    return discord.utils.escape_markdown(discord.utils.escape_mentions(str(text)))


class Session:
    def __init__(self, cog, ctx, settings):
        self.cog, self.ctx, self.settings = cog, ctx, settings
        self.game = Game(ctx.author.id)
        self.game.join(ctx.author.id, ctx.author.display_name)
        self.lock = asyncio.Lock()
        self.message = None
        self.view = None
        self.timer = None
        self.deadline = 0
        self.armed_epoch = -1
        self.active = True

    async def io(self, awaitable):
        return await asyncio.wait_for(awaitable, timeout=15)

    def close(self):
        self.active = False
        if self.view:
            self.view.stop()
        if self.timer and self.timer is not asyncio.current_task():
            self.timer.cancel()
        if self.cog.games.get(self.ctx.channel.id) is self:
            self.cog.games.pop(self.ctx.channel.id, None)

    def arm(self):
        if self.armed_epoch == self.game.epoch:
            return
        if self.timer and self.timer is not asyncio.current_task():
            self.timer.cancel()
        self.armed_epoch = self.game.epoch
        seconds = self.settings["timeouts"][self.game.phase]
        self.deadline = time.time() + seconds
        self.timer = asyncio.create_task(self.wait_deadline(self.game.epoch, seconds),
                                         name=f"mrwhite:{self.ctx.channel.id}")

    async def wait_deadline(self, epoch, seconds):
        try:
            await asyncio.sleep(seconds)
            async with self.lock:
                if self.active and self.game.epoch == epoch:
                    self.game.expire()
                    await self.publish()
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("MrWhite deadline failed in channel %s", self.ctx.channel.id)
            self.close()

    def embed(self):
        g = self.game
        title = {"joining": "Secret Seas • Crew lobby", "playing": f"Round {g.round} • Clues",
                 "voting": f"Round {g.round} • {'Revote' if g.revote else 'Vote'}",
                 "guessing": "Mr. White • One last guess", "ended": "Voyage complete"}[g.phase]
        if g.phase == "joining":
            desc = ("Join a crew of **3–25**. Civilians share a word; Undercover gets a related word; "
                    "Mr. White gets no word. Give clues, vote, and expose the infiltrators.\n"
                    "Roles are private: use **My secret dossier** after departure.\n"
                    f"Captain: <@{g.host}> • Only the captain or a moderator can start/end.\n")
            if len(g.players) >= 3:
                c,u,w = role_counts(len(g.players))
                desc += f"Crew distribution: **{c} Civilian / {u} Undercover / {w} Mr. White**\n"
            desc += "\n" + "\n".join(f"• {safe(name)}" for name in g.players.values())
        elif g.phase == "ended":
            desc = g.result
            if g.roles:
                desc += f"\nCivilian word: **{safe(g.pair[0])}** • Undercover word: **{safe(g.pair[1])}**\n\n"
                desc += "\n".join(f"{safe(g.players[p])} — {r.value}" for p,r in g.roles.items())
        else:
            desc = f"Captain: <@{g.host}> • **{len(g.alive)}** crew remain.\n"
            if g.phase == "playing":
                desc += "Give one short clue. Do not reveal your word. Any order is allowed.\n\n"
                if g.round > 1:
                    desc += "Your secret word is unchanged; reopen your dossier if needed.\n"
            elif g.phase == "voting":
                desc += (f"**{len(g.votes)}/{len(g.alive)}** ballots received. You may change your ballot "
                         "until resolution. No self-votes.\n\n")
            else:
                desc += f"<@{g.guesser}>: guess the **Civilian** word once, before the deadline.\n\n"
        embed = discord.Embed(title=title, description=desc[:4000], color=0xE63649)
        if g.phase in ("playing", "voting"):
            lines = [f"**{safe(g.players[p][:24])}**: {safe(g.clues.get(p, '…'))}" for p in g.alive]
            chunk = ""
            for line in lines:
                if len(chunk) + len(line) + 1 > 1000:
                    embed.add_field(name="Crew clues", value=chunk, inline=False)
                    chunk = ""
                chunk += line + "\n"
            if chunk:
                embed.add_field(name="Crew clues", value=chunk, inline=False)
        if g.phase != "ended":
            embed.add_field(name="Deadline", value=f"<t:{int(self.deadline)}:R>")
        embed.set_footer(text="SECRET SEAS • Original art • Use mrwhite rules for win conditions")
        return embed

    async def publish(self):
        g = self.game
        if not self.active:
            return
        changed = self.armed_epoch != g.epoch
        if g.phase == "ended":
            self.close()
        else:
            self.arm()
        if self.view:
            self.view.stop()
        view = None if g.phase == "ended" else GameView(self)
        self.view = view
        events, g.events = g.events, []
        if events:
            await self.io(self.ctx.send("\n".join(events), allowed_mentions=discord.AllowedMentions.none()))
        embed = self.embed()
        if self.message is None or changed:
            if self.message:
                try:
                    await self.io(self.message.edit(view=None))
                except discord.NotFound:
                    pass
            kwargs = {}
            if self.ctx.channel.permissions_for(self.ctx.guild.me).attach_files:
                try:
                    artwork = await asyncio.to_thread(render_banner, g.phase)
                    kwargs["file"] = discord.File(BytesIO(artwork), filename="secret-seas.png")
                    embed.set_image(url="attachment://secret-seas.png")
                except Exception:
                    log.exception("MrWhite artwork failed; using text card")
            self.message = await self.io(self.ctx.send(embed=embed, view=view,
                          allowed_mentions=discord.AllowedMentions.none(), **kwargs))
        else:
            if self.message.attachments:
                embed.set_image(url="attachment://secret-seas.png")
            self.message = await self.io(self.message.edit(embed=embed, view=view,
                                        allowed_mentions=discord.AllowedMentions.none()))

    async def authorized_host(self, member):
        return (member.id == self.game.host or member.guild_permissions.manage_guild
                or await self.cog.bot.is_owner(member))

    async def act(self, member, action, value=None, epoch=None):
        async with self.lock:
            if not self.active or self.cog.games.get(self.ctx.channel.id) is not self:
                raise RuleError("This voyage has ended. Start a new lobby.")
            if epoch is not None and epoch != self.game.epoch:
                raise RuleError("This control has expired. Use the newest game card.")
            if member.bot:
                raise RuleError("Bots cannot join or control this game.")
            if self.deadline and time.time() >= self.deadline and action not in ("role", "end"):
                try:
                    self.game.expire()
                    await self.publish()
                except Exception:
                    self.close()
                    raise
                raise RuleError("The deadline passed. Use the current game card.")
            if action in ("begin", "end", "transfer", "kick") and not await self.authorized_host(member):
                raise RuleError("Only the captain or a server moderator can do that.")
            g = self.game
            if action == "role":
                return g.secret(member.id)
            if action == "join":
                g.join(member.id, member.display_name)
            elif action == "leave":
                g.leave(member.id)
            elif action == "begin":
                pairs = self.settings["pairs"]
                if not pairs:
                    raise RuleError("No word pairs configured. A moderator must add a pair first.")
                pair = list(random.SystemRandom().choice(pairs))
                random.SystemRandom().shuffle(pair)
                g.begin(tuple(pair))
            elif action == "say":
                g.say(member.id, value)
            elif action == "vote":
                g.vote(member.id, value)
            elif action == "guess":
                g.guess(member.id, value)
            elif action == "end":
                g.finish("Voyage ended by the captain or a moderator.")
            elif action == "transfer":
                g.require(value in g.alive, "The new captain must be a surviving crew member.")
                g.host = value
            elif action == "kick":
                g.require(g.phase == "joining", "Crew removal is only available in the lobby.")
                g.leave(value)
            else:
                raise RuleError("Unknown game action.")
            try:
                await self.publish()
            except Exception:
                self.close()
                raise
            return "Action recorded."

    async def interact(self, interaction, action, value=None, epoch=None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            if interaction.channel_id != self.ctx.channel.id:
                raise RuleError("Use the game controls in their original channel.")
            if (not await self.cog.bot.allowed_by_whitelist_blacklist(interaction.user)
                    or await self.cog.bot.cog_disabled_in_guild(self.cog, interaction.guild)):
                raise RuleError("MrWhite is unavailable to you here.")
            result = await self.act(interaction.user, action, value, epoch)
        except RuleError as exc:
            result = str(exc)
        except (discord.HTTPException, asyncio.TimeoutError):
            result = "Discord could not update the game. The session was closed; start a new lobby."
        except Exception:
            log.exception("MrWhite interaction failed")
            self.close()
            result = "The voyage could not continue and was closed. Please start a new lobby."
        await interaction.followup.send(result, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
