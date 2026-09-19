from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import discord
import pytest
from redbot.core import commands
from redbot.core.commands.help import HelpSettings, RedHelpFormatter

from repohelp.repohelp import RepoHelp, RepositoryMenu, repository_for


class Example(commands.Cog):
    @commands.command()
    async def hello(self, ctx):
        """Say hello."""


@pytest.fixture
def env(monkeypatch):
    settings = HelpSettings()
    monkeypatch.setattr(HelpSettings, "from_context", AsyncMock(return_value=settings))
    example = Example()
    example.__class__.__module__ = "example.main"
    example.hello.cog = example
    example.hello.can_see = AsyncMock(return_value=True)
    downloader = NS(
        installed_cogs=AsyncMock(return_value=[NS(name="example", repo_name="ultcogs")])
    )
    cogs = {"Example": example, "Downloader": downloader}
    bot = NS(
        cogs={"Example": example},
        commands=[example.hello],
        get_cog=lambda name: cogs.get(name),
        cog_disabled_in_guild=AsyncMock(return_value=False),
        allowed_by_whitelist_blacklist=AsyncMock(return_value=True),
        embed_requested=AsyncMock(return_value=True),
        _help_formatter=RedHelpFormatter(),
    )
    # Exercise Red's real formatter registration/conflict behavior.
    from redbot.core.bot import Red

    bot.set_help_formatter = lambda formatter: Red.set_help_formatter(bot, formatter)
    bot.reset_help_formatter = lambda: Red.reset_help_formatter(bot)
    author = NS(id=1, send=AsyncMock())
    ctx = NS(
        bot=bot,
        author=author,
        guild=NS(get_member=lambda uid: author),
        clean_prefix=".",
        me=NS(display_name="Sunny Go Support"),
        send=AsyncMock(),
    )
    owner = RepoHelp(bot)
    return NS(owner=owner, ctx=ctx, example=example, downloader=downloader, settings=settings)


def click(uid=1):
    return NS(
        user=NS(id=uid),
        response=NS(defer=AsyncMock(), send_message=AsyncMock()),
        followup=NS(send=AsyncMock()),
        edit_original_response=AsyncMock(),
    )


async def menu(env):
    view = RepositoryMenu(env.owner.formatter, env.ctx, env.settings)
    await view.refresh()
    return view


async def test_mapping_uses_downloader_and_filters_permissions(env):
    groups = await env.owner.formatter.catalog(env.ctx, env.settings)
    assert list(groups) == ["Repository: ultcogs"]
    assert list(groups["Repository: ultcogs"]["Example"]) == ["hello"]
    env.example.hello.can_see.return_value = False
    assert await env.owner.formatter.catalog(env.ctx, env.settings) == {}
    env.example.hello.can_see.return_value = True
    env.ctx.bot.cog_disabled_in_guild.return_value = True
    assert await env.owner.formatter.catalog(env.ctx, env.settings) == {}


async def test_unknown_metadata_and_core(env):
    env.downloader.installed_cogs.side_effect = RuntimeError("unavailable")
    groups = await env.owner.formatter.catalog(env.ctx, env.settings)
    assert list(groups) == ["Local / Unknown Source"]
    assert repository_for(None, []) == "Red Core"
    core = type("Core", (), {"__module__": "redbot.cogs.admin.admin"})()
    assert repository_for(core, []) == "Red Core"
    assert (
        repository_for(env.example, [NS(name="exam", repo_name="wrong")])
        == "Local / Unknown Source"
    )
    assert (
        repository_for(env.example, [NS(name="example", repo_name="MISSING_REPO")])
        == "Local / Unknown Source"
    )


async def test_navigation_and_command_detail(env):
    view = await menu(env)
    i = click()
    await view.navigate(i, "select", "Repository: ultcogs", (None, None, 0))
    assert view.repo == "Repository: ultcogs"
    await view.navigate(i, "select", "Example", (view.repo, None, 0))
    assert view.cog == "Example"
    env.owner.formatter.send_help = AsyncMock()
    await view.navigate(i, "select", "hello", (view.repo, view.cog, 0))
    env.owner.formatter.send_help.assert_awaited_once_with(env.ctx, env.example.hello)
    await view.navigate(i, "back")
    assert view.cog is None
    await view.navigate(i, "home")
    assert view.repo is None


async def test_permissions_rechecked_before_selection(env):
    view = await menu(env)
    await view.navigate(click(), "select", "Repository: ultcogs", (None, None, 0))
    env.example.hello.can_see.return_value = False
    await view.navigate(click(), "select", "Example", (view.repo, None, 0))
    assert view.repo is None
    assert view.groups == {}


