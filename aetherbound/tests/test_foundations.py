import copy
import json
import random

import pytest

from aetherbound import engine as g
from aetherbound.content import CLASSES, SKILLS
from aetherbound.loot import migrate_item_flags
from aetherbound.store import Store

from .test_engine import graduate


@pytest.mark.parametrize("cls", CLASSES)
@pytest.mark.parametrize("key", ("skill1", "skill2", "skill3"))
def test_skill_data_drives_cost_cooldown_effects(cls, key, monkeypatch):
    p = graduate(cls)
    p["level"] = 20
    g.begin(p, "raizen")
    b = p["battle"]
    original = copy.deepcopy(SKILLS[cls][key])
    spec = dict(original, cost=5, cooldown=6)
    monkeypatch.setitem(SKILLS[cls], key, spec)
    before = b["energy"]
    g.act(p, b["id"], 0, key, random.Random(2))
    assert b["energy"] == before - 5
    assert b["cooldowns"][key] == 5
    assert SKILLS[cls][key]["effects"] == original["effects"]
    assert g.stats(p)["hp"] >= b["hp"] > 0


def test_salvage_lock_atomicity_payout_and_tutorial_protection():
    p = graduate()
    a = g.make_item("ring1", rarity="rare")
    b = g.make_item("ring2", rarity="mythic")
    p["inventory"].update({i["id"]: i for i in (a, b)})
    g.lock_items(p, [b["id"]], True)
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.salvage_many(p, [a["id"], b["id"]])
    assert p == before
    with pytest.raises(g.RuleError):
        g.salvage_many(p, [a["id"], a["id"]])
    assert p == before
    g.lock_items(p, [b["id"]], False)
    iron, essence = p["materials"].get("iron", 0), p["materials"].get("essence", 0)
    g.salvage_many(p, [a["id"], b["id"]])
    assert p["materials"]["iron"] == iron + 11
    assert p["materials"]["essence"] == essence + 5
    with pytest.raises(g.RuleError):
        g.salvage(p, p["equipped"]["main"])
    starter = g.new_player("Test", "vanguard")
    with pytest.raises(g.RuleError):
        g.salvage(starter, next(iter(starter["inventory"])))


def test_binding_migration_includes_overflow_and_shop_and_preserves_flags():
    p = graduate()
    ordinary = g.make_item("ring2")
    overflow = g.make_item("head", unique="wayfarer")
    offer = g.make_item("feet")
    p["inventory"][ordinary["id"]] = ordinary
    p["unclaimed_loot"] = [overflow]
    p["shop"] = {"offers": [{"item": offer}]}
    for i in list(p["inventory"].values()) + [overflow, offer]:
        i.pop("locked", None)
        i.pop("bound", None)
    migrate_item_flags(p)
    assert not ordinary["bound"] and not offer["bound"]
    assert overflow["bound"]
    assert p["inventory"][p["equipped"]["main"]]["bound"]
    g.lock_items(p, [ordinary["id"]], True)
    old = copy.deepcopy(p)
    migrate_item_flags(p)
    assert p == old
    g.equip(p, ordinary["id"])
    assert ordinary["bound"]


def test_auto_equip_whole_loadout_and_locked_current_gear():
    p = graduate()
    best = g.make_item("main")
    best["power"] = 100
    p["inventory"][best["id"]] = best
    current = p["inventory"][p["equipped"]["main"]]
    current["locked"] = True
    g.auto_equip(p, [best["id"]])
    assert p["equipped"]["main"] == current["id"]
    current["locked"] = False
    g.auto_equip(p, [best["id"]])
    assert p["equipped"]["main"] == best["id"] and best["bound"]
    old = copy.deepcopy(p)
    g.auto_equip(p, [best["id"], "missing", current["id"]])
    assert p == old
    # Losing an excellent off-hand can outweigh a modest two-handed weapon gain.
    off = p["inventory"][p["equipped"]["off"]]
    off["bonuses"] = {"vitality": 100}
    twohand = g.make_item("main", twohand=True)
    twohand["power"] = 70
    p["inventory"][twohand["id"]] = twohand
    g.auto_equip(p, [twohand["id"]])
    assert p["equipped"]["main"] == best["id"] and "off" in p["equipped"]


async def test_economy_log_transactions_overflow_killswitch_and_privacy(tmp_path):
    store = Store(tmp_path / "audit.sqlite3")
    await store.initialize()
    p = graduate()
    a = g.make_item("ring2", rarity="rare")
    p["inventory"][a["id"]] = a
    await store.change(1, 5, lambda _, c: p, create=True)
    initial = len(await store.rows("economy_events"))
    await store.settings(1, {"features": {"bulk_salvage": False}})
    with pytest.raises(g.RuleError):
        await store.change(1, 5, lambda p, c: g.salvage(p, a["id"]), feature="bulk_salvage")
    assert len(await store.rows("economy_events")) == initial
    await store.settings(1, {"features": {"bulk_salvage": True}})
    await store.change(
        1, 5, lambda p, c: g.salvage(p, a["id"]), reason="bulk_salvage", feature="bulk_salvage"
    )
    event = (await store.rows("economy_events"))[-1]
    assert event["reason"] == "bulk_salvage"
    d = json.loads(event["data"])
    assert d["destroyed"] == [a["id"]] and d["materials"] == {"iron": 4, "essence": 2}
    count = len(await store.rows("economy_events"))

    def fail(p, c):
        p["gold"] += 100
        raise g.RuleError("fail")

    with pytest.raises(g.RuleError):
        await store.change(1, 5, fail)
    assert len(await store.rows("economy_events")) == count
    overflow = g.make_item("head")
    await store.change(1, 5, lambda p, c: p.update(unclaimed_loot=[overflow]))
    count = len(await store.rows("economy_events"))
    await store.change(1, 5, lambda p, c: g.claim_loot(p))
    assert len(await store.rows("economy_events")) == count  # Move, not mint.
    await store.delete_user(5)
    assert not await store.rows("economy_events")


async def test_schema_one_migration_is_repeatable_and_keeps_progress(tmp_path):
    store = Store(tmp_path / "legacy.sqlite3")
    await store.initialize()
    p = graduate()
    for i in p["inventory"].values():
        i.pop("bound", None)
        i.pop("locked", None)
    await store.change(1, 5, lambda _, c: p, create=True)
    await store.transaction(lambda c: c.execute("PRAGMA user_version=1"))
    await store.initialize()
    migrated = await store.player(1, 5)
    assert migrated["gold"] == p["gold"] and migrated["tutorial"] == p["tutorial"]
    assert migrated["inventory"].keys() == p["inventory"].keys()
    assert migrated["inventory"][migrated["equipped"]["main"]]["bound"]
    await store.initialize()
    assert await store.player(1, 5) == migrated
