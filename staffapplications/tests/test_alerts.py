from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import discord

from staffapplications.alerts import Alerts, diagnostic
from staffapplications.store import Store


def environment(tmp_path):
    store = Store(tmp_path / "db")
    store.configure(1, error_channel=50)
    owner = NS(send=AsyncMock())
    channel = NS(guild=NS(id=1), send=AsyncMock())
    bot = NS(owner_ids={99}, owner_id=None, get_user=lambda _: owner, get_channel=lambda _: channel)
    return Alerts(bot, store, clock=lambda: 10), store, owner, channel


async def test_both_alert_routes_and_redacted_exception(tmp_path):
    alerts, store, owner, channel = environment(tmp_path)
    try:
        raise RuntimeError("secret-token and private application answer")
    except RuntimeError as exc:
        incident = await alerts.report(1, "test", exc, "abc")
    owner.send.assert_awaited_once()
    channel.send.assert_awaited_once()
    text = owner.send.call_args.args[0]
    assert incident in text and "RuntimeError" in text and "test_alerts.py" in text
    assert "secret-token" not in text and "private application answer" not in text
    assert owner.send.call_args.kwargs["allowed_mentions"].everyone is False
    store.close()


async def test_owner_failure_does_not_block_channel(tmp_path):
    alerts, store, owner, channel = environment(tmp_path)
    owner.send.side_effect = RuntimeError("DM blocked")
    await alerts.report(1, "test", ValueError("payload"))
    channel.send.assert_awaited_once()
    store.close()


async def test_channel_failure_does_not_block_owner(tmp_path):
    alerts, store, owner, channel = environment(tmp_path)
    channel.send.side_effect = RuntimeError("channel deleted")
    await alerts.report(1, "test", ValueError("payload"))
    owner.send.assert_awaited_once()
    assert channel.send.await_count == 1  # no recursive report
    store.close()


async def test_suppression_force_expiry_and_bounded_cache(tmp_path):
    alerts, store, owner, channel = environment(tmp_path)
    await alerts.report(1, "same", RuntimeError())
    await alerts.report(1, "same", RuntimeError())
    assert owner.send.await_count == 1
    await alerts.report(1, "same", RuntimeError(), force=True)
    assert owner.send.await_count == 2
    alerts.clock = lambda: 311
    await alerts.report(1, "same", RuntimeError())
    assert owner.send.await_count == 3
    for n in range(270):
        await alerts.report(1, str(n), RuntimeError())
    assert len(alerts.recent) == 256
    store.close()


def test_discord_payload_not_in_diagnostic():
    exc = discord.Forbidden(
        NS(status=403, reason="Forbidden"), {"code": 50007, "message": "private answer"}
    )
    result = diagnostic(exc)
    assert "403" in result and "50007" in result
    assert "private answer" not in result


async def test_global_worker_failure_reaches_configured_channel(tmp_path):
    alerts, store, owner, channel = environment(tmp_path)
    await alerts.report(None, "background worker", RuntimeError())
    owner.send.assert_awaited_once()
    channel.send.assert_awaited_once()
    store.close()
