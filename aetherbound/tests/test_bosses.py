import asyncio
import copy
import random

import pytest

from aetherbound import bosses as b
from aetherbound import engine as g
from aetherbound.balance import actor
from aetherbound.store import Store


@pytest.fixture
async def arena(tmp_path):
    s = Store(tmp_path / "shared.db")
    await s.initialize()
    await s.transaction(lambda c: b.create(c, "pool", 1, "tsukara", 2000))
    for user, cls in enumerate(("vanguard", "strider", "arcanist"), 1):
        p = actor(cls, 10, "rare", user)
        await s.change(1, user, lambda old, c, p=p: p, create=True)
        await s.change(1, user, lambda p, c, u=user: b.join(p, c, 1, u, "pool", now=1000))
    return s


async def turn(s, user, action="attack", now=1001):
    p = await s.player(1, user)
    battle = p["battle"]
    return await s.change(
        1,
        user,
        lambda p, c: b.act(
            p, c, 1, user, battle["id"], battle["turn"], action, random.Random(5), now=now
        ),
    )


async def test_concurrent_damage_and_stale_turn(arena):
    before = (await arena.rows("boss_pools"))[0]["hp"]
    await asyncio.gather(turn(arena, 1), turn(arena, 2))
    pool = (await arena.rows("boss_pools"))[0]
    members = await arena.rows("boss_members")
    assert before - pool["hp"] == sum(x["damage"] for x in members) > 0
    p = await arena.player(1, 1)
    with pytest.raises(g.RuleError):
        await arena.change(
            1,
            1,
            lambda p, c: b.act(
                p, c, 1, 1, p["battle"]["id"], 0, "attack", random.Random(1), now=1001
            ),
        )
    assert await arena.player(1, 1) == p


async def test_personal_kill_never_pays_and_cannot_rejoin(arena):
    await arena.change(1, 1, lambda p, c: p["battle"].update(enemy_hp=1))
    await turn(arena, 1)
    p = await arena.player(1, 1)
    assert p["wins"] == 0 and p["boss_wins"] == 0 and p["gold"] == 0 and p["battle"] is None
    with pytest.raises(g.RuleError):
        await arena.change(1, 1, lambda p, c: b.join(p, c, 1, 1, "pool", now=1002))
    with pytest.raises(g.RuleError):
        await arena.change(
            1, 1, lambda p, c: b.claim(p, c, 1, 1, "pool", random.Random(1), now=1002)
        )


async def test_final_blow_clamped_and_reward_once(arena):
    await arena.transaction(lambda c: c.execute("UPDATE boss_pools SET hp=1"))
    await arena.transaction(lambda c: c.execute("UPDATE boss_members SET damage=300 WHERE user=1"))
    results = await asyncio.gather(turn(arena, 1), turn(arena, 2))
    assert len(results) == 2
    assert (await arena.rows("boss_pools"))[0]["hp"] == 0
    members = await arena.rows("boss_members")
    assert sum(x["damage"] for x in members) == 301

    async def claim():
        return await arena.change(
            1,
            1,
            lambda p, c: b.claim(p, c, 1, 1, "pool", random.Random(7), now=1003),
            reason="shared_boss_reward",
        )

    results = await asyncio.gather(claim(), claim(), return_exceptions=True)
    assert sum(isinstance(x, g.RuleError) for x in results) == 1
    p = await arena.player(1, 1)
    assert p["boss_wins"] == 1 and p["kills"]["tsukara"] == 1
    assert p["gold"] == int(84 * 2 * 301 / 2280)
    assert any(x["reason"] == "shared_boss_reward" for x in await arena.rows("economy_events"))


