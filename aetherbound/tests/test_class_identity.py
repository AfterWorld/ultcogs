import copy
import random

import pytest

from aetherbound import engine as g
from aetherbound.content import MECHANICS
from aetherbound.store import Store

from .test_engine import graduate


def fighter(cls):
    p = graduate(cls)
    p["level"] = 20
    g.begin(p, "raizen")
    p["battle"].update(enemy_hp=100000, enemy_maxhp=100000, hp=10000, maxhp=10000)
    return p


def turn(p, action):
    b = p["battle"]
    g.act(p, b["id"], b["turn"], action, random.Random(5))


def test_resolve_caps_and_cleave_spends_it():
    p = fighter("vanguard")
    for _ in range(4):
        turn(p, "guard")
    assert p["battle"]["resource"] == 3
    uncharged = copy.deepcopy(p)
    uncharged["battle"]["resource"] = 0
    turn(p, "skill1")
    turn(uncharged, "skill1")
    assert p["battle"]["resource"] == 0
    assert p["battle"]["enemy_hp"] < uncharged["battle"]["enemy_hp"]
    assert p["battle"]["energy"] == uncharged["battle"]["energy"]


def test_momentum_requires_alternation_and_resets():
    p = fighter("strider")
    for action in ("attack", "skill1", "attack", "skill2"):
        turn(p, action)
    assert p["battle"]["resource"] == 3
    turn(p, "attack")
    assert p["battle"]["resource"] == 3
    turn(p, "attack")
    assert p["battle"]["resource"] == 0
    turn(p, "skill1")
    assert p["battle"]["resource"] == 1
    turn(p, "guard")
    assert p["battle"]["resource"] == 0
    same_gear = copy.deepcopy(p)
    same_gear["cls"] = "vanguard"
    assert g.stats(p)["crit"] == pytest.approx(g.stats(same_gear)["crit"] + 0.03)


def test_charges_discount_real_cost_and_legacy_battles():
    p = fighter("arcanist")
    p["battle"].pop("resource")
    p["battle"].pop("last_damaging")
    for _ in range(4):
        turn(p, "attack")
    assert p["battle"]["resource"] == 3
    assert g.skill_cost(p, "skill1") == 10
    p["battle"]["energy"] = 10
    turn(p, "skill1")
    assert p["battle"]["energy"] == 0 and p["battle"]["resource"] == 0
    turn(p, "guard")
    assert p["battle"]["energy"] == 12
    assert g.skill_cost(p, "skill1") == 16
    saved = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        turn(p, "skill1")
    assert p == saved


@pytest.mark.parametrize("cls", MECHANICS)
async def test_resource_survives_restart_and_resets_next_encounter(tmp_path, cls):
    p = fighter(cls)
    turn(p, "attack" if cls != "vanguard" else "guard")
    turn(p, "skill3")
    store = Store(tmp_path / "state.db")
    await store.initialize()
    await store.change(1, 5, lambda _, c: p, create=True)
    saved = await Store(store.path).player(1, 5)
    assert saved["battle"]["resource"] == p["battle"]["resource"]
    turn(saved, "flee")
    g.begin(saved, "raizen")
    assert saved["battle"]["resource"] == 0


def test_soft_armor_is_continuous_and_upgrades_keep_helping():
    assert g.armor_rating(99) == 99
    assert g.armor_rating(100) == 100
    assert 100 < g.armor_rating(101) < 101
    values = [g.armor_rating(raw) for raw in range(100, 1000)]
    assert all(a < b for a, b in zip(values, values[1:]))
    gains = [g.armor_rating(raw + 2) - g.armor_rating(raw) for raw in (100, 200, 400)]
    assert gains[0] > gains[1] > gains[2] > 0
    p = fighter("vanguard")
    for i in p["inventory"].values():
        i["power"] = 28
    before = g.stats(p)["armor"]
    p["inventory"][p["equipped"]["chest"]]["upgrade"] += 1
    assert g.stats(p)["armor"] > before > 100


def test_vanguard_passive_reduces_direct_damage(monkeypatch):
    p = fighter("vanguard")
    without = copy.deepcopy(p)
    turn(p, "attack")
    monkeypatch.setitem(MECHANICS["vanguard"], "incoming", 1)
    turn(without, "attack")
    assert p["battle"]["hp"] > without["battle"]["hp"]
