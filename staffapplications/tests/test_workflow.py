import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

import staffapplications.staffapplications as module
from staffapplications.staffapplications import (
    StaffApplications,
    draft_embed,
    review_embed,
    transcript,
)
from staffapplications.store import UserError
from staffapplications.views import AnswerModal, DraftView, ReviewView, panel


@pytest.fixture
def cog(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "cog_data_path", lambda _: tmp_path)
    bot = NS(
        user=NS(id=999),
        add_view=MagicMock(),
        get_channel=MagicMock(),
        get_user=MagicMock(),
        get_guild=MagicMock(),
        fetch_user=AsyncMock(),
        fetch_channel=AsyncMock(),
        cog_disabled_in_guild=AsyncMock(return_value=False),
        allowed_by_whitelist_blacklist=AsyncMock(return_value=True),
        is_owner=AsyncMock(return_value=False),
        wait_until_red_ready=AsyncMock(),
    )
    value = StaffApplications(bot)
    value.store.configure(
        1,
        open=True,
        review_channel=3,
        error_channel=5,
        reviewer_role=4,
        questions=["Why do you want to help?", "When are you available?"],
    )
    value.alerts.report = AsyncMock(return_value="incident")
    yield value
    for view in value._views.values():
        view.stop()
    if value._worker:
        value._worker.cancel()
    value.store.close()


def draft(cog, user=10):
    return cog.store.start(1, user, "Moderator")


def queued(cog, user=10):
    app = draft(cog, user)
    for i in range(len(app["answers"])):
        app = cog.store.answer(app["id"], user, i, "Answer " + str(i), app["revision"])
    return cog.store.submit(app["id"], user)


def interaction(uid=10, guild_id=1, reviewer=False, message_id=100):
    return NS(
        user=NS(
            id=uid,
            bot=False,
            roles=[NS(id=4)] if reviewer else [],
            guild_permissions=NS(manage_guild=False),
            send=AsyncMock(),
        ),
        guild_id=guild_id,
        channel_id=3,
        message=NS(id=message_id),
        response=NS(
            defer=AsyncMock(),
            send_message=AsyncMock(),
            send_modal=AsyncMock(),
            is_done=lambda: True,
        ),
        followup=NS(send=AsyncMock()),
    )


def channel_with_history(candidates=()):
    channel = NS(send=AsyncMock(return_value=NS(id=100)), get_partial_message=MagicMock())

    async def history(**kwargs):
        for value in candidates:
            yield value

    channel.history = history
    return channel


async def test_real_components_persistent_and_payloads(cog):
    app = draft(cog)
    result = panel(cog, 1)
    assert isinstance(result["view"], discord.ui.LayoutView)
    assert result["view"].is_persistent()
    assert result["view"].to_components()[0]["type"] == 17
    assert DraftView(cog, app).is_persistent()
    modal = AnswerModal(cog, app, 0)
    assert modal.to_dict()["components"]
    assert len(draft_embed(app)) < 6000
    app = queued(cog)
    assert ReviewView(cog, app).is_persistent()
    assert review_embed(app).footer.text == f"staffapp:{app['id']}"
    file = transcript(app)
    assert b"Why do you want" in file.fp.read()
    file.close()


async def test_legacy_panel_fallback(cog, monkeypatch):
    monkeypatch.delattr(discord.ui, "LayoutView")
    value = panel(cog, 1)
    assert "embed" in value and value["view"].is_persistent()


async def test_delivery_and_simultaneous_retry_create_only_one_message(cog):
    app = queued(cog)
    channel = channel_with_history()
    cog.review_channel = AsyncMock(return_value=channel)
    await asyncio.gather(cog.deliver(app["id"]), cog.deliver(app["id"]))
    channel.send.assert_awaited_once()
    assert cog.store.get(app["id"])["status"] == "pending"
    assert cog.store.get(app["id"])["message"] == 100


async def test_ambiguous_send_recovers_without_duplicate(cog):
    app = queued(cog)
    candidates = []
    channel = channel_with_history(candidates)

    async def uncertain_send(**kwargs):
        candidates.append(NS(id=432, author=cog.bot.user, embeds=[kwargs["embed"]]))
        raise TimeoutError("response lost after Discord accepted the message")

    channel.send.side_effect = uncertain_send
    cog.review_channel = AsyncMock(return_value=channel)
    with pytest.raises(TimeoutError):
        await cog.deliver(app["id"])
    assert cog.store.get(app["id"])["attempted"]
    await cog.deliver(app["id"])
    assert cog.store.get(app["id"])["message"] == 432
    channel.send.assert_awaited_once()