async def test_expiry_pause_flee_and_restart(arena):
    await turn(arena, 1)
    saved = await arena.player(1, 1)
    reopened = Store(arena.path)
    await reopened.initialize()
    assert await reopened.player(1, 1) == saved
    await reopened.settings(1, {"features": {"shared_bosses": False}})
    with pytest.raises(g.RuleError):
        await turn(reopened, 1)
    await turn(reopened, 1, "flee")
    assert (await reopened.player(1, 1))["battle"] is None
    before = (await reopened.player(1, 2))["potions"]
    await turn(reopened, 2, "potion", now=2000)
    p = await reopened.player(1, 2)
    assert p["potions"] == before and p["battle"] is None
    assert "expired" in p["last_result"]


async def test_guild_isolation_and_level_gate(arena):
    with pytest.raises(g.RuleError):
        await arena.transaction(lambda c: b.get(c, 2, "pool"))
    p = actor("vanguard", 5, "rare", 2)
    await arena.change(1, 4, lambda old, c: p, create=True)
    with pytest.raises(g.RuleError):
        await arena.change(1, 4, lambda p, c: b.join(p, c, 1, 4, "pool", now=1001))
    assert not any(x["user"] == 4 for x in await arena.rows("boss_members"))


async def test_under_threshold_overflow_and_expired_claim(arena):
    await arena.transaction(lambda c: c.execute("UPDATE boss_pools SET hp=0,defeated=1001"))
    with pytest.raises(g.RuleError):
        await arena.change(
            1, 1, lambda p, c: b.claim(p, c, 1, 1, "pool", random.Random(1), now=1002)
        )
    await arena.transaction(lambda c: c.execute("UPDATE boss_members SET damage=500 WHERE user=1"))
    await arena.change(
        1, 1, lambda p, c: p.update(unclaimed_loot=[g.make_item("main") for _ in range(19)])
    )
    before = await arena.player(1, 1)
    with pytest.raises(g.RuleError):
        await arena.change(
            1, 1, lambda p, c: b.claim(p, c, 1, 1, "pool", random.Random(1), now=1002)
        )
    assert await arena.player(1, 1) == before
    with pytest.raises(g.RuleError):
        await arena.change(
            1, 1, lambda p, c: b.claim(p, c, 1, 1, "pool", random.Random(1), now=2001 + 7 * 86400)
        )
    await arena.delete_user(1)
    assert not any(x["user"] == 1 for x in await arena.rows("boss_members"))


def test_inventory_best_binds_only_final_and_respects_locks():
    p = actor("vanguard", 10, "common", 1)
    old = copy.deepcopy(p)
    low = g.make_item("main", 10, "rare", random.Random(1))
    high = g.make_item("main", 10, "mythic", random.Random(1))
    p["inventory"].update({i["id"]: i for i in (low, high)})
    g.equip_best(p)
    assert p["equipped"]["main"] == high["id"]
    assert not low["bound"] and high["bound"]
    assert g.loadout_rating(p) >= g.loadout_rating(old)
    g.lock_items(p, [high["id"]], True)
    better = g.make_item("main", 10, "mythic", random.Random(1))
    better["power"] = 999
    p["inventory"][better["id"]] = better
    g.equip_best(p)
    assert p["equipped"]["main"] == high["id"] and not better["bound"]
    before = copy.deepcopy(p)
    g.equip_best(p)
    assert p == before
    g.begin(p, "tsukara")
    with pytest.raises(g.RuleError):
        g.equip_best(p)


async def test_shared_turn_rolls_back_pool_and_player_together(arena):
    player = await arena.player(1, 1)
    pool = await arena.rows("boss_pools")
    members = await arena.rows("boss_members")

    def fail(p, c):
        battle = p["battle"]
        b.act(p, c, 1, 1, battle["id"], battle["turn"], "attack", random.Random(1), now=1001)
        raise RuntimeError("simulated failure after damage")

    with pytest.raises(RuntimeError):
        await arena.change(1, 1, fail)
    assert await arena.player(1, 1) == player
    assert await arena.rows("boss_pools") == pool
    assert await arena.rows("boss_members") == members
