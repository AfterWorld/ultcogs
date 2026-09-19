from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import discord
import pytest

from staffapplications.presets import ONE_PIECE_TEMPLATE, SAMPLE_ANSWERS
from staffapplications.staffapplications import StaffApplications
from staffapplications.store import UserError
from staffapplications.tests.test_workflow import cog as cog
from staffapplications.tests.test_workflow import interaction, queued
from staffapplications.views import SamplePages


def context():
    return NS(guild=NS(id=1), author=NS(id=10, send=AsyncMock()), send=AsyncMock())


async def preview(cog, ctx):
    await StaffApplications.test_application.callback(cog, ctx)


async def test_preview_preserves_real_application_and_closed_settings(cog):
    real = queued(cog)
    cog.store.configure(1, open=False, questions=ONE_PIECE_TEMPLATE["questions"])
    before = cog.store.settings(1)
    count = cog.store.submitted_count(1)
    ctx = context()
    channel = NS(send=AsyncMock(return_value=NS(jump_url="https://discord.com/channels/1/3/4")))
    cog.review_channel = AsyncMock(return_value=channel)
    await preview(cog, ctx)
    dm = ctx.author.send.call_args.kwargs
    review = channel.send.call_args.kwargs
    assert dm["embed"].title.startswith("TEST")
    assert review["embed"].title.startswith("TEST")
    assert "Fictional sample" in review["file"].fp.read().decode()
    for payload, reader in [(dm, "Review Answers"), (review, "View Answers")]:
        assert [b.label for b in payload["view"].children if not b.disabled] == [reader]
        assert payload["allowed_mentions"].everyone is False
        assert payload["view"].app["answers"] == list(SAMPLE_ANSWERS.values())
    assert cog.store.settings(1) == before
    assert cog.store.submitted_count(1) == count
    assert cog.store.all() == [real]


async def test_blocked_dm_does_not_post_review(cog):
    ctx = context()
    ctx.author.send.side_effect = discord.Forbidden(NS(status=403, reason="Forbidden"), "blocked")
    channel = NS(send=AsyncMock())
    cog.review_channel = AsyncMock(return_value=channel)
    with pytest.raises(UserError, match="Enable DMs"):
        await preview(cog, ctx)
    channel.send.assert_not_called()
    assert cog.store.all() == []


async def test_missing_configuration_does_not_send(cog):
    cog.store.configure(1, review_channel=None)
    ctx = context()
    with pytest.raises(UserError, match="Configure channels"):
        await preview(cog, ctx)
    ctx.author.send.assert_not_called()


async def test_channel_validation_before_dm(cog):
    ctx = context()
    cog.review_channel = AsyncMock(side_effect=UserError("Private channel required"))
    with pytest.raises(UserError, match="Private channel"):
        await preview(cog, ctx)
    ctx.author.send.assert_not_called()


async def test_custom_questions_and_reader_authorization(cog):
    ctx = context()
    channel = NS(send=AsyncMock(return_value=NS(jump_url="preview")))
    cog.review_channel = AsyncMock(return_value=channel)
    await preview(cog, ctx)
    view = channel.send.call_args.kwargs["view"]
    assert all("custom question" in answer for answer in view.app["answers"])
    cog.guard = AsyncMock(side_effect=UserError("Reviewer required"))
    click = interaction(uid=20)
    with pytest.raises(UserError, match="Reviewer required"):
        await view.open_answers(click)
    click.followup.send.assert_not_called()
    cog.guard = AsyncMock()
    await view.open_answers(click)
    cog.guard.assert_awaited_once_with(click, 1, reviewer=True)
    pages = click.followup.send.call_args.kwargs["view"]
    assert isinstance(pages, SamplePages)
    click.edit_original_response = AsyncMock()
    await pages.turn(click, 1)
    assert pages.index == 1
    assert "TEST" in click.edit_original_response.call_args.kwargs["embed"].title
    stranger = interaction(uid=30)
    await pages.turn(stranger, 1)
    assert pages.index == 1
    dm_view = ctx.author.send.call_args.kwargs["view"]
    cog.guard.reset_mock()
    await dm_view.open_answers(stranger)
    cog.guard.assert_not_called()
    assert cog.store.all() == []