async def test_history_failure_never_blindly_resends(cog):
    app = queued(cog)
    app["attempted"] = True
    cog.store.save(app)
    channel = channel_with_history()

    async def broken_history(**kwargs):
        raise RuntimeError("no history permission")
        yield

    channel.history = broken_history
    cog.review_channel = AsyncMock(return_value=channel)
    with pytest.raises(RuntimeError):
        await cog.deliver(app["id"])
    channel.send.assert_not_awaited()


async def test_worker_backoff_and_alert(cog):
    app = queued(cog)
    cog.review_channel = AsyncMock(side_effect=RuntimeError("channel missing"))
    await cog.cycle()
    restored = cog.store.get(app["id"])
    assert restored["status"] == "queued" and restored["next_retry"] > 0
    cog.alerts.report.assert_awaited_once()
    await cog.cycle()
    assert cog.alerts.report.await_count == 1


async def test_membership_and_reviewer_checks(cog):
    guild = NS(
        get_member=lambda _: None,
        fetch_member=AsyncMock(
            side_effect=discord.NotFound(NS(status=404, reason="Not found"), "gone")
        ),
    )
    cog.bot.get_guild.return_value = guild
    with pytest.raises(UserError, match="member"):
        await cog.guard(interaction(guild_id=None), 1)
    with pytest.raises(UserError, match="reviewers"):
        await cog.guard(interaction(), 1, reviewer=True)
    await cog.guard(interaction(uid=20, reviewer=True), 1, reviewer=True)
    with pytest.raises(UserError, match="different server"):
        await cog.guard(interaction(guild_id=2), 1)
    cog.bot.allowed_by_whitelist_blacklist.return_value = False
    with pytest.raises(UserError, match="cannot use"):
        await cog.guard(interaction(), 1)


async def test_wrong_review_message_rejected(cog):
    app = queued(cog)
    app.update(status="pending", message=100)
    cog.store.save(app)
    with pytest.raises(UserError, match="original"):
        await cog.handle(interaction(uid=20, reviewer=True, message_id=101), 1, "claim", app["id"])


async def test_blocked_start_dm_preserves_draft_and_alerts(cog):
    app = draft(cog)
    i = interaction()
    i.user.send.side_effect = discord.Forbidden(NS(status=403, reason="Forbidden"), "blocked")
    await cog.send_draft(i, app)
    assert cog.store.get(app["id"])["status"] == "draft"
    assert "Enable direct messages" in i.followup.send.call_args.args[0]
    cog.alerts.report.assert_awaited_once()


async def test_decision_dm_blocked_is_reported_and_status_preserved(cog):
    app = queued(cog)
    app.update(status="pending", message=100)
    cog.store.save(app)
    app = cog.store.decide(app["id"], 20, "accepted", "Welcome")
    app["ui_dirty"] = False
    cog.store.save(app)
    user = NS(
        send=AsyncMock(side_effect=discord.Forbidden(NS(status=403, reason="Forbidden"), "blocked"))
    )
    cog.bot.get_user.return_value = user
    await cog.side_effects(app["id"])
    saved = cog.store.get(app["id"])
    assert saved["status"] == "accepted" and not saved["notify"] and saved["notification_failed"]
    cog.alerts.report.assert_awaited_once()


async def test_exception_handler_acknowledges_and_reports(cog):
    i = interaction()
    await cog.interaction_error(i, 1, RuntimeError("private data"), "abc")
    assert "private data" not in i.followup.send.call_args.args[0]
    cog.alerts.report.assert_awaited_once()
    cog.alerts.report.reset_mock()
    await cog.interaction_error(i, 1, UserError("Please answer every question"))
    cog.alerts.report.assert_not_awaited()


async def test_restores_persistent_views_on_load(cog):
    app = draft(cog)
    app.update(dm_message=50, dm_channel=51)
    cog.store.save(app)
    cog.store.configure(1, panel_message=60)
    cog.worker = AsyncMock()
    await cog.cog_load()
    assert set(cog._views) == {50, 60}
    assert all(view.is_persistent() for view in cog._views.values())
    await asyncio.sleep(0)


async def test_delete_removes_review_and_dm_before_record(cog):
    app = queued(cog)
    app.update(status="pending", message=100, dm_message=101, dm_channel=102)
    cog.store.save(app)
    message = NS(delete=AsyncMock())
    channel = NS(get_partial_message=lambda _: message)
    cog.bot.get_channel.return_value = channel
    await cog.erase(app)
    assert message.delete.await_count == 2
    with pytest.raises(UserError, match="no longer exists"):
        cog.store.get(app["id"])


