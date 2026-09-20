import asyncio
import random

import pytest

from aetherbound import engine as g
from aetherbound.store import Store

from .test_engine import graduate


@pytest.fixture
async def store(tmp_path):
    s = Store(tmp_path / "game.db")
    await s.initialize()
    return s


async def test_isolation_and_restart(store):
    await store.change(1, 5, lambda p, c: g.new_player("One", "vanguard"), create=True)
    await store.change(2, 5, lambda p, c: g.new_player("Two", "arcanist"), create=True)
    await store.change(1, 5, lambda p, c: p.update(gold=99))
    reopened = Store(store.path)
    assert (await reopened.player(1, 5))["gold"] == 99
    assert (await reopened.player(2, 5))["gold"] == 0


async def test_rollback(store):
    await store.change(1, 5, lambda p, c: g.new_player("One", "vanguard"), create=True)

    def fail(p, c):
        p["gold"] = 1000
        raise g.RuleError("rollback")

    with pytest.raises(g.RuleError):
        await store.change(1, 5, fail)
    assert (await store.player(1, 5))["gold"] == 0


async def test_simultaneous_actions_and_rewards(store):
    p = graduate()
    g.begin(p, "slime")
    p["battle"]["enemy_hp"] = 1
    bid = p["battle"]["id"]
    before = p["wins"]
    await store.change(1, 5, lambda _, c: p, create=True)

    async def click():
        return await store.change(1, 5, lambda p, c: g.act(p, bid, 0, "attack", random.Random(1)))

    results = await asyncio.gather(click(), click(), return_exceptions=True)
    assert sum(isinstance(x, g.RuleError) for x in results) == 1
    assert (await store.player(1, 5))["wins"] == before + 1


async def test_active_battle_round_trip(store):
    p = graduate()
    g.begin(p, "slime")
    g.act(p, p["battle"]["id"], 0, "guard", random.Random(1))
    await store.change(1, 5, lambda _, c: p, create=True)
    loaded = await Store(store.path).player(1, 5)
    assert loaded == p
    g.act(loaded, loaded["battle"]["id"], 1, "attack", random.Random(1))


async def test_delete_all_guild_data(store):
    for guild in (1, 2):
        await store.change(guild, 5, lambda p, c: g.new_player("One", "vanguard"), create=True)
    await store.transaction(lambda c: c.execute("INSERT INTO trades VALUES(1,1,5,2,0)"))
    await store.delete_user(5)
    assert not await store.rows("players")
    assert not await store.rows("trades")


async def test_two_store_instances_cannot_double_claim_rewards(store):
    p = graduate()
    g.accept_quest(p, "first_hunts")
    p["wins"] = 4
    await store.change(1, 5, lambda _, c: p, create=True)
    second = Store(store.path)
    results = await asyncio.gather(
        store.change(1, 5, lambda p, c: g.claim_quest(p, "first_hunts")),
        second.change(1, 5, lambda p, c: g.claim_quest(p, "first_hunts")),
        return_exceptions=True,
    )
    assert sum(isinstance(x, g.RuleError) for x in results) == 1
    assert (await store.player(1, 5))["gold"] == p["gold"] + 60


async def test_reject_newer_database(store):
    await store.transaction(lambda c: c.execute("PRAGMA user_version=99"))
    with pytest.raises(RuntimeError):
        await Store(store.path).initialize()
