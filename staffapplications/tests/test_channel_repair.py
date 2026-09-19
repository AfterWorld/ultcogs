import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from staffapplications.staffapplications import StaffApplications
from staffapplications.store import UserError
from staffapplications.tests.test_workflow import cog as cog


def environment(cog, missing=()):
    role = MagicMock()
    role.id, role.managed = 4, False
    role.is_default.return_value = False
    role.guild = NS(id=1)
    everyone, bot = MagicMock(), MagicMock()
    channels = {}
    permissions = NS(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        manage_roles=True,
    )

    def make_channel(channel_id):
        channel = MagicMock(spec=discord.TextChannel)
        channel.id, channel.guild = channel_id, NS(id=1, me=bot, default_role=everyone)
        channel.permissions_for.side_effect = lambda target: (
            NS(view_channel=False) if target is everyone else permissions
        )
        return channel

    for cid in (101, 102, 103):
        if cid not in missing:
            channels[cid] = make_channel(cid)

    async def fetch(cid):
        if cid not in channels:
            raise discord.NotFound(
                NS(status=404, reason="Not found"), {"code": 10003, "message": "Unknown Channel"}
            )
        return channels[cid]

    async def create(name, **kwargs):
        cid = 201 + len([cid for cid in channels if cid >= 201])
        channels[cid] = make_channel(cid)
        return channels[cid]

    guild = NS(
        id=1,
        me=bot,
        default_role=everyone,
        get_role=lambda _: role,
        create_text_channel=AsyncMock(side_effect=create),
    )
    ctx = NS(guild=guild, send=AsyncMock())
    cog.bot.fetch_channel = AsyncMock(side_effect=fetch)
    cog.publish_panel = AsyncMock()
    cog.set_panel_visibility = AsyncMock()
    cog.store.configure(
        1,
        panel_channel=101,
        review_channel=102,
        error_channel=103,
        panel_message=150,
        reviewer_role=4,
        manage_panel_visibility=True,
        open=True,
    )
    return ctx, role, channels


async def test_repair_recreates_only_deleted_panel_privately(cog):
    ctx, role, channels = environment(cog, missing=(101,))
    await StaffApplications.repair_channels.callback(cog, ctx)
    ctx.guild.create_text_channel.assert_awaited_once()
    call = ctx.guild.create_text_channel.call_args
    assert call.args[0] == "staff-applications"
    assert call.kwargs["overwrites"][ctx.guild.default_role].view_channel is False
    assert call.kwargs["overwrites"][role].view_channel is True
    cfg = cog.store.settings(1)
    assert cfg["panel_channel"] == 201 and cfg["panel_message"] is None
    assert cfg["review_channel"] == 102 and cfg["error_channel"] == 103
    assert not cfg["open"] and cfg["manage_panel_visibility"]
    cog.publish_panel.assert_awaited_once_with(1)


async def test_repair_all_missing_then_repeat_creates_no_duplicates(cog):
    ctx, role, channels = environment(cog, missing=(101, 102, 103))
    app = cog.store.start(1, 10, "Moderator")
    await asyncio.gather(
        StaffApplications.repair_channels.callback(cog, ctx),
        StaffApplications.repair_channels.callback(cog, ctx),
    )
    assert ctx.guild.create_text_channel.await_count == 3
    for call in ctx.guild.create_text_channel.call_args_list:
        assert call.kwargs["overwrites"][ctx.guild.default_role].view_channel is False
    assert cog.store.get(app["id"])["status"] == "draft"


async def test_existing_channels_untouched_and_open_state_preserved(cog):
    ctx, role, channels = environment(cog)
    await StaffApplications.repair_channels.callback(cog, ctx)
    ctx.guild.create_text_channel.assert_not_awaited()
    cog.set_panel_visibility.assert_not_awaited()
    assert cog.store.settings(1)["open"]


@pytest.mark.parametrize(
    "error",
    [
        discord.Forbidden(NS(status=403, reason="Forbidden"), "no access"),
        discord.HTTPException(NS(status=503, reason="Unavailable"), "outage"),
    ],
)
async def test_permission_or_network_failure_never_creates_channels(cog, error):
    ctx, role, channels = environment(cog, missing=(101,))
    original = cog.bot.fetch_channel.side_effect

    async def fetch(cid):
        if cid == 102:
            raise error
        return await original(cid)

    cog.bot.fetch_channel.side_effect = fetch
    with pytest.raises((UserError, discord.HTTPException)):
        await StaffApplications.repair_channels.callback(cog, ctx)
    ctx.guild.create_text_channel.assert_not_awaited()
    assert cog.store.settings(1)["panel_channel"] == 101


async def test_partial_creation_saved_and_retry_resumes(cog):
    ctx, role, channels = environment(cog, missing=(101, 102, 103))
    original = ctx.guild.create_text_channel.side_effect

    async def create(name, **kwargs):
        if name == "application-reviews":
            raise discord.Forbidden(NS(status=403, reason="Forbidden"), "temporary failure")
        return await original(name, **kwargs)

    ctx.guild.create_text_channel.side_effect = create
    with pytest.raises(discord.Forbidden):
        await StaffApplications.repair_channels.callback(cog, ctx)
    assert cog.store.settings(1)["panel_channel"] == 201
    ctx.guild.create_text_channel.side_effect = original
    await StaffApplications.repair_channels.callback(cog, ctx)
    assert len([cid for cid in channels if cid >= 201]) == 3
    assert (
        sum(c.args[0] == "staff-applications" for c in ctx.guild.create_text_channel.call_args_list)
        == 1
    )


async def test_missing_saved_role_requests_current_role_before_mutating(cog):
    ctx, role, channels = environment(cog, missing=(101,))
    ctx.guild.get_role = lambda _: None
    with pytest.raises(UserError, match="YourStaffRole"):
        await StaffApplications.repair_channels.callback(cog, ctx)
    cog.bot.fetch_channel.assert_not_awaited()
    ctx.guild.create_text_channel.assert_not_awaited()
    await StaffApplications.repair_channels.callback(cog, ctx, role)
    ctx.guild.create_text_channel.assert_awaited_once()
