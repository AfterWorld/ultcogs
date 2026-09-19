"""Repository navigation for Red's existing help command."""

import asyncio
import logging
from dataclasses import replace

import discord
from redbot.core import commands
from redbot.core.commands.help import HelpSettings, RedHelpFormatter

log = logging.getLogger("red.AfterWorld.repohelp")
NONE = discord.AllowedMentions.none()
PAGE_SIZE = 10


def repository_for(cog, installed):
    if cog is None:
        return "Red Core"
    module = type(cog).__module__
    if module.startswith("redbot.core.") or module.startswith("redbot.cogs."):
        return "Red Core"
    for item in installed:
        if module == item.name or module.startswith(item.name + "."):
            name = getattr(item, "repo_name", None)
            if name and name != "MISSING_REPO":
                return f"Repository: {name}"
    return "Local / Unknown Source"


class RepositoryFormatter(RedHelpFormatter):
    def __init__(self, owner):
        self.owner = owner

    async def catalog(self, ctx, settings):
        # Browsing never exposes hidden or unavailable commands, even if the
        # owner's standard detailed-help settings are more permissive.
        settings = replace(settings, verify_checks=True, show_hidden=False)
        installed = ()
        downloader = ctx.bot.get_cog("Downloader")
        if downloader is not None:
            try:
                installed = await downloader.installed_cogs()
            except Exception:
                log.exception("Could not read Downloader metadata; using unknown-source group")
        groups = {}
        for name, command_map in await self.get_bot_help_mapping(ctx, settings):
            cog = ctx.bot.get_cog(name) if name else None
            if cog and ctx.guild and await ctx.bot.cog_disabled_in_guild(cog, ctx.guild):
                continue
            repo = repository_for(cog, installed)
            groups.setdefault(repo, {})[name or ""] = command_map
        return dict(sorted(groups.items(), key=lambda pair: pair[0].casefold()))

    async def format_bot_help(self, ctx, help_settings):
        if ctx.guild and await ctx.bot.cog_disabled_in_guild(self.owner, ctx.guild):
            return await RedHelpFormatter().format_bot_help(ctx, help_settings)
        view = RepositoryMenu(self, ctx, help_settings)
        await view.refresh()
        if not view.groups:
            return await ctx.send("No commands are available here.", allowed_mentions=NONE)
        destination = ctx.author if help_settings.max_pages_in_guild == 0 else ctx
        try:
            view.message = await destination.send(**view.payload())
        except discord.Forbidden:
            view.stop()
            if destination is ctx.author:
                await ctx.send("I couldn't DM your help menu. Please enable DMs and try again.")
                return
            raise
        self.owner.views.add(view)