async def test_delete_failure_keeps_record_for_retry(cog):
    app = queued(cog)
    app.update(status="pending", message=100)
    cog.store.save(app)
    message = NS(
        delete=AsyncMock(
            side_effect=discord.Forbidden(NS(status=403, reason="Forbidden"), "blocked")
        )
    )
    cog.bot.get_channel.return_value = NS(get_partial_message=lambda _: message)
    with pytest.raises(discord.Forbidden):
        await cog.erase(app)
    assert cog.store.get(app["id"])["message"] == 100


async def test_real_red_command_registration():
    assert StaffApplications.staffapp.get_command("setup")
    assert StaffApplications.staffapp.get_command("testerror")
    assert StaffApplications.staffapp.checks


async def test_broken_review_card_does_not_block_decision_dm(cog):
    app = queued(cog)
    app.update(status="pending", message=100)
    cog.store.save(app)
    cog.store.decide(app["id"], 20, "declined", "Thanks for applying")
    cog.review_channel = AsyncMock(side_effect=RuntimeError("missing channel"))
    user = NS(send=AsyncMock())
    cog.bot.get_user.return_value = user
    with pytest.raises(RuntimeError):
        await cog.side_effects(app["id"])
    user.send.assert_awaited_once()
    app = cog.store.get(app["id"])
    assert app["ui_dirty"] and not app["notify"]


async def test_delete_waits_for_inflight_delivery_then_removes_message(cog):
    app = queued(cog)
    entered, release = asyncio.Event(), asyncio.Event()
    message = NS(id=123, delete=AsyncMock())
    channel = channel_with_history()
    channel.get_partial_message.return_value = message

    async def slow_send(**kwargs):
        entered.set()
        await release.wait()
        return message

    channel.send.side_effect = slow_send
    cog.review_channel = AsyncMock(return_value=channel)
    cog.bot.get_channel.return_value = channel
    delivering = asyncio.create_task(cog.deliver(app["id"]))
    await entered.wait()
    deleting = asyncio.create_task(cog.erase(app))
    await asyncio.sleep(0)
    assert not deleting.done()
    release.set()
    await asyncio.gather(delivering, deleting)
    message.delete.assert_awaited_once()
    with pytest.raises(UserError):
        cog.store.get(app["id"])


async def test_delete_of_ambiguous_submission_only_reconciles_never_sends(cog):
    app = queued(cog)
    app["attempted"] = True
    cog.store.save(app)
    channel = channel_with_history()
    cog.review_channel = AsyncMock(return_value=channel)
    await cog.erase(app)
    channel.send.assert_not_awaited()
    with pytest.raises(UserError):
        cog.store.get(app["id"])


async def test_new_decision_during_card_edit_remains_dirty(cog):
    app = queued(cog)
    app.update(status="pending", message=100)
    cog.store.save(app)
    cog.store.decide(app["id"], 20, "claim")

    async def racing_edit(**kwargs):
        cog.store.decide(app["id"], 20, "accepted", "Welcome")

    message = NS(edit=AsyncMock(side_effect=racing_edit))
    channel = NS(get_partial_message=lambda _: message)
    cog.review_channel = AsyncMock(return_value=channel)
    cog.bot.get_user.return_value = NS(send=AsyncMock())
    await cog.side_effects(app["id"])
    app = cog.store.get(app["id"])
    assert app["status"] == "accepted" and app["ui_dirty"]


async def test_successful_modal_persists_and_duplicate_modal_rejected(cog):
    app = draft(cog)
    modal = AnswerModal(cog, app, 0)
    modal.answer._value = "I enjoy helping people."
    cog.refresh_draft = AsyncMock()
    await modal.on_submit(interaction())
    assert cog.store.get(app["id"])["answers"][0] == "I enjoy helping people."
    with pytest.raises(UserError, match="out of date"):
        await modal.on_submit(interaction())


async def test_duplicate_staff_decisions_only_one_succeeds(cog):
    from staffapplications.views import DecisionModal

    app = queued(cog)
    app.update(status="pending", message=100)
    cog.store.save(app)
    first = DecisionModal(cog, app, "accepted")
    second = DecisionModal(cog, app, "declined")
    first.reason._value = "Welcome"
    second.reason._value = "No thanks"
    results = await asyncio.gather(
        first.on_submit(interaction(uid=20, reviewer=True)),
        second.on_submit(interaction(uid=30, reviewer=True)),
        return_exceptions=True,
    )
    assert sum(isinstance(r, UserError) for r in results) == 1
    assert cog.store.get(app["id"])["status"] in {"accepted", "declined"}


async def test_public_review_channel_rejected(cog):
    permissions = NS(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
    )
    channel = NS(
        guild=NS(me=object(), default_role=object()), permissions_for=lambda _: permissions
    )
    with pytest.raises(UserError, match="private channel"):
        cog.validate_channel(channel, private=True, review=True)


