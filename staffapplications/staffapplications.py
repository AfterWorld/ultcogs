"""Staff recruitment for Red, with durable delivery and scoped error reporting."""

import asyncio
import io
import logging
import time
from datetime import datetime, timezone
from weakref import WeakValueDictionary

import discord
from redbot.core import commands
from redbot.core.data_manager import cog_data_path

from .alerts import Alerts
from .presets import ONE_PIECE_TEMPLATE
from .store import PanelUnavailable, Store, UserError
from .views import (
    NONE,
    AnswerModal,
    AnswerPages,
    CancelView,
    DecisionModal,
    DraftView,
    EditView,
    PositionView,
    ReviewView,
    panel,
    reply,
)

log = logging.getLogger("red.staffapplications")


def transcript(app):
    lines = [
        f"Staff application {app['id']}",
        f"Applicant ID: {app['user']}",
        f"Position: {app['position']}",
        "",
    ]
    for n, (question, answer) in enumerate(zip(app["questions"], app["answers"]), 1):
        lines.extend([f"{n}. {question}", answer or "(not answered)", ""])
    return discord.File(
        io.BytesIO("\n".join(lines).encode("utf-8")), filename=f"application-{app['id']}.txt"
    )


def draft_embed(app):
    count = sum(bool(a) for a in app["answers"])
    next_index = next((i for i, a in enumerate(app["answers"]) if not a), None)
    text = (
        f"**Position:** {app['position']}\n**Progress:** {count}/{len(app['questions'])} answers saved\n\n"
        "Answers are saved when you submit each form. You can return using My Application in the server.\n"
        "Your answers will be shared with authorized reviewers and bot operators when you submit."
    )
    if next_index is not None:
        text += f"\n\n**Next question:**\n{app['questions'][next_index]}"
    else:
        text += "\n\nAll questions answered. Review your answers, then Submit."
    return discord.Embed(
        title="Your Staff Application", description=text, color=0x5865F2
    ).set_footer(text=app["id"])


def review_embed(app):
    status = "pending" if app["status"] == "queued" else app["status"]
    color = {"accepted": 0x57F287, "declined": 0xED4245}.get(status, 0x5865F2)
    embed = discord.Embed(
        title="Staff Application",
        color=color,
        description="Complete answers are attached as a text file. Review privately before deciding.",
    )
    embed.add_field(name="Applicant", value=f"<@{app['user']}> (`{app['user']}`)")
    embed.add_field(name="Position", value=app["position"])
    embed.add_field(name="Status", value=status.replace("_", " ").title())
    embed.add_field(
        name="Reviewer", value=f"<@{app['reviewer']}>" if app["reviewer"] else "Unclaimed"
    )
    embed.add_field(name="Submitted", value=f"<t:{int(app['submitted'])}:f>")
    if app.get("reason"):
        embed.add_field(name="Decision message", value=app["reason"], inline=False)
    embed.set_footer(text=f"staffapp:{app['id']}")
    return embed