class RepositoryMenu(discord.ui.View):
    def __init__(self, formatter, ctx, settings):
        super().__init__(timeout=180)
        self.formatter, self.ctx, self.settings = formatter, ctx, settings
        self.repo = self.cog = None
        self.page = 0
        self.groups = {}
        self.message = None
        self.embeds = True
        self.lock = asyncio.Lock()

    async def refresh(self):
        self.settings = await HelpSettings.from_context(self.ctx)
        self.groups = await self.formatter.catalog(self.ctx, self.settings)
        self.embeds = await self.formatter.embed_requested(self.ctx)
        if self.repo not in self.groups:
            self.repo = self.cog = None
        elif self.cog is not None and self.cog not in self.groups[self.repo]:
            self.cog = None
        self.render_controls()

    def entries(self):
        if self.repo is None:
            return [(name, f"{len(cogs)} cogs") for name, cogs in self.groups.items()]
        if self.cog is None:
            return [
                (name, f"{len(cmds)} commands")
                for name, cmds in sorted(self.groups[self.repo].items())
            ]
        return [
            (name, command.format_shortdoc_for_context(self.ctx) or "View command help")
            for name, command in sorted(self.groups[self.repo][self.cog].items())
        ]

    def render_controls(self):
        self.clear_items()
        entries = self.entries()
        self.pages = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = min(self.page, self.pages - 1)
        self.visible = entries[self.page * PAGE_SIZE : (self.page + 1) * PAGE_SIZE]
        if self.visible:
            select = discord.ui.Select(
                placeholder="Choose a repository"
                if self.repo is None
                else "Choose a cog"
                if self.cog is None
                else "View command details",
                options=[
                    discord.SelectOption(
                        label=(name or "Uncategorized")[:100],
                        value=str(i),
                        description=description[:100],
                    )
                    for i, (name, description) in enumerate(self.visible)
                ],
            )
            # Capture this page's keys so a queued interaction cannot select a
            # different item after a concurrent page change.
            choices = [name for name, _ in self.visible]
            state = (self.repo, self.cog, self.page)

            async def select_callback(interaction):
                await self.navigate(interaction, "select", choices[int(select.values[0])], state)

            select.callback = select_callback
            self.add_item(select)
        for label, action, disabled in [
            ("Home", "home", self.repo is None and self.page == 0),
            ("Back", "back", self.repo is None),
            ("Previous", "previous", self.page == 0),
            ("Next", "next", self.page + 1 == self.pages),
        ]:
            button = discord.ui.Button(label=label, disabled=disabled, row=1)

            async def callback(interaction, action=action):
                await self.navigate(interaction, action)

            button.callback = callback
            self.add_item(button)

    def payload(self):
        heading = (
            (self.cog or "Uncategorized") if self.cog is not None else self.repo or "Repositories"
        )
        lines = [
            f"**{discord.utils.escape_markdown(name or 'Uncategorized')[:100]}** — {discord.utils.escape_markdown(desc)[:100]}"
            for name, desc in self.visible
        ]
        description = "\n".join(lines) or "No commands are available here."
        footer = f"Page {self.page + 1}/{self.pages} • {self.ctx.clean_prefix}help <command> for detailed help"
        title = f"{self.ctx.me.display_name[:100]} Help Menu — {heading[:100]}"
        if self.embeds:
            embed = discord.Embed(title=title, description=description, color=0x2BBBAD)
            embed.set_footer(text=footer[:200])
            return dict(content=None, embed=embed, view=self, allowed_mentions=NONE)
        # Keep text messages under Discord's 2,000-character limit.
        return dict(
            content=f"{title}\n{description[:1500]}\n{footer[:200]}",
            embed=None,
            view=self,
            allowed_mentions=NONE,
        )

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Run your own help command to browse.", ephemeral=True
            )
            return False
        return True

    async def navigate(self, interaction, action, key=None, state=None):
        await interaction.response.defer()
        async with self.lock:
            if self.is_finished():
                return
            if self.ctx.guild:
                member = self.ctx.guild.get_member(self.ctx.author.id)
                if member is None:
                    await interaction.followup.send(
                        "Run help again after rejoining the server.", ephemeral=True
                    )
                    return
                self.ctx.author = member
            if not await self.ctx.bot.allowed_by_whitelist_blacklist(self.ctx.author):
                return
            if self.ctx.guild and await self.ctx.bot.cog_disabled_in_guild(
                self.formatter.owner, self.ctx.guild
            ):
                return
            old_state = (self.repo, self.cog, self.page)
            await self.refresh()
            if action == "select":
                if state != old_state or state != (self.repo, self.cog, self.page):
                    await interaction.edit_original_response(**self.payload())
                    return
                available = dict(self.entries())
                if key not in available:
                    await interaction.edit_original_response(**self.payload())
                    return
                if self.repo is None:
                    self.repo = key
                elif self.cog is None:
                    self.cog = key
                else:
                    command = self.groups[self.repo][self.cog][key]
                    await self.formatter.send_help(self.ctx, command)
                    return
                self.page = 0
            elif action == "home":
                self.repo = self.cog = None
                self.page = 0
            elif action == "back":
                if self.cog is not None:
                    self.cog = None
                else:
                    self.repo = None
                self.page = 0
            else:
                self.page = max(0, self.page + (1 if action == "next" else -1))
            self.render_controls()
            await interaction.edit_original_response(**self.payload())

    async def on_timeout(self):
        self.formatter.owner.views.discard(self)
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass

    async def on_error(self, interaction, error, item):
        log.error(
            "Repository help interaction failed", exc_info=(type(error), error, error.__traceback__)
        )
        text = "The help menu couldn't refresh. Please run help again."
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)


class RepoHelp(commands.Cog):
    """Browse loaded cogs by repository using the existing help command."""

    __version__ = "1.0.0"

    def __init__(self, bot):
        self.bot = bot
        self.views = set()
        self.formatter = RepositoryFormatter(self)

    async def cog_load(self):
        try:
            self.bot.set_help_formatter(self.formatter)
        except RuntimeError as error:
            raise RuntimeError(
                "Another custom help formatter is active. Unload that help cog before loading repohelp."
            ) from error

    def cog_unload(self):
        if self.bot._help_formatter is self.formatter:
            self.bot.reset_help_formatter()
        for view in self.views:
            view.stop()
        self.views.clear()

    async def red_delete_data_for_user(self, **kwargs):
        return