async def test_private_answer_reader_checks_reviewer_again(cog):
    from staffapplications.views import AnswerPages

    app = queued(cog)
    app.update(status="pending", message=100)
    cog.store.save(app)
    pages = AnswerPages(cog, app, 20, reviewer=True)
    with pytest.raises(UserError, match="reviewers"):
        await pages.turn(interaction(uid=20, reviewer=False), 1)


async def test_owner_alert_still_attempted_when_command_reply_fails(cog):
    ctx = NS(guild=NS(id=1), send=AsyncMock(side_effect=RuntimeError("reply failed")))
    with pytest.raises(RuntimeError):
        await cog.cog_command_error(ctx, RuntimeError("original bug"))
    cog.alerts.report.assert_awaited_once()


async def test_generated_channels_start_private_with_staff_access(cog):
    everyone, bot_member, reviewer = MagicMock(), MagicMock(), MagicMock()
    reviewer.id, reviewer.managed = 4, False
    reviewer.is_default.return_value = False
    guild = NS(
        id=1,
        default_role=everyone,
        me=bot_member,
        create_text_channel=AsyncMock(side_effect=[NS(id=10), NS(id=11), NS(id=12)]),
    )
    ctx = NS(guild=guild, send=AsyncMock())
    cog.publish_panel = AsyncMock()
    await StaffApplications.create_channels.callback(cog, ctx, reviewer)
    for call in guild.create_text_channel.call_args_list:
        overwrites = call.kwargs["overwrites"]
        assert overwrites[everyone].view_channel is False
        assert overwrites[reviewer].view_channel is True
        assert overwrites[bot_member].view_channel is True
    cfg = cog.store.settings(1)
    assert cfg["manage_panel_visibility"] and not cfg["open"]
    assert cfg["review_channel"] == 11 and cfg["error_channel"] == 12


def managed_panel(cog):
    everyone = object()
    overwrite = discord.PermissionOverwrite(
        view_channel=False, send_messages=False, add_reactions=False
    )
    channel = NS(
        guild=NS(id=1, default_role=everyone, me=object()),
        permissions_for=lambda _: NS(manage_roles=True),
        overwrites_for=lambda _: overwrite,
        set_permissions=AsyncMock(),
    )
    cog.bot.get_channel.return_value = channel
    cog.store.configure(1, panel_channel=10, manage_panel_visibility=True, open=False)
    cog.publish_panel = AsyncMock()
    return channel


async def test_open_and_close_change_only_panel_visibility(cog):
    channel = managed_panel(cog)
    ctx = NS(guild=NS(id=1), tick=AsyncMock())
    await StaffApplications.open_command.callback(cog, ctx, True)
    assert cog.store.settings(1)["open"]
    overwrite = channel.set_permissions.call_args.kwargs["overwrite"]
    assert overwrite.view_channel is True
    assert overwrite.send_messages is False and overwrite.add_reactions is False
    await StaffApplications.open_command.callback(cog, ctx, False)
    assert not cog.store.settings(1)["open"]
    assert channel.set_permissions.call_args.kwargs["overwrite"].view_channel is False
    assert all(call.args == (10,) for call in cog.bot.get_channel.call_args_list)


async def test_failed_permission_change_does_not_open_applications(cog):
    channel = managed_panel(cog)
    channel.set_permissions.side_effect = discord.Forbidden(
        NS(status=403, reason="Forbidden"), "denied"
    )
    ctx = NS(guild=NS(id=1), tick=AsyncMock())
    with pytest.raises(discord.Forbidden):
        await StaffApplications.open_command.callback(cog, ctx, True)
    assert not cog.store.settings(1)["open"]
    cog.publish_panel.assert_not_awaited()


async def test_close_stops_submissions_even_if_hiding_fails(cog):
    channel = managed_panel(cog)
    cog.store.configure(1, open=True)
    channel.set_permissions.side_effect = discord.Forbidden(
        NS(status=403, reason="Forbidden"), "denied"
    )
    ctx = NS(guild=NS(id=1), tick=AsyncMock())
    with pytest.raises(discord.Forbidden):
        await StaffApplications.open_command.callback(cog, ctx, False)
    assert not cog.store.settings(1)["open"]


async def test_existing_manually_configured_channel_keeps_visibility(cog):
    cog.store.configure(1, panel_channel=10, manage_panel_visibility=False)
    cog.set_panel_visibility = AsyncMock()
    cog.publish_panel = AsyncMock()
    ctx = NS(guild=NS(id=1), tick=AsyncMock())
    await StaffApplications.open_command.callback(cog, ctx, False)
    cog.set_panel_visibility.assert_not_awaited()
    assert not cog.store.settings(1)["open"]
