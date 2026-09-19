from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from staffapplications.alerts import diagnostic
from staffapplications.store import PanelUnavailable
from staffapplications.tests.test_workflow import cog as cog


def configured(cog):
    cog.store.configure(1, panel_channel=22, panel_message=33)
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 22
    channel.guild = NS(id=1)
    message = NS(id=33)
    channel.get_partial_message.return_value = NS(edit=AsyncMock(return_value=message))
    channel.send = AsyncMock(return_value=NS(id=44))
    return channel


def http_error(kind, code, status):
    return kind(
        NS(status=status, reason="Discord error"), {"code": code, "message": "sensitive payload"}
    )


async def test_cache_miss_fetches_existing_channel_without_duplicate_panel(cog):
    channel = configured(cog)
    cog.bot.get_channel.return_value = None
    cog.bot.fetch_channel.return_value = channel
    await cog.publish_panel(1)
    cog.bot.fetch_channel.assert_awaited_once_with(22)
    channel.get_partial_message.return_value.edit.assert_awaited_once()
    channel.send.assert_not_awaited()
    assert cog.store.settings(1)["panel_message"] == 33


@pytest.mark.parametrize(
    "kind,code,status,reason",
    [
        (discord.NotFound, 10003, 404, "missing"),
        (discord.Forbidden, 50001, 403, "forbidden"),
    ],
)
async def test_missing_or_inaccessible_channel_alerts_once_until_repaired(
    cog, kind, code, status, reason
):
    channel = configured(cog)
    cog.bot.get_channel.return_value = None
    cog.bot.fetch_channel.side_effect = http_error(kind, code, status)
    await cog.cycle()
    await cog.cycle()
    cog.bot.fetch_channel.assert_awaited_once_with(22)
    cog.alerts.report.assert_awaited_once()
    error = cog.alerts.report.call_args.args[2]
    assert isinstance(error, PanelUnavailable) and error.reason == reason
    assert "sensitive payload" not in diagnostic(error)
    assert "staffapp" in diagnostic(error)
    # Explicit repair retries the same channel and clears the paused refresh state.
    cog.bot.fetch_channel.side_effect = None
    cog.bot.fetch_channel.return_value = channel
    await cog.publish_panel(1)
    assert 1 not in cog._panel_paused
    assert cog.store.settings(1)["panel_channel"] == 22


async def test_deleted_message_is_recreated_but_channel_deletion_is_not(cog):
    channel = configured(cog)
    cog.bot.get_channel.return_value = channel
    channel.get_partial_message.return_value.edit.side_effect = http_error(
        discord.NotFound, 10008, 404
    )
    await cog.publish_panel(1)
    channel.send.assert_awaited_once()
    assert cog.store.settings(1)["panel_message"] == 44
    channel.send.reset_mock()
    channel.get_partial_message.return_value.edit.side_effect = http_error(
        discord.NotFound, 10003, 404
    )
    with pytest.raises(PanelUnavailable, match="deleted"):
        await cog.publish_panel(1)
    channel.send.assert_not_awaited()


async def test_discord_outage_uses_retry_delay_not_permanent_pause(cog):
    configured(cog)
    cog.bot.get_channel.return_value = None
    cog.bot.fetch_channel.side_effect = http_error(discord.HTTPException, 0, 503)
    await cog.cycle()
    await cog.cycle()
    assert cog.bot.fetch_channel.await_count == 1
    assert 1 not in cog._panel_paused
    assert cog._panel_retry[1] > 0
    cog._panel_retry[1] = 0
    await cog.cycle()
    assert cog.bot.fetch_channel.await_count == 2


async def test_changed_panel_configuration_resumes_refresh(cog):
    channel = configured(cog)
    cog._panel_paused[1] = (21, 33)
    cog.bot.get_channel.return_value = channel
    await cog.cycle()
    channel.get_partial_message.return_value.edit.assert_awaited_once()
    assert 1 not in cog._panel_paused


async def test_wrong_guild_channel_is_rejected_without_edit(cog):
    channel = configured(cog)
    channel.guild = NS(id=2)
    cog.bot.get_channel.return_value = channel
    with pytest.raises(PanelUnavailable, match="this server"):
        await cog.publish_panel(1)
    channel.send.assert_not_awaited()
    channel.get_partial_message.assert_not_called()