class StaffApplications(commands.Cog):
    """Private staff applications, persistent buttons, and owner error alerts."""

    __version__ = "1.2.1"

    def __init__(self, bot):
        self.bot = bot
        self.store = Store(cog_data_path(self) / "applications.sqlite3")
        self.alerts = Alerts(bot, self.store)
        self._worker = None
        self._views = {}  # one current persistent view per message
        self._locks = WeakValueDictionary()
        self._panel_counts = {}
        self._panel_paused = {}
        self._panel_retry = {}

    async def cog_load(self):
        for guild_id in self.store.guilds():
            cfg = self.store.settings(guild_id)
            if cfg["panel_message"]:
                self.track(panel(self, guild_id)["view"], cfg["panel_message"])
        for app in self.store.all():
            if app["status"] == "draft" and app["dm_message"]:
                self.track(DraftView(self, app), app["dm_message"])
            if app["message"] and app["status"] in {
                "pending",
                "under_review",
                "accepted",
                "declined",
            }:
                self.track(ReviewView(self, app), app["message"])
        self._worker = asyncio.create_task(self.worker(), name="staffapplications-delivery")

    async def cog_unload(self):
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
        for view in self._views.values():
            view.stop()
        self._views.clear()
        self.store.close()

    def track(self, view, message_id):
        previous = self._views.pop(message_id, None)
        if previous:
            previous.stop()
        self.bot.add_view(view, message_id=message_id)
        self._views[message_id] = view

    def untrack(self, message_id):
        view = self._views.pop(message_id, None)
        if view:
            view.stop()

    async def guard(self, interaction, guild_id, reviewer=False, verify_membership=True):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            raise UserError("The bot is no longer in this server.")
        if interaction.guild_id not in (None, guild_id):
            raise UserError("This control belongs to a different server.")
        if interaction.user.bot:
            raise UserError("Bots cannot apply.")
        if await self.bot.cog_disabled_in_guild(self, guild):
            raise UserError("Staff applications are disabled in this server.")
        if not await self.bot.allowed_by_whitelist_blacklist(who=interaction.user):
            raise UserError("You cannot use this bot.")
        # Guild interactions carry up-to-date roles; DMs need an explicit membership lookup.
        member = interaction.user if interaction.guild_id == guild_id else None
        if member is None and not verify_membership:
            return guild  # Modal submissions recheck membership after acknowledging.
        if member is None:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except discord.NotFound:
                raise UserError("You must still be a member of the server to apply.") from None
        if reviewer:
            if interaction.guild_id != guild_id:
                raise UserError("Review applications from the private review channel.")
            role_id = self.store.settings(guild_id)["reviewer_role"]
            if not (
                member.guild_permissions.manage_guild
                or any(r.id == role_id for r in member.roles)
                or await self.bot.is_owner(member)
            ):
                raise UserError("Only authorized reviewers can use this control.")
        return guild

    @staticmethod
    def check_review_message(interaction, app, modal=False):
        if interaction.channel_id != app["delivery_channel"]:
            raise UserError("Use the original review channel.")
        if not modal and getattr(interaction.message, "id", None) != app["message"]:
            raise UserError("Use the original application review card.")

    async def interaction_error(self, interaction, guild_id, error, app_id=None):
        if isinstance(error, UserError):
            await reply(interaction, str(error))
            return
        # Acknowledge before alert network requests so the applicant isn't left waiting.
        try:
            await reply(
                interaction,
                "Something went wrong. Any previously saved answers are kept. The bot owner is being notified; use My Application to check your progress.",
            )
        except discord.HTTPException:
            pass
        await self.alerts.report(guild_id, "interaction", error, app_id)

    async def handle(self, interaction, guild_id, action, app_id=None):
        modal_actions = {"continue", "accepted", "declined"}
        if action not in modal_actions:
            await interaction.response.defer(ephemeral=True)
        review_actions = {"view_answers", "claim", "under_review", "accepted", "declined"}
        await self.guard(
            interaction,
            guild_id,
            reviewer=action in review_actions,
            verify_membership=action != "continue",
        )
        cfg = self.store.settings(guild_id)
        if action in {"apply", "requirements", "status"}:
            if interaction.guild_id != guild_id:
                raise UserError("Use the panel inside the server.")
            if action == "requirements":
                return await reply(interaction, cfg["requirements"])
            app = self.store.latest(guild_id, interaction.user.id)
            if action == "status":
                if app is None:
                    return await reply(
                        interaction, "You have no application here yet. Use Apply Now."
                    )
                if app["status"] == "draft":
                    return await self.send_draft(interaction, app)
                return await reply(interaction, self.status_text(app))
            if app and app["status"] in {"draft", "queued", "pending", "under_review"}:
                if app["status"] == "draft":
                    return await self.send_draft(interaction, app)
                return await reply(interaction, self.status_text(app))
            if not cfg["open"]:
                raise UserError("Applications are currently closed.")
            return await reply(
                interaction,
                "Choose a position to begin your private application.",
                view=PositionView(self, guild_id),
            )
        app = self.store.get(app_id)
        if app["guild"] != guild_id:
            raise UserError("This application belongs to another server.")
        if action in review_actions:
            self.check_review_message(interaction, app)
            if action == "view_answers":
                pages = AnswerPages(self, app, interaction.user.id, reviewer=True)
                return await reply(
                    interaction, "Application answers", embed=pages.embed(), view=pages
                )
            if action in {"accepted", "declined"}:
                return await interaction.response.send_modal(DecisionModal(self, app, action))
            self.store.decide(app_id, interaction.user.id, action)
            return await reply(interaction, "Review assignment/status saved.")
        app = self.store.owned(app_id, interaction.user.id, draft=True)
        if action == "continue":
            index = next((i for i, a in enumerate(app["answers"]) if not a), None)
            if index is None:
                return await reply(
                    interaction, "All answers are saved. Review Answers, then Submit."
                )
            return await interaction.response.send_modal(AnswerModal(self, app, index))
        if action == "edit":
            return await reply(interaction, "Choose the answer to edit.", view=EditView(self, app))
        if action == "preview":
            pages = AnswerPages(self, app, interaction.user.id)
            return await reply(
                interaction,
                "Review your answers before submitting.",
                embed=pages.embed(),
                view=pages,
            )
        if action == "submit":
            self.store.submit(app_id, interaction.user.id)
            await reply(
                interaction,
                "Application saved and queued for staff delivery. Check My Application for delivery status.",
            )
            return await self.refresh_draft(app_id)
        if action == "cancel":
            return await reply(
                interaction, "Cancel this draft? This cannot be undone.", view=CancelView(self, app)
            )
        if action == "confirm_cancel":
            self.store.cancel(app_id, interaction.user.id)
            await reply(interaction, "Draft cancelled.")
            return await self.refresh_draft(app_id)
        raise UserError("Unknown application control.")

    @staticmethod
    def status_text(app):
        status = {
            "queued": "Saved — awaiting delivery to staff",
            "pending": "Delivered — awaiting review",
        }.get(app["status"], app["status"].replace("_", " ").title())
        return f"Application `{app['id']}`\n**{status}**" + (
            f"\n{app['reason']}" if app.get("reason") else ""
        )

    async def begin(self, interaction, guild_id, position):
        app = self.store.start(guild_id, interaction.user.id, position)
        if app["status"] != "draft":
            return await reply(interaction, self.status_text(app))
        await self.send_draft(interaction, app)

    async def send_draft(self, interaction, app):
        lock = self._locks.setdefault(app["id"], asyncio.Lock())
        async with lock:
            app = self.store.get(app["id"])
            if app["status"] != "draft":
                return await reply(interaction, self.status_text(app))
            view = DraftView(self, app)
            try:
                message = await interaction.user.send(
                    embed=draft_embed(app), view=view, allowed_mentions=NONE
                )
            except discord.Forbidden as exc:
                await reply(
                    interaction,
                    "I couldn't DM you. Enable direct messages for this server, then click My Application to retry. Your draft is saved.",
                )
                await self.alerts.report(app["guild"], "send application DM", exc, app["id"])
                return
            # Retire the previous DM controls; failed edits are harmless because every action checks saved state.
            old = app["dm_message"]
            app = self.store.get(app["id"])
            app.update(dm_message=message.id, dm_channel=message.channel.id)
            self.store.save(app)
            if old:
                self.untrack(old)
            self.track(view, message.id)
            await reply(interaction, "Check your DMs — your application is ready.")

    async def refresh_draft(self, app_id):
        app = self.store.get(app_id)
        if not app["dm_channel"] or not app["dm_message"]:
            return
        channel = self.bot.get_channel(app["dm_channel"]) or await self.bot.fetch_channel(
            app["dm_channel"]
        )
        message = channel.get_partial_message(app["dm_message"])
        if app["status"] == "draft":
            view = DraftView(self, app)
            await message.edit(embed=draft_embed(app), view=view, allowed_mentions=NONE)
            self.track(view, message.id)
        else:
            await message.edit(
                content=self.status_text(app), embed=None, view=None, allowed_mentions=NONE
            )
            self.untrack(message.id)

    async def review_channel(self, app):
        guild = self.bot.get_guild(app["guild"])
        if guild is None:
            raise RuntimeError("Guild unavailable")
        channel = guild.get_channel(app["delivery_channel"]) or await self.bot.fetch_channel(
            app["delivery_channel"]
        )
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError("Review channel missing")
        self.validate_channel(channel, private=True, review=True)
        return channel

    def validate_channel(self, channel, *, private=False, review=False):
        perms = channel.permissions_for(channel.guild.me)
        needed = ["view_channel", "send_messages", "embed_links"]
        if review:
            needed += ["attach_files", "read_message_history"]
        if not all(getattr(perms, p) for p in needed):
            raise UserError("Bot permissions needed: " + ", ".join(needed))
        if private and channel.permissions_for(channel.guild.default_role).view_channel:
            raise UserError(
                "Choose a private channel: deny View Channel for @everyone and grant access only to reviewers."
            )

    async def deliver(self, app_id):
        lock = self._locks.setdefault(app_id, asyncio.Lock())
        async with lock:
            await self._deliver(app_id)

    async def _deliver(self, app_id):
        app = self.store.get(app_id)
        if app["status"] != "queued":
            return
        channel = await self.review_channel(app)
        message = None
        if app["attempted"]:
            # Recover an accepted send whose HTTP reply or local commit was lost.
            # Read the entire relevant interval; never blindly resend on an ambiguous failure.
            message = await self.find_delivery(channel, app)
        if message is None:
            app["attempted"] = True
            self.store.save(app)
            message = await channel.send(
                embed=review_embed(app),
                file=transcript(app),
                view=ReviewView(self, app),
                allowed_mentions=NONE,
            )
        # Reload so concurrent administrative operations cannot be overwritten.
        app = self.store.get(app_id)
        app.update(message=message.id, status="pending", attempts=0, next_retry=0)
        self.store.save(app)
        self.track(ReviewView(self, app), message.id)

    async def find_delivery(self, channel, app):
        after = datetime.fromtimestamp(app["submitted"] - 5, timezone.utc)
        async for candidate in channel.history(limit=None, after=after, oldest_first=True):
            if candidate.author.id == self.bot.user.id and any(
                e.footer.text == f"staffapp:{app['id']}" for e in candidate.embeds
            ):
                return candidate
        return None

    async def side_effects(self, app_id):
        async with self._locks.setdefault(app_id, asyncio.Lock()):
            await self._side_effects(app_id)

    async def _side_effects(self, app_id):
        app = self.store.get(app_id)
        if app["status"] == "deleting":
            return
        update_error = None
        if app["ui_dirty"] and app["message"]:
            try:
                channel = await self.review_channel(app)
                await channel.get_partial_message(app["message"]).edit(
                    embed=review_embed(app), view=ReviewView(self, app), allowed_mentions=NONE
                )
                latest = self.store.get(app_id)
                # Do not erase a newer decision that arrived during the edit request.
                if (latest["status"], latest["reviewer"], latest.get("reason")) == (
                    app["status"],
                    app["reviewer"],
                    app.get("reason"),
                ):
                    latest["ui_dirty"] = False
                    self.store.save(latest)
                self.track(ReviewView(self, latest), app["message"])
            except Exception as exc:
                update_error = exc
        app = self.store.get(app_id)
        if app["notify"]:
            user = self.bot.get_user(app["user"]) or await self.bot.fetch_user(app["user"])
            try:
                await user.send(self.status_text(app), allowed_mentions=NONE)
            except discord.Forbidden as exc:
                # A blocked DM is permanent until the applicant changes privacy settings.
                # Status remains available in the server panel; no infinite retry spam.
                app = self.store.get(app_id)
                app.update(notify=False, notification_failed=True)
                self.store.save(app)
                await self.alerts.report(app["guild"], "decision DM blocked", exc, app_id)
            else:
                app = self.store.get(app_id)
                app.update(notify=False, notification_failed=False)
                self.store.save(app)

        if update_error is not None:
            raise update_error

    async def cycle(self):
        for saved in self.store.all():
            if saved["next_retry"] > time.time():
                continue
            try:
                if saved["status"] == "deleting":
                    await self.erase(saved)
                    continue
                if saved["status"] == "queued":
                    await self.deliver(saved["id"])
                if saved["ui_dirty"] or saved["notify"]:
                    await self.side_effects(saved["id"])
            except Exception as exc:
                try:
                    app = self.store.get(saved["id"])
                except UserError:
                    continue  # application was intentionally deleted
                app["attempts"] += 1
                app["next_retry"] = time.time() + min(3600, 30 * 2 ** min(app["attempts"], 7))
                self.store.save(app)
                await self.alerts.report(
                    saved["guild"], "application delivery/review update", exc, saved["id"]
                )
        for app in self.store.expired():
            try:
                await self.erase(app)
            except Exception as exc:
                await self.alerts.report(app["guild"], "retention cleanup", exc, app["id"])

        for guild_id in self.store.guilds():
            cfg = self.store.settings(guild_id)
            signature = (cfg["panel_channel"], cfg["panel_message"])
            if (
                self._panel_paused.get(guild_id) == signature
                or self._panel_retry.get(guild_id, 0) > time.time()
            ):
                continue
            count = self.store.submitted_count(guild_id)
            if cfg["panel_message"] and self._panel_counts.get(guild_id) != count:
                try:
                    await self.publish_panel(guild_id)
                except PanelUnavailable as exc:
                    self._panel_paused[guild_id] = signature
                    await self.alerts.report(guild_id, "refresh application panel", exc)
                except Exception as exc:
                    self._panel_retry[guild_id] = time.time() + 60
                    await self.alerts.report(guild_id, "refresh application panel", exc)

    async def worker(self):
        await self.bot.wait_until_red_ready()
        while True:
            try:
                await self.cycle()
            except Exception as exc:
                await self.alerts.report(None, "background worker", exc)
            await asyncio.sleep(10)

    async def erase(self, app):
        async with self._locks.setdefault(app["id"], asyncio.Lock()):
            await self._erase(app["id"])

    async def _erase(self, app_id):
        app = self.store.get(app_id)
        # Persist deletion before network I/O so no new answer/decision can race it.
        app.setdefault("deleting_from", app["status"])
        app["status"] = "deleting"
        self.store.save(app)
        if app["deleting_from"] == "queued" and app["attempted"] and not app["message"]:
            # Reconcile an ambiguous send, but never send an application just to delete it.
            try:
                channel = await self.review_channel(app)
            except discord.NotFound:
                channel = None
            if channel is not None:
                message = await self.find_delivery(channel, app)
                if message:
                    app["message"] = message.id
                    self.store.save(app)
        for channel_id, message_id in [
            (app["delivery_channel"], app["message"]),
            (app["dm_channel"], app["dm_message"]),
        ]:
            if channel_id and message_id:
                try:
                    channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(
                        channel_id
                    )
                    await channel.get_partial_message(message_id).delete()
                except discord.NotFound:
                    pass
                self.untrack(message_id)
        self.store.remove(app["id"])

    async def red_delete_data_for_user(self, *, requester, user_id):
        for app in self.store.all():
            if app["user"] == user_id:
                await self.erase(app)
            elif app["reviewer"] == user_id:
                app["reviewer"] = None
                app["ui_dirty"] = bool(app["message"])
                self.store.save(app)

    async def cog_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(
            error,
            (UserError, commands.UserInputError, commands.CheckFailure, commands.CommandOnCooldown),
        ):
            await ctx.send(str(error) or "You cannot use this command.", allowed_mentions=NONE)
            return
        try:
            await ctx.send("An unexpected error occurred. The bot owner is being notified.")
        finally:
            await self.alerts.report(getattr(ctx.guild, "id", None), "command", error)

    @commands.group(name="staffapp", invoke_without_command=True)
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def staffapp(self, ctx):
        """Configure staff applications. Start with staffapp setup."""
        await ctx.send_help()

    @staffapp.command(name="setup")
    async def setup_command(
        self,
        ctx,
        panel_channel: discord.TextChannel,
        review_channel: discord.TextChannel,
        error_channel: discord.TextChannel,
        reviewer_role: discord.Role,
    ):
        """Configure existing channels: panel, private reviews, private errors, reviewers."""
        if len({panel_channel.id, review_channel.id, error_channel.id}) != 3:
            raise UserError("Choose three different channels.")
        if any(c.guild.id != ctx.guild.id for c in (panel_channel, review_channel, error_channel)):
            raise UserError("All channels must be in this server.")
        if reviewer_role.is_default() or reviewer_role.managed:
            raise UserError("Choose a staff role that you manage, not @everyone or a managed role.")
        self.validate_channel(panel_channel)
        self.validate_channel(review_channel, private=True, review=True)
        self.validate_channel(error_channel, private=True)
        if not review_channel.permissions_for(reviewer_role).view_channel:
            raise UserError("The reviewer role needs View Channel in the review channel.")
        old = self.store.settings(ctx.guild.id)
        self.store.configure(
            ctx.guild.id,
            panel_channel=panel_channel.id,
            review_channel=review_channel.id,
            error_channel=error_channel.id,
            reviewer_role=reviewer_role.id,
            open=False,
            manage_panel_visibility=(
                old["manage_panel_visibility"] and old["panel_channel"] == panel_channel.id
            ),
        )
        if old["panel_channel"] != panel_channel.id:
            self.untrack(old["panel_message"])
            self.store.configure(ctx.guild.id, panel_message=None)
        if self.store.settings(ctx.guild.id)["manage_panel_visibility"]:
            await self.set_panel_visibility(ctx.guild.id, False)
        await self.publish_panel(ctx.guild.id)
        await ctx.send(
            "Configured. Applications start closed. Use `staffapp open true` when ready, and `staffapp testerror` to verify alerts."
        )

    @staffapp.command(name="createchannels")
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    async def create_channels(self, ctx, reviewer_role: discord.Role):
        """Create all channels privately; opening applications publishes only the panel."""
        if reviewer_role.is_default() or reviewer_role.managed:
            raise UserError("Choose a normal staff role.")
        if self.store.settings(ctx.guild.id)["panel_channel"]:
            raise UserError("Channels are already configured. Use staffapp setup to change them.")
        bot_overwrite = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
        )
        panel_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(
                view_channel=False, send_messages=False
            ),
            ctx.guild.me: bot_overwrite,
            reviewer_role: discord.PermissionOverwrite(
                view_channel=True, read_message_history=True
            ),
        }
        private = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            ctx.guild.me: bot_overwrite,
            reviewer_role: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }
        created = []
        try:
            for name, overwrites in [
                ("staff-applications", panel_overwrites),
                ("application-reviews", private),
                ("application-errors", private),
            ]:
                created.append(
                    await ctx.guild.create_text_channel(
                        name, overwrites=overwrites, reason="Staff application setup"
                    )
                )
        except Exception:
            # Roll back only empty channels created by this command.
            for channel in created:
                try:
                    await channel.delete(reason="Incomplete staff application setup")
                except discord.HTTPException:
                    pass
            raise
        self.store.configure(
            ctx.guild.id,
            panel_channel=created[0].id,
            review_channel=created[1].id,
            error_channel=created[2].id,
            reviewer_role=reviewer_role.id,
            open=False,
            manage_panel_visibility=True,
        )
        await self.publish_panel(ctx.guild.id)
        await ctx.send(
            "All channels created privately. Use `staffapp open true` to make the application channel public. Review and error channels stay private."
        )

    async def resolve_panel_channel(self, guild_id):
        channel_id = self.store.settings(guild_id)["panel_channel"]
        if not channel_id:
            raise PanelUnavailable("unconfigured")
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            # Cache misses during reload/startup do not mean the channel was deleted.
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.NotFound:
                raise PanelUnavailable("missing", channel_id) from None
            except discord.Forbidden:
                raise PanelUnavailable("forbidden", channel_id) from None
        if not isinstance(channel, discord.TextChannel) or channel.guild.id != guild_id:
            raise PanelUnavailable("invalid", channel_id)
        return channel

    async def publish_panel(self, guild_id):
        cfg = self.store.settings(guild_id)
        channel = await self.resolve_panel_channel(guild_id)
        rendered_count = self.store.submitted_count(guild_id)
        payload = panel(self, guild_id)
        message = None
        try:
            if cfg["panel_message"]:
                try:
                    message = await channel.get_partial_message(cfg["panel_message"]).edit(
                        **payload, allowed_mentions=NONE
                    )
                except discord.NotFound as exc:
                    if exc.code != 10008:  # Only an unknown message permits recreation.
                        raise
            if message is None:
                message = await channel.send(**payload, allowed_mentions=NONE)
        except discord.NotFound:
            raise PanelUnavailable("missing", channel.id) from None
        except discord.Forbidden:
            raise PanelUnavailable("forbidden", channel.id) from None
        self.store.configure(guild_id, panel_message=message.id)
        self.track(payload["view"], message.id)
        self._panel_counts[guild_id] = rendered_count
        self._panel_paused.pop(guild_id, None)
        self._panel_retry.pop(guild_id, None)

    @staffapp.command(name="panel")
    async def panel_command(self, ctx):
        """Create, repair, or refresh the public panel."""
        await self.publish_panel(ctx.guild.id)
        await ctx.tick()

    async def set_panel_visibility(self, guild_id, enabled):
        channel = await self.resolve_panel_channel(guild_id)
        if not channel.permissions_for(channel.guild.me).manage_roles:
            raise UserError(
                "I need Manage Roles in the application channel to change its visibility."
            )
        overwrite = channel.overwrites_for(channel.guild.default_role)
        overwrite.view_channel = enabled
        # Preserve other permissions, including the read-only panel setting.
        await channel.set_permissions(
            channel.guild.default_role,
            overwrite=overwrite,
            reason="Staff applications opened" if enabled else "Staff applications closed",
        )

    @staffapp.command(name="open")
    async def open_command(self, ctx, enabled: bool):
        """Open/close applications and show/hide the bot-created application channel."""
        async with self._locks.setdefault(("visibility", ctx.guild.id), asyncio.Lock()):
            cfg = self.store.settings(ctx.guild.id)
            if enabled and not all(
                cfg[k]
                for k in ("panel_channel", "review_channel", "error_channel", "reviewer_role")
            ):
                raise UserError("Configure all channels and a reviewer role first.")
            if not enabled:
                # Stop accepting applications even if Discord rejects the permission change.
                self.store.configure(ctx.guild.id, open=False)
            if cfg["manage_panel_visibility"]:
                await self.set_panel_visibility(ctx.guild.id, enabled)
            self.store.configure(ctx.guild.id, open=enabled)
            await self.publish_panel(ctx.guild.id)
            await ctx.tick()

    @staffapp.command(name="errorchannel")
    async def error_channel_command(self, ctx, channel: discord.TextChannel):
        """Choose the private error channel. Owner DMs remain enabled."""
        self.validate_channel(channel, private=True)
        if channel.id in (
            self.store.settings(ctx.guild.id)["panel_channel"],
            self.store.settings(ctx.guild.id)["review_channel"],
        ):
            raise UserError("Use a separate private error channel.")
        self.store.configure(ctx.guild.id, error_channel=channel.id)
        await ctx.tick()

    @staffapp.command(name="testerror")
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def test_error(self, ctx):
        """Send a clearly labeled test to owner DMs and the configured error channel."""
        await self.alerts.report(
            ctx.guild.id, "TEST — requested alert check", RuntimeError("test"), force=True
        )
        await ctx.send(
            "Test attempted on both routes. Check the owner's DMs and error channel; delivery failures are recorded in the bot log."
        )

    @staffapp.command(name="positions")
    async def positions_command(self, ctx, *, positions: str):
        """Set 1–25 positions separated by |. Existing drafts keep their position."""
        values = [v.strip() for v in positions.split("|")]
        if (
            not 1 <= len(values) <= 25
            or any(not v or len(v) > 100 for v in values)
            or len(set(values)) != len(values)
        ):
            raise UserError("Use 1–25 unique positions, each 1–100 characters, separated by |.")
        self.store.configure(ctx.guild.id, positions=values)
        await ctx.tick()

    @staffapp.command(name="questions")
    async def questions_command(self, ctx, *, questions: str):
        """Set 1–20 questions separated by |. Existing drafts keep their questions."""
        values = [v.strip() for v in questions.split("|")]
        if not 1 <= len(values) <= 20 or any(not v or len(v) > 500 for v in values):
            raise UserError("Use 1–20 questions, each 1–500 characters, separated by |.")
        self.store.configure(ctx.guild.id, questions=values)
        await ctx.tick()

    @staffapp.command(name="preset")
    async def preset_command(self, ctx, name: str = "onepiece"):
        """Apply the One Piece panel and ten moderator questions to future drafts."""
        if name.lower() != "onepiece":
            raise UserError("Available preset: onepiece")
        self.store.configure(ctx.guild.id, **ONE_PIECE_TEMPLATE, template_version=2)
        if self.store.settings(ctx.guild.id)["panel_channel"]:
            await self.publish_panel(ctx.guild.id)
        await ctx.send(
            "One Piece panel and all ten moderator questions loaded. Existing drafts and submitted answers are unchanged."
        )

    @staffapp.command(name="requirements")
    async def requirements_command(self, ctx, *, text: str):
        """Set the requirements shown to applicants (up to 1,800 characters)."""
        if not 1 <= len(text) <= 1800:
            raise UserError("Use 1–1,800 characters.")
        self.store.configure(ctx.guild.id, requirements=text)
        if self.store.settings(ctx.guild.id)["panel_channel"]:
            await self.publish_panel(ctx.guild.id)
        await ctx.tick()

    @staffapp.command(name="appearance")
    async def appearance_command(self, ctx, color: discord.Color, *, text: str):
        """Set panel appearance: #5865F2 Title | Description."""
        parts = [s.strip() for s in text.split("|", 1)]
        if len(parts) != 2 or not 1 <= len(parts[0]) <= 100 or not 1 <= len(parts[1]) <= 1500:
            raise UserError(
                "Use Title | Description (title 1–100, description 1–1,500 characters)."
            )
        self.store.configure(ctx.guild.id, title=parts[0], description=parts[1], color=color.value)
        await self.publish_panel(ctx.guild.id)
        await ctx.tick()

    @staffapp.command(name="limits")
    async def limits_command(self, ctx, cooldown_hours: int, retention_days: int):
        """Set reapplication cooldown (0–8760 hours) and retention (1–365 days)."""
        if not 0 <= cooldown_hours <= 8760 or not 1 <= retention_days <= 365:
            raise UserError("Cooldown must be 0–8760 hours; retention must be 1–365 days.")
        self.store.configure(
            ctx.guild.id, cooldown_hours=cooldown_hours, retention_days=retention_days
        )
        await ctx.tick()

    @staffapp.command(name="retry")
    async def retry_command(self, ctx, application_id: str):
        """Retry a failed delivery, card update, or applicant notification."""
        app = self.store.get(application_id)
        if app["guild"] != ctx.guild.id:
            raise UserError("That application belongs to another server.")
        app.update(next_retry=0, attempts=0)
        if app.get("notification_failed"):
            app["notify"] = True
        self.store.save(app)
        await ctx.send(
            "Retry scheduled. If the original review channel was deleted, use staffapp reroute."
        )

    @staffapp.command(name="reroute")
    async def reroute_command(self, ctx, application_id: str, channel: discord.TextChannel):
        """Move an undelivered application only after its old channel is deleted."""
        async with self._locks.setdefault(application_id, asyncio.Lock()):
            app = self.store.get(application_id)
            if app["guild"] != ctx.guild.id or app["status"] != "queued":
                raise UserError("Choose an undelivered application from this server.")
            self.validate_channel(channel, private=True, review=True)
            try:
                await self.bot.fetch_channel(app["delivery_channel"])
            except discord.NotFound:
                pass
            else:
                raise UserError(
                    "The original channel still exists. Restore permissions and use staffapp retry to avoid duplicate delivery."
                )
            app.update(delivery_channel=channel.id, attempted=False, next_retry=0)
            self.store.save(app)
            await ctx.tick()

    @staffapp.command(name="delete")
    async def delete_command(self, ctx, application_id: str, confirm: bool = False):
        """Delete an application and its bot-posted review/DM messages; pass true to confirm."""
        app = self.store.get(application_id)
        if app["guild"] != ctx.guild.id:
            raise UserError("That application belongs to another server.")
        if not confirm:
            raise UserError(
                "Add true to confirm deletion of this application and its review attachment."
            )
        await self.erase(app)
        await ctx.tick()

    @staffapp.command(name="settings")
    async def settings_command(self, ctx):
        """Show configuration and application queue counts."""
        cfg = self.store.settings(ctx.guild.id)
        counts = {}
        for app in self.store.all():
            if app["guild"] == ctx.guild.id:
                counts[app["status"]] = counts.get(app["status"], 0) + 1
        await ctx.send(
            f"Applications: {'open' if cfg['open'] else 'closed'}\n"
            f"Panel: {cfg['panel_channel']} · Reviews: {cfg['review_channel']} · Errors: {cfg['error_channel']}\n"
            f"Reviewer role: {cfg['reviewer_role']}\nPositions: {', '.join(cfg['positions'])}\n"
            f"Questions: {len(cfg['questions'])} · Cooldown: {cfg['cooldown_hours']} hours · Retention: {cfg['retention_days']} days\n"
            f"Counts: {counts}",
            allowed_mentions=NONE,
        )