async def test_only_requester_controls_menu(env):
    view = await menu(env)
    stranger = click(2)
    assert not await view.interaction_check(stranger)
    stranger.response.send_message.assert_awaited_once()
    assert await view.interaction_check(click())


async def test_pagination_and_stale_selection(env):
    env.owner.formatter.catalog = AsyncMock(
        return_value={f"Repo {n:02}": {"Example": {}} for n in range(26)}
    )
    view = await menu(env)
    assert view.pages == 3
    assert len(view.children[0].options) == 10
    await view.navigate(click(), "next")
    assert view.page == 1
    await view.navigate(click(), "select", "Repo 00", (None, None, 0))
    assert view.repo is None
    await view.navigate(click(), "next")
    assert len(view.children[0].options) == 6
    assert view.children[-1].disabled
    await view.navigate(click(), "home")
    assert view.page == 0


async def test_unload_and_conflicts(env):
    await env.owner.cog_load()
    assert env.ctx.bot._help_formatter is env.owner.formatter
    other = RepoHelp(env.ctx.bot)
    with pytest.raises(RuntimeError, match="Another custom help"):
        await other.cog_load()
    other.cog_unload()
    assert env.ctx.bot._help_formatter is env.owner.formatter
    view = await menu(env)
    env.owner.views.add(view)
    env.owner.cog_unload()
    assert type(env.ctx.bot._help_formatter) is RedHelpFormatter
    assert view.is_finished()
    assert not env.owner.views


async def test_text_output_and_timeout(env):
    env.ctx.bot.embed_requested.return_value = False
    view = await menu(env)
    payload = view.payload()
    assert payload["embed"] is None
    assert "Repository: ultcogs" in payload["content"]
    assert len(payload["content"]) <= 2000
    view.message = NS(edit=AsyncMock())
    env.owner.views.add(view)
    await view.on_timeout()
    view.message.edit.assert_awaited_once_with(view=None)
    assert view not in env.owner.views


async def test_dm_destination_and_blocked_dm(env):
    await env.owner.formatter.format_bot_help(env.ctx, HelpSettings(max_pages_in_guild=0))
    env.ctx.author.send.assert_awaited_once()
    env.ctx.send.assert_not_called()
    env.ctx.author.send.side_effect = discord.Forbidden(
        NS(status=403, reason="Forbidden"), "blocked"
    )
    await env.owner.formatter.format_bot_help(env.ctx, HelpSettings(max_pages_in_guild=0))
    assert "couldn't DM" in env.ctx.send.call_args.args[0]


async def test_direct_command_help_inherited(env, monkeypatch):
    assert env.owner.formatter.send_help.__func__ is RedHelpFormatter.send_help
    monkeypatch.setattr(env.owner.formatter, "format_command_help", AsyncMock())
    await env.owner.formatter.send_help(env.ctx, env.example.hello)
    env.owner.formatter.format_command_help.assert_awaited_once_with(
        env.ctx, env.example.hello, help_settings=env.settings
    )


async def test_empty_menu_and_left_server(env):
    view = await menu(env)
    env.ctx.guild.get_member = lambda uid: None
    i = click()
    await view.navigate(i, "next")
    i.followup.send.assert_awaited_once()
    env.example.hello.can_see.return_value = False
    await env.owner.formatter.format_bot_help(env.ctx, env.settings)
    assert env.ctx.send.call_args.args[0] == "No commands are available here."


async def test_disabled_commands_excluded_even_with_permissive_settings(env):
    env.example.hello.enabled = False
    settings = HelpSettings(verify_checks=False, show_hidden=True)
    assert await env.owner.formatter.catalog(env.ctx, settings) == {}


async def test_payload_limits_with_long_names(env):
    env.owner.formatter.catalog = AsyncMock(
        return_value={("*" * 250 + str(n)): {"Cog": {}} for n in range(26)}
    )
    view = await menu(env)
    embed = view.payload()["embed"]
    assert len(embed.description) <= 4096
    assert len(embed.title) <= 256
    assert all(len(option.label) <= 100 for option in view.children[0].options)


async def test_unloaded_cog_disappears(env):
    view = await menu(env)
    await view.navigate(click(), "select", "Repository: ultcogs", (None, None, 0))
    env.ctx.bot.commands.clear()
    env.ctx.bot.cogs.clear()
    await view.navigate(click(), "select", "Example", (view.repo, None, 0))
    assert not view.groups
    assert view.repo is None
