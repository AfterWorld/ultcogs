import copy
import random

import pytest
from aetherbound.content import DUNGEONS, MONSTERS
from aetherbound.views import battle_embed

from aetherbound import engine as g

from .test_engine import graduate


def clear_room(p):
    b = p["battle"]
    b["enemy_hp"] = 1
    return g.act(p, b["id"], b["turn"], "attack", random.Random(1))


def test_clear_unlocks_scaled_tier_and_replay_does_not_skip_tiers():
    p = graduate(level=20)
    for room in range(4):
        g.enter_dungeon(p)
        assert p["run"]["room"] == room
        clear_room(p)
    assert p["run"] is None and g.dungeon_tier(p, "hollow") == 2
    g.enter_dungeon(p)
    assert p["battle"]["level"] == MONSTERS["wolf"]["level"] + 2
    assert p["battle"]["enemy_maxhp"] == 230
    assert "Level 5" in battle_embed(p).description
    g.act(p, p["battle"]["id"], 0, "flee", random.Random(1))
    for _ in range(4):
        g.enter_dungeon(p, "hollow", 1)
        clear_room(p)
    assert g.dungeon_tier(p, "hollow") == 2


def test_furnace_gate_room_carry_and_legacy_run():
    p = graduate(level=15)
    before = copy.deepcopy(p)
    with pytest.raises(g.RuleError):
        g.enter_dungeon(p, "furnace")
    assert p == before
    p["level"] = 16
    for index, monster in enumerate(DUNGEONS["furnace"]["rooms"]):
        g.enter_dungeon(p, "furnace" if index == 0 else None)
        assert p["battle"]["monster"] == monster
        if index:
            assert p["battle"]["hp"] == 70
        p["battle"]["hp"] = 70
        result = clear_room(p)
        if index < 3:
            assert p["run"]["hp"] == 70
    assert "Furnace Descent cleared! +120 gold" in result
    assert p["dungeon_clears"] == {"hollow": 0, "furnace": 1}
    assert g.objective_total(p, "trail") == 0
    p["run"] = {"room": 3, "hp": 70}
    g.enter_dungeon(p)
    assert p["battle"]["monster"] == "tsukara" and p["battle"]["level"] == 10


def test_scaled_damage_rewards_and_tier_limits():
    base = graduate(level=20)
    scaled = copy.deepcopy(base)
    for p, level in ((base, 3), (scaled, 13)):
        g.begin(p, "wolf", level=level)
        g.act(p, p["battle"]["id"], 0, "guard", random.Random(2))
    assert scaled["battle"]["hp"] < base["battle"]["hp"]
    for p in (base, scaled):
        clear_room(p)
    assert scaled["gold"] > base["gold"]
    assert scaled["inventory"][scaled["last_loot"][0]]["level"] == 13
    p = graduate(level=20)
    for tier in (0, -1, 2):
        with pytest.raises(g.RuleError):
            g.enter_dungeon(p, "hollow", tier)
    p["dungeons"] = 999  # Legacy clears remain useful, bounded by level 20.
    assert g.dungeon_tier(p, "hollow") == 6
    g.enter_dungeon(p, "hollow")
    assert p["battle"]["level"] == 13
    clear_room(p)
    with pytest.raises(g.RuleError):
        g.enter_dungeon(p, "furnace")
